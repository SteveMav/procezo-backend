import uuid

from django.db import transaction
from django.db.models import CharField, PositiveIntegerField, UUIDField, Value
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from drf_spectacular.utils import OpenApiParameter, extend_schema
from drf_spectacular.types import OpenApiTypes

from audit.service import record
from identity.models import Membership, Unit
from identity.policy import active_memberships, can, visible_cases

from .models import Case
from .serializers import AssignmentSerializer, CaseAssignmentReadSerializer, CaseCreateSerializer, CaseSerializer, CaseTimelineSerializer, CaseUpdateSerializer
from .service import assign_case, create_case, update_case


class CaseViewSet(viewsets.GenericViewSet):
    serializer_class = CaseSerializer
    lookup_value_regex = "[0-9a-f-]{36}"

    def get_queryset(self):
        return visible_cases(self.request.user).select_related("unit", "assignee", "created_by")

    def get_object(self):
        case = super().get_object()
        if not can(self.request.user, "case.read", case):
            raise PermissionDenied()
        return case

    @extend_schema(
        parameters=[
            OpenApiParameter("unit", OpenApiTypes.UUID),
            OpenApiParameter("status", OpenApiTypes.STR),
            OpenApiParameter("reference", OpenApiTypes.STR),
            OpenApiParameter("ordering", OpenApiTypes.STR, enum=["created_at", "-created_at", "reference", "-reference"]),
        ],
        responses=CaseSerializer(many=True),
    )
    def list(self, request):
        queryset = self.get_queryset()
        allowed_filters = {"unit", "status", "reference", "ordering", "page", "page_size", "format"}
        unknown = set(request.query_params) - allowed_filters
        if unknown:
            raise ValidationError({"filters": ["Filtre non autorisé."]})
        if "unit" in request.query_params:
            try:
                unit_id = uuid.UUID(request.query_params["unit"])
            except (ValueError, TypeError):
                raise ValidationError({"unit": ["Identifiant invalide."]})
            queryset = queryset.filter(unit_id=unit_id)
        if "status" in request.query_params:
            if request.query_params["status"] not in Case.Status.values:
                raise ValidationError({"status": ["Statut invalide."]})
            queryset = queryset.filter(status=request.query_params["status"])
        if "reference" in request.query_params:
            queryset = queryset.filter(reference__icontains=request.query_params["reference"][:24])
        ordering = request.query_params.get("ordering", "-created_at")
        if ordering not in {"created_at", "-created_at", "reference", "-reference"}:
            raise ValidationError({"ordering": ["Tri non autorisé."]})
        queryset = queryset.order_by(ordering, "id")
        page = self.paginate_queryset(queryset)
        audit_units = {case.unit_id: case.unit for case in page}
        if not audit_units:
            fallback_unit = self._audit_unit(request)
            audit_units[fallback_unit.pk] = fallback_unit
        with transaction.atomic():
            for unit in audit_units.values():
                record(request, action="case.list", unit=unit, details={"filters": sorted(set(request.query_params) & {"unit", "status", "reference"})})
        return self.get_paginated_response(CaseSerializer(page, many=True).data)

    def _audit_unit(self, request):
        # A list can span units; use an active membership unit as the audit scope.
        membership = active_memberships(request.user).filter(role__in=[Membership.Role.MANAGER, Membership.Role.INVESTIGATOR]).select_related("unit").first()
        if membership is None:
            raise PermissionDenied()
        return membership.unit

    @extend_schema(responses=CaseSerializer)
    def retrieve(self, request, *args, **kwargs):
        case = self.get_object()
        with transaction.atomic():
            record(request, action="case.read", unit=case.unit, resource=case)
        return Response(CaseSerializer(case).data)

    @extend_schema(request=CaseCreateSerializer, responses={201: CaseSerializer})
    def create(self, request):
        serializer = CaseCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        unit = get_object_or_404(Unit.objects.filter(pk__in=active_memberships(request.user).values("unit_id")), pk=data["unit"])
        case = create_case(request, unit=unit, classification=int(data["classification"]), assignee=data["assignee"], next_action=data["next_action"], assignment_reason=data["assignment_reason"])
        return Response(CaseSerializer(case).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=CaseUpdateSerializer, responses=CaseSerializer)
    def partial_update(self, request, *args, **kwargs):
        case = self.get_object()
        serializer = CaseUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        case = update_case(request, case, **serializer.validated_data)
        return Response(CaseSerializer(case).data)

    @extend_schema(request=AssignmentSerializer, responses=CaseSerializer)
    @action(detail=True, methods=["post"], url_path="affectations")
    def assignments(self, request, *args, **kwargs):
        case = self.get_object()
        serializer = AssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        case = assign_case(request, case, **serializer.validated_data)
        return Response(CaseSerializer(case).data)

    @extend_schema(responses=CaseAssignmentReadSerializer(many=True))
    @assignments.mapping.get
    def list_assignments(self, request, *args, **kwargs):
        case = self.get_object()
        page = self.paginate_queryset(case.assignments.all())
        with transaction.atomic():
            record(request, action="case.assignments.read", unit=case.unit, resource=case)
        return self.get_paginated_response(CaseAssignmentReadSerializer(page, many=True).data)

    @extend_schema(responses=CaseTimelineSerializer(many=True))
    @action(detail=True, methods=["get"], url_path="chronologie")
    def timeline(self, request, *args, **kwargs):
        case = self.get_object()
        columns = ("id", "kind", "actor_id", "next_action", "status", "version", "created_at", "resource_id")
        actions = case.actions.order_by().annotate(resource_id=Value(None, output_field=UUIDField())).values(*columns)
        events = case.inspection_events.order_by().annotate(
            next_action=Value(None, output_field=CharField(max_length=240)),
            status=Value(None, output_field=CharField(max_length=20)),
            version=Value(None, output_field=PositiveIntegerField()),
        ).values(*columns)
        page = self.paginate_queryset(actions.union(events).order_by("created_at", "id"))
        rows = [{"id": row["id"], "kind": row["kind"], "actor": row["actor_id"], "next_action": row["next_action"], "status": row["status"], "version": row["version"], "created_at": row["created_at"], "resource_id": row["resource_id"]} for row in page]
        with transaction.atomic():
            record(request, action="case.timeline.read", unit=case.unit, resource=case)
        return self.get_paginated_response(CaseTimelineSerializer(rows, many=True).data)
