from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from audit.service import record
from cases.models import Case
from identity.models import Membership, Unit
from identity.policy import active_memberships, can, visible_cases, visible_intelligence
from platform_api.errors import Conflict

from .models import CaseIntelligence, Dissemination, DisseminationReturn, Intelligence, ProtectedSource
from .serializers import (CaseLinkSerializer, ConfirmDisseminationSerializer, DisseminationCreateSerializer, DisseminationSerializer,
                          IntelligenceCreateSerializer, IntelligenceSerializer, IntelligenceUpdateSerializer,
                          ReturnCreateSerializer, ReturnSerializer)


class IntelligenceViewSet(viewsets.GenericViewSet):
    serializer_class = IntelligenceSerializer
    lookup_value_regex = "[0-9a-f-]{36}"

    def get_queryset(self):
        return visible_intelligence(self.request.user).select_related("unit", "assignee")

    def get_object(self):
        item = super().get_object()
        if not can(self.request.user, "intelligence.read", item):
            raise PermissionDenied()
        return item

    @extend_schema(responses=IntelligenceSerializer(many=True))
    def list(self, request):
        if set(request.query_params) - {"page", "page_size", "format"}:
            raise ValidationError({"filters": ["Filtre non autorisé."]})
        page = self.paginate_queryset(self.get_queryset())
        units = {item.unit_id: item.unit for item in page}
        if not units:
            membership = active_memberships(request.user).filter(role__in=[Membership.Role.MANAGER, Membership.Role.INVESTIGATOR]).select_related("unit").first()
            if membership is None:
                raise PermissionDenied()
            units[membership.unit_id] = membership.unit
        with transaction.atomic():
            for unit in units.values():
                record(request, action="intelligence.list", unit=unit)
        return self.get_paginated_response(IntelligenceSerializer(page, many=True).data)

    @extend_schema(responses=IntelligenceSerializer)
    def retrieve(self, request, *args, **kwargs):
        item = self.get_object()
        with transaction.atomic():
            record(request, action="intelligence.read", unit=item.unit, resource=item)
        return Response(IntelligenceSerializer(item).data)

    @extend_schema(request=IntelligenceCreateSerializer, responses={201: IntelligenceSerializer})
    def create(self, request):
        serializer = IntelligenceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        unit = get_object_or_404(Unit.objects.filter(pk__in=active_memberships(request.user).values("unit_id")), pk=data["unit"])
        classification = int(data["classification"])
        if not can(request.user, "intelligence.create", context={"unit": unit, "classification": classification}):
            raise PermissionDenied()
        assignee = get_user_model().objects.filter(pk=data["assignee"], is_active=True).first()
        if assignee is None or not active_memberships(assignee, unit=unit).filter(role=Membership.Role.INVESTIGATOR, clearance__gte=classification).exists():
            raise ValidationError({"assignee": ["Agent non habilité."]})
        if request.user.pk != assignee.pk and not active_memberships(request.user, unit=unit).filter(role=Membership.Role.MANAGER, clearance__gte=classification).exists():
            raise PermissionDenied()
        source_identity = data.pop("source_identity", None)
        if source_identity:
            if not can(request.user, "source.write", context={"unit": unit, "classification": classification}):
                raise PermissionDenied()
            if source_identity.casefold() in (data["subject"] + " " + data["summary"]).casefold():
                raise ValidationError({"source_identity": ["La source ne doit pas figurer dans l'objet ou le résumé."]})
        with transaction.atomic():
            item = Intelligence.objects.create(unit=unit, classification=classification, subject=data["subject"], summary=data["summary"], provenance=data["provenance"], occurred_on=data["occurred_on"], assignee=assignee, created_by=request.user)
            if source_identity:
                ProtectedSource.objects.create(intelligence=item, identity=source_identity)
            record(request, action="intelligence.created", unit=unit, resource=item, details={"source_recorded": bool(source_identity)})
        return Response(IntelligenceSerializer(item).data, status=201)

    @extend_schema(request=IntelligenceUpdateSerializer, responses=IntelligenceSerializer)
    def partial_update(self, request, *args, **kwargs):
        item = self.get_object()
        data = IntelligenceUpdateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = dict(data.validated_data)
        version = values.pop("version")
        if not can(request.user, "intelligence.update", item):
            raise PermissionDenied()
        source = ProtectedSource.objects.filter(intelligence=item).first()
        if source and source.identity.casefold() in (values.get("subject", item.subject) + " " + values.get("summary", item.summary)).casefold():
            raise ValidationError({"summary": ["La source ne doit pas figurer dans l'objet ou le résumé."]})
        with transaction.atomic():
            updated = Intelligence.objects.filter(pk=item.pk, version=version).update(**values, version=version + 1, updated_at=timezone.now())
            if not updated:
                raise Conflict()
            item.refresh_from_db()
            record(request, action="intelligence.updated", unit=item.unit, resource=item, details={"version": item.version, "fields": sorted(values)})
        return Response(IntelligenceSerializer(item).data)

    @extend_schema(responses=IntelligenceSerializer)
    @action(detail=True, methods=["get"], url_path="source")
    def source(self, request, *args, **kwargs):
        item = self.get_object()
        if not can(request.user, "source.read", item):
            raise PermissionDenied()
        source = get_object_or_404(ProtectedSource, intelligence=item)
        with transaction.atomic():
            record(request, action="source.read", unit=item.unit, resource=item)
        return Response({"identity": source.identity})

    @extend_schema(request=CaseLinkSerializer, responses=IntelligenceSerializer)
    @action(detail=True, methods=["post", "get"], url_path="dossiers")
    def cases(self, request, *args, **kwargs):
        item = self.get_object()
        if request.method == "GET":
            ids = list(visible_cases(request.user).filter(intelligence=item).values_list("id", flat=True))
            with transaction.atomic():
                record(request, action="intelligence.cases.read", unit=item.unit, resource=item)
            return Response({"dossiers": ids})
        serializer = CaseLinkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        case = get_object_or_404(visible_cases(request.user), pk=serializer.validated_data["case"])
        if not can(request.user, "intelligence.update", item) or not can(request.user, "case.read", case):
            raise PermissionDenied()
        version = serializer.validated_data["version"]
        with transaction.atomic():
            if not Intelligence.objects.filter(pk=item.pk, version=version).update(version=version + 1, updated_at=timezone.now()):
                raise Conflict()
            try:
                CaseIntelligence.objects.create(intelligence=item, case=case, linked_by=request.user)
            except IntegrityError:
                raise Conflict()
            item.refresh_from_db()
            record(request, action="intelligence.case.linked", unit=item.unit, resource=item, details={"case_id": str(case.pk), "version": item.version})
        return Response(IntelligenceSerializer(item).data, status=201)

    @extend_schema(request=DisseminationCreateSerializer, responses=DisseminationSerializer(many=True))
    @action(detail=True, methods=["post", "get"], url_path="diffusions")
    def disseminations(self, request, *args, **kwargs):
        item = self.get_object()
        if not can(request.user, "intelligence.distribute", item):
            raise PermissionDenied()
        if request.method == "GET":
            page = self.paginate_queryset(item.disseminations.all())
            with transaction.atomic():
                record(request, action="intelligence.disseminations.read", unit=item.unit, resource=item)
            return self.get_paginated_response(DisseminationSerializer(page, many=True).data)
        serializer = DisseminationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        recipient = get_object_or_404(Unit, pk=data["recipient_unit"])
        defaults = {"recipient_unit": recipient, "channel": data["channel"], "reference": data.get("reference", ""), "expected_action": data["expected_action"], "sent_at": data.get("sent_at"), "created_by": request.user}
        with transaction.atomic():
            obj, created = Dissemination.objects.get_or_create(intelligence=item, idempotency_key=data["idempotency_key"], defaults=defaults)
            if not created and any(getattr(obj, key) != value for key, value in defaults.items()):
                raise Conflict()
            if created:
                record(request, action="intelligence.dissemination.recorded", unit=item.unit, resource=item, details={"dissemination_id": str(obj.pk), "recipient_unit_id": str(recipient.pk), "confirmed": obj.sent_at is not None})
        return Response(DisseminationSerializer(obj).data, status=201 if created else 200)


class DisseminationViewSet(viewsets.GenericViewSet):
    lookup_value_regex = "[0-9a-f-]{36}"
    queryset = Dissemination.objects.select_related("intelligence__unit", "recipient_unit")

    def _visible_dissemination(self, request, pk):
        origin_scope = self.queryset.filter(intelligence__in=visible_intelligence(request.user))
        obj = get_object_or_404(origin_scope, pk=pk)
        item = obj.intelligence
        origin = can(request.user, "intelligence.distribute", item)
        recipient = obj.sent_at is not None and active_memberships(request.user, unit=obj.recipient_unit).filter(role=Membership.Role.MANAGER, clearance__gte=item.classification).exists()
        if not origin and not recipient:
            raise PermissionDenied()
        return obj

    @extend_schema(responses=DisseminationSerializer)
    def retrieve(self, request, *args, **kwargs):
        obj = self._visible_dissemination(request, kwargs["pk"])
        with transaction.atomic():
            record(request, action="intelligence.dissemination.read", unit=obj.intelligence.unit, resource=obj.intelligence, details={"dissemination_id": str(obj.pk)})
        return Response(DisseminationSerializer(obj).data)

    @extend_schema(request=ConfirmDisseminationSerializer, responses=DisseminationSerializer)
    @action(detail=True, methods=["post"], url_path="confirmer")
    def confirm(self, request, *args, **kwargs):
        obj = self._visible_dissemination(request, kwargs["pk"])
        item = obj.intelligence
        if not can(request.user, "intelligence.distribute", item):
            raise PermissionDenied()
        serializer = ConfirmDisseminationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sent_at = serializer.validated_data["sent_at"]
        with transaction.atomic():
            updated = Dissemination.objects.filter(pk=obj.pk, sent_at__isnull=True).update(sent_at=sent_at)
            obj.refresh_from_db()
            if not updated and obj.sent_at != sent_at:
                raise Conflict()
            if updated:
                record(request, action="intelligence.dissemination.confirmed", unit=item.unit, resource=item, details={"dissemination_id": str(obj.pk)})
        return Response(DisseminationSerializer(obj).data)

    @extend_schema(request=ReturnCreateSerializer, responses=ReturnSerializer(many=True))
    @action(detail=True, methods=["post", "get"], url_path="retours")
    def returns(self, request, *args, **kwargs):
        # Resolve through visible intelligence before exposing a dissemination's existence.
        obj = self._visible_dissemination(request, kwargs["pk"])
        item = obj.intelligence
        if obj.sent_at is None:
            raise ValidationError({"diffusion": ["Envoi non confirmé."]})
        if request.method == "GET":
            page = self.paginate_queryset(obj.returns.all())
            with transaction.atomic():
                record(request, action="intelligence.returns.read", unit=item.unit, resource=item)
            return self.get_paginated_response(ReturnSerializer(page, many=True).data)
        serializer = ReturnCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        defaults = {"acknowledged": data["acknowledged"], "received_at": data["received_at"], "note": data.get("note", ""), "recorded_by": request.user}
        with transaction.atomic():
            obj_return, created = DisseminationReturn.objects.get_or_create(dissemination=obj, idempotency_key=data["idempotency_key"], defaults=defaults)
            if not created and any(getattr(obj_return, key) != value for key, value in defaults.items()):
                raise Conflict()
            if created:
                record(request, action="intelligence.return.recorded", unit=item.unit, resource=item, details={"dissemination_id": str(obj.pk), "return_id": str(obj_return.pk)})
        return Response(ReturnSerializer(obj_return).data, status=201 if created else 200)
