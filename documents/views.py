import hashlib

from django.db import transaction
from django.db.models import Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from audit.service import record
from cases.models import Case
from identity.policy import can, visible_cases, visible_intelligence
from platform_api.errors import DependencyUnavailable

from .models import Document, FileOperation
from .serializers import DocumentSerializer, UploadSerializer
from .service import private_path, rescan_document, upload_document


def authorized_parent(request, data, operation):
    if data.get("case"):
        parent = get_object_or_404(visible_cases(request.user), pk=data["case"])
        action_name = "case.update" if operation == "upload" else "case.read"
    else:
        parent = get_object_or_404(visible_intelligence(request.user), pk=data["intelligence"])
        # Intelligence attachments may contain identifying material. Keep them
        # behind the dedicated source delegations until DGDA defines categories.
        action_name = "source.write" if operation == "upload" else "source.read"
    if not can(request.user, action_name, parent):
        raise PermissionDenied()
    return parent


class DocumentViewSet(viewsets.GenericViewSet):
    serializer_class = DocumentSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    lookup_value_regex = "[0-9a-f-]{36}"

    def get_queryset(self):
        return Document.objects.filter(
            Q(case__in=visible_cases(self.request.user)) |
            Q(intelligence__in=visible_intelligence(self.request.user))
        ).select_related("case__unit", "intelligence__unit")

    def get_object(self):
        obj = super().get_object()
        authorized_parent(self.request, {"case": obj.case_id, "intelligence": obj.intelligence_id}, "read")
        return obj

    @extend_schema(responses=DocumentSerializer(many=True))
    def list(self, request):
        allowed = {"case", "intelligence", "page", "page_size", "format"}
        if set(request.query_params) - allowed:
            raise ValidationError({"filters": ["Filtre non autorisé."]})
        serializer = ParentFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        parent = authorized_parent(request, data, "read")
        queryset = self.get_queryset().filter(**({"case": parent} if isinstance(parent, Case) else {"intelligence": parent}))
        page = self.paginate_queryset(queryset)
        with transaction.atomic():
            record(request, action="document.list", unit=parent.unit, resource=parent)
        return self.get_paginated_response(DocumentSerializer(page, many=True).data)

    @extend_schema(responses=DocumentSerializer)
    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        with transaction.atomic():
            record(request, action="document.read", unit=obj.parent.unit, resource=obj.parent, details={"document_id": str(obj.pk)})
        return Response(DocumentSerializer(obj).data)

    @extend_schema(request=UploadSerializer, responses={201: DocumentSerializer})
    def create(self, request):
        serializer = UploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        parent = authorized_parent(request, data, "upload")
        obj = upload_document(request, parent=parent, upload=data["file"])
        return Response(DocumentSerializer(obj).data, status=201)

    @extend_schema(responses=DocumentSerializer)
    @action(detail=True, methods=["post"], url_path="reanalyser")
    def rescan(self, request, *args, **kwargs):
        obj = self.get_object()
        authorized_parent(request, {"case": obj.case_id, "intelligence": obj.intelligence_id}, "upload")
        return Response(DocumentSerializer(rescan_document(request, obj)).data)

    @extend_schema(responses={(200, "application/octet-stream"): bytes})
    @action(detail=True, methods=["get"], url_path="telecharger")
    def download(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.state != Document.State.ACCEPTED:
            raise PermissionDenied("Pièce indisponible.")
        try:
            stream = private_path(obj.storage_name).open("rb")
        except OSError:
            self._mark_missing(request, obj)
            raise DependencyUnavailable()
        try:
            digest = hashlib.sha256()
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
            if digest.hexdigest() != obj.sha256:
                stream.close()
                self._mark_missing(request, obj)
                raise DependencyUnavailable()
            stream.seek(0)
            with transaction.atomic():
                authorized_parent(request, {"case": obj.case_id, "intelligence": obj.intelligence_id}, "read")
                record(request, action="document.download", unit=obj.parent.unit, resource=obj.parent, details={"document_id": str(obj.pk)})
            response = FileResponse(stream, as_attachment=True, filename=f"{obj.pk}", content_type="application/octet-stream")
            response["Cache-Control"] = "no-store"
            response["X-Content-Type-Options"] = "nosniff"
            return response
        except Exception:
            stream.close()
            raise

    def _mark_missing(self, request, obj):
        with transaction.atomic():
            if Document.objects.filter(pk=obj.pk, state=Document.State.ACCEPTED).update(state=Document.State.MISSING):
                FileOperation.objects.create(document=obj, kind="integrity", result="missing")
                record(request, action="document.missing", unit=obj.parent.unit, resource=obj.parent, details={"document_id": str(obj.pk)})


class ParentFilterSerializer(serializers.Serializer):
    case = serializers.UUIDField(required=False)
    intelligence = serializers.UUIDField(required=False)

    def validate(self, attrs):
        if ("case" in attrs) == ("intelligence" in attrs):
            raise serializers.ValidationError({"parent": ["Un seul parent est requis."]})
        return attrs
