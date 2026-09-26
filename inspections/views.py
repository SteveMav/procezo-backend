import uuid

from django.db import transaction
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from drf_spectacular.utils import OpenApiParameter, extend_schema
from drf_spectacular.types import OpenApiTypes

from audit.service import record
from identity.policy import can, visible_cases
from platform_api.errors import DependencyUnavailable

from .models import Defense, InspectionMission, ObservationSheet, SheetProject
from .serializers import DefenseInputSerializer, DefenseSerializer, MissionInputSerializer, MissionSerializer, ObservationAssessmentInputSerializer, ObservationAssessmentSerializer, ProjectSerializer, SheetInputSerializer, SheetSerializer, SheetUpdateSerializer, VersionSerializer
from .service import assess, create_defense, create_mission, create_sheet, prepare_project, project_file, update_sheet


def validated(serializer_class, data):
    serializer = serializer_class(data=data)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


def case_filter(request):
    if set(request.query_params) - {"case", "page", "page_size", "format"}:
        raise ValidationError({"filters": ["Filtre non autorisé."]})
    try:
        case_id = uuid.UUID(request.query_params["case"])
    except (KeyError, ValueError, TypeError):
        raise ValidationError({"case": ["Identifiant de dossier requis."]})
    case = get_object_or_404(visible_cases(request.user), pk=case_id)
    if not can(request.user, "case.read", case):
        raise PermissionDenied()
    return case


class MissionViewSet(viewsets.GenericViewSet):
    serializer_class = MissionSerializer
    lookup_value_regex = "[0-9a-f-]{36}"

    def get_queryset(self):
        return InspectionMission.objects.filter(case__in=visible_cases(self.request.user)).select_related("case__unit").prefetch_related("participants", "documents")

    @extend_schema(parameters=[OpenApiParameter("case", OpenApiTypes.UUID, required=True)], responses=MissionSerializer(many=True))
    def list(self, request):
        case = case_filter(request)
        page = self.paginate_queryset(self.get_queryset().filter(case=case))
        with transaction.atomic():
            record(request, action="inspection.mission.list", unit=case.unit, resource=case)
        return self.get_paginated_response(MissionSerializer(page, many=True).data)

    @extend_schema(responses=MissionSerializer)
    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        with transaction.atomic():
            record(request, action="inspection.mission.read", unit=obj.case.unit, resource=obj.case, details={"mission_id": str(obj.pk)})
        return Response(MissionSerializer(obj).data)

    @extend_schema(request=MissionInputSerializer, responses={201: MissionSerializer})
    def create(self, request):
        data = validated(MissionInputSerializer, request.data)
        case = get_object_or_404(visible_cases(request.user), pk=data.pop("case"))
        return Response(MissionSerializer(create_mission(request, case, data)).data, status=201)


class SheetViewSet(viewsets.GenericViewSet):
    serializer_class = SheetSerializer
    lookup_value_regex = "[0-9a-f-]{36}"

    def get_queryset(self):
        return ObservationSheet.objects.filter(case__in=visible_cases(self.request.user)).select_related("case__unit", "mission").prefetch_related("observations__documents", "projects")

    @extend_schema(parameters=[OpenApiParameter("case", OpenApiTypes.UUID, required=True)], responses=SheetSerializer(many=True))
    def list(self, request):
        case = case_filter(request)
        page = self.paginate_queryset(self.get_queryset().filter(case=case))
        with transaction.atomic():
            record(request, action="inspection.sheet.list", unit=case.unit, resource=case)
        return self.get_paginated_response(SheetSerializer(page, many=True).data)

    @extend_schema(responses=SheetSerializer)
    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        with transaction.atomic():
            record(request, action="inspection.sheet.read", unit=obj.case.unit, resource=obj.case, details={"sheet_id": str(obj.pk)})
        return Response(SheetSerializer(obj).data)

    @extend_schema(request=SheetInputSerializer, responses={201: SheetSerializer})
    def create(self, request):
        data = validated(SheetInputSerializer, request.data)
        case = get_object_or_404(visible_cases(request.user), pk=data.pop("case"))
        return Response(SheetSerializer(create_sheet(request, case, data)).data, status=201)

    @extend_schema(request=SheetUpdateSerializer, responses=SheetSerializer)
    def partial_update(self, request, *args, **kwargs):
        obj = self.get_object()
        return Response(SheetSerializer(update_sheet(request, obj, validated(SheetUpdateSerializer, request.data))).data)

    @extend_schema(responses=OpenApiTypes.OBJECT)
    @action(detail=True, methods=["get"], url_path="apercu")
    def preview(self, request, *args, **kwargs):
        obj = self.get_object()
        with transaction.atomic():
            record(request, action="inspection.sheet.preview.read", unit=obj.case.unit, resource=obj.case, details={"sheet_id": str(obj.pk)})
        return Response({"project_only": True, "reference": obj.case.reference, "origin": obj.origin, "mission": obj.mission_id, "recipient_address": obj.recipient_address, "concerned_party": obj.concerned_party, "facts": obj.facts, "observations": [{"number": item.number, "facts": item.facts, "documents": [str(doc.pk) for doc in item.documents.all()]} for item in obj.observations.all()]})

    @extend_schema(request=VersionSerializer, responses=ProjectSerializer)
    @action(detail=True, methods=["post"], url_path="preparer")
    def prepare(self, request, *args, **kwargs):
        obj = self.get_object()
        project = prepare_project(request, obj, validated(VersionSerializer, request.data)["version"])
        return Response(ProjectSerializer(project).data)

    @extend_schema(request=DefenseInputSerializer, responses={201: DefenseSerializer})
    @action(detail=True, methods=["post"], url_path="defenses")
    def defenses(self, request, *args, **kwargs):
        obj = self.get_object()
        return Response(DefenseSerializer(create_defense(request, obj, validated(DefenseInputSerializer, request.data))).data, status=201)

    @extend_schema(responses=DefenseSerializer(many=True))
    @defenses.mapping.get
    def list_defenses(self, request, *args, **kwargs):
        obj = self.get_object()
        page = self.paginate_queryset(obj.defenses.all().prefetch_related("annexes", "observations"))
        with transaction.atomic():
            record(request, action="inspection.defense.list", unit=obj.case.unit, resource=obj.case, details={"sheet_id": str(obj.pk)})
        return self.get_paginated_response(DefenseSerializer(page, many=True).data)

    @extend_schema(request=ObservationAssessmentInputSerializer, responses={201: ObservationAssessmentSerializer})
    @action(detail=True, methods=["post"], url_path=r"observations/(?P<observation_id>[0-9a-f-]{36})/appreciations")
    def assessments(self, request, observation_id=None, *args, **kwargs):
        obj = self.get_object()
        observation = get_object_or_404(obj.observations.all(), pk=observation_id)
        return Response(ObservationAssessmentSerializer(assess(request, observation, validated(ObservationAssessmentInputSerializer, request.data))).data, status=201)

    @extend_schema(responses=ObservationAssessmentSerializer(many=True))
    @assessments.mapping.get
    def list_assessments(self, request, observation_id=None, *args, **kwargs):
        obj = self.get_object()
        observation = get_object_or_404(obj.observations.all(), pk=observation_id)
        page = self.paginate_queryset(observation.assessments.all())
        with transaction.atomic():
            record(request, action="inspection.observation.assessments.read", unit=obj.case.unit, resource=obj.case, details={"observation_id": str(observation.pk)})
        return self.get_paginated_response(ObservationAssessmentSerializer(page, many=True).data)


class SheetProjectViewSet(viewsets.GenericViewSet):
    serializer_class = ProjectSerializer
    lookup_value_regex = "[0-9a-f-]{36}"

    def get_queryset(self):
        return SheetProject.objects.filter(sheet__case__in=visible_cases(self.request.user)).select_related("sheet__case__unit")

    @extend_schema(responses={(200, "application/pdf"): bytes})
    @action(detail=True, methods=["get"], url_path="telecharger")
    def download(self, request, *args, **kwargs):
        project = self.get_object()
        path = project_file(project)
        try:
            stream = path.open("rb")
        except OSError:
            raise DependencyUnavailable()
        try:
            with transaction.atomic():
                if not can(request.user, "case.read", project.sheet.case):
                    raise PermissionDenied()
                record(request, action="inspection.sheet.project.download", unit=project.sheet.case.unit, resource=project.sheet.case, details={"project_id": str(project.pk)})
            response = FileResponse(stream, as_attachment=True, filename=f"projet-feuille-{project.pk}.pdf", content_type="application/pdf")
            response["Cache-Control"] = "no-store"
            response["X-Content-Type-Options"] = "nosniff"
            return response
        except Exception:
            stream.close()
            raise


class DefenseViewSet(viewsets.GenericViewSet):
    serializer_class = DefenseSerializer
    lookup_value_regex = "[0-9a-f-]{36}"

    def get_queryset(self):
        return Defense.objects.filter(sheet__case__in=visible_cases(self.request.user)).select_related("sheet__case__unit").prefetch_related("annexes", "observations")

    @extend_schema(responses=DefenseSerializer)
    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        with transaction.atomic():
            record(request, action="inspection.defense.read", unit=obj.sheet.case.unit, resource=obj.sheet.case, details={"defense_id": str(obj.pk)})
        return Response(DefenseSerializer(obj).data)
