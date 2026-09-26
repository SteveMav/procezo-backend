from django.db import transaction
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone
from rest_framework import generics, serializers
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from drf_spectacular.utils import OpenApiParameter, extend_schema
from drf_spectacular.types import OpenApiTypes

from audit.service import record
from identity.models import Membership
from identity.policy import active_memberships, has_delegation, visible_cases
from identity.models import Delegation
from requests_app.models import CommunicationRequest, RequestEvent
from decisions.models import Decision

from .models import Case


class WorkItemSerializer(serializers.Serializer):
    kind = serializers.CharField(required=False)
    id = serializers.UUIDField()
    case = serializers.UUIDField()
    reference = serializers.CharField(required=False)
    status = serializers.CharField()
    next_action = serializers.CharField(required=False)
    due_on = serializers.DateField(required=False, allow_null=True)
    overdue = serializers.BooleanField(required=False)
    returned = serializers.BooleanField(required=False)
    internal_alert = serializers.BooleanField(required=False)
    action_url = serializers.CharField()


class ValidationItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    case = serializers.UUIDField()
    status = serializers.CharField()
    due_on = serializers.DateField(allow_null=True)
    overdue = serializers.BooleanField()
    action_url = serializers.CharField()


class WorkListView(generics.GenericAPIView):
    serializer_class = WorkItemSerializer
    @extend_schema(parameters=[OpenApiParameter("kind", OpenApiTypes.STR, enum=["cases", "requests", "decisions"])])
    def get(self, request):
        if set(request.query_params) - {"kind", "page", "page_size", "format"}:
            raise ValidationError({"filters": ["Filtre non autorisé."]})
        memberships = list(active_memberships(request.user).filter(role__in=[Membership.Role.MANAGER, Membership.Role.INVESTIGATOR]).select_related("unit"))
        if not memberships:
            raise PermissionDenied()
        kind = request.query_params.get("kind", "cases")
        if kind == "cases":
            queryset = visible_cases(request.user).filter(assignee=request.user).select_related("unit").order_by("-updated_at", "id")
            page = self.paginate_queryset(queryset)
            results = [{"kind": "case", "id": str(obj.pk), "case": str(obj.pk), "reference": obj.reference, "status": obj.status, "next_action": obj.next_action, "action_url": f"/api/v1/dossiers/{obj.pk}/"} for obj in page]
        elif kind == "requests":
            queryset = CommunicationRequest.objects.filter(case__in=visible_cases(request.user)).filter(Q(author=request.user) | Q(case__assignee=request.user)).exclude(state=CommunicationRequest.State.ISSUED).select_related("case").annotate(was_returned=Exists(RequestEvent.objects.filter(request_id=OuterRef("pk"), kind="returned"))).order_by("due_on", "id")
            page = self.paginate_queryset(queryset)
            today = timezone.localdate()
            results = [{"kind": "request", "id": str(obj.pk), "case": str(obj.case_id), "status": obj.state, "due_on": obj.due_on, "overdue": bool(obj.due_on and obj.due_on < today), "returned": obj.was_returned and obj.state == CommunicationRequest.State.DRAFT, "internal_alert": bool(obj.due_on and obj.due_on < today), "action_url": f"/api/v1/demandes/{obj.pk}/"} for obj in page]
        elif kind == "decisions":
            queryset = Decision.objects.filter(case__in=visible_cases(request.user), author=request.user, state__in=[Decision.State.PROPOSED, Decision.State.RETURNED]).order_by("-updated_at", "-id")
            page = self.paginate_queryset(queryset)
            results = [{"kind": "decision", "id": str(obj.pk), "case": str(obj.case_id), "status": obj.state, "returned": obj.state == Decision.State.RETURNED, "internal_alert": obj.state == Decision.State.RETURNED, "action_url": f"/api/v1/decisions/{obj.pk}/"} for obj in page]
        else:
            raise ValidationError({"kind": ["Type de travail invalide."]})
        with transaction.atomic():
            for unit in {membership.unit for membership in memberships}:
                record(request, action="work.list", unit=unit, details={"kind": kind})
        return self.get_paginated_response(results)


class ToValidateView(generics.GenericAPIView):
    serializer_class = ValidationItemSerializer
    @extend_schema(parameters=[OpenApiParameter("kind", OpenApiTypes.STR, enum=["requests", "decisions"])])
    def get(self, request):
        if set(request.query_params) - {"kind", "page", "page_size", "format"}:
            raise ValidationError({"filters": ["Filtre non autorisé."]})
        memberships = list(active_memberships(request.user).filter(role=Membership.Role.MANAGER).select_related("unit"))
        if not memberships:
            raise PermissionDenied()
        kind = request.query_params.get("kind", "requests")
        if kind not in {"requests", "decisions"}:
            raise ValidationError({"kind": ["Type de validation invalide."]})
        permitted = Q(pk__in=[])
        for membership in memberships:
            delegation = Delegation.Action.REQUEST_VALIDATE if kind == "requests" else Delegation.Action.DECISION_VALIDATE
            if has_delegation(request.user, delegation, membership.unit):
                permitted |= Q(case__unit=membership.unit, case__classification__lte=membership.clearance)
        if kind == "requests":
            queryset = CommunicationRequest.objects.filter(state=CommunicationRequest.State.SUBMITTED, case__in=visible_cases(request.user)).filter(permitted).exclude(author=request.user).select_related("case__unit").distinct().order_by("created_at", "id")
        else:
            queryset = Decision.objects.filter(state=Decision.State.PROPOSED, case__in=visible_cases(request.user)).filter(permitted).exclude(author=request.user).select_related("case__unit").distinct().order_by("created_at", "id")
        page = self.paginate_queryset(queryset)
        today = timezone.localdate()
        if kind == "requests":
            results = [{"id": str(obj.pk), "case": str(obj.case_id), "status": obj.state, "due_on": obj.due_on, "overdue": bool(obj.due_on and obj.due_on < today), "action_url": f"/api/v1/demandes/{obj.pk}/valider/"} for obj in page]
        else:
            results = [{"id": str(obj.pk), "case": str(obj.case_id), "status": obj.state, "due_on": None, "overdue": False, "action_url": f"/api/v1/decisions/{obj.pk}/valider/"} for obj in page]
        with transaction.atomic():
            for unit in {membership.unit for membership in memberships}:
                record(request, action="work.validation.list", unit=unit, details={"kind": kind})
        return self.get_paginated_response(results)
