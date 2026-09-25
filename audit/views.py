import uuid

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import ListAPIView
from rest_framework import serializers
from drf_spectacular.utils import OpenApiParameter, extend_schema
from drf_spectacular.types import OpenApiTypes

from identity.models import Membership, Unit
from identity.policy import active_memberships, can
from .models import AuditEvent
from .service import record


class AuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEvent
        fields = ["id", "occurred_at", "actor", "unit", "classification", "action", "resource_type", "resource_id", "request_id", "details"]


class AuditListView(ListAPIView):
    serializer_class = AuditEventSerializer

    @extend_schema(parameters=[OpenApiParameter("unit", OpenApiTypes.UUID, required=True)])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        raw_unit = self.request.query_params.get("unit")
        if not raw_unit:
            raise ValidationError({"unit": ["Unité requise."]})
        try:
            unit_id = uuid.UUID(raw_unit)
        except (ValueError, TypeError):
            raise ValidationError({"unit": ["Identifiant invalide."]})
        unit = get_object_or_404(Unit.objects.filter(pk__in=active_memberships(self.request.user).values("unit_id")), pk=unit_id)
        if not can(self.request.user, "audit.read", context={"unit": unit, "classification": 0}):
            raise PermissionDenied()
        self.audit_unit = unit
        clearance = max(active_memberships(self.request.user, unit=unit).filter(role=Membership.Role.AUDITOR).values_list("clearance", flat=True))
        return AuditEvent.objects.filter(unit=unit, classification__lte=clearance)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        with transaction.atomic():
            record(request, action="audit.read", unit=self.audit_unit)
        return self.get_paginated_response(self.get_serializer(page, many=True).data)
