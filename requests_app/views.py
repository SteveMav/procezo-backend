import uuid

from django.db import transaction
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from audit.service import record
from identity.policy import can, visible_cases

from .models import ActVersion, CommunicationRequest, RequestResponse, RequestedItem
from .serializers import (
    ActSerializer, AssessmentInputSerializer, AssessmentSerializer, EventSerializer,
    IssueSerializer, PrepareSerializer, RectifySerializer, RequestCreateSerializer,
    RequestSerializer, RequestUpdateSerializer, ResponseCreateSerializer,
    ResponseSerializer, RequestReturnSerializer, SignSerializer, TransitionSerializer,
)
from .service import (
    act_file, assess_item, create_request, create_response, issue, prepare_act,
    rectify_links, return_request, sign, submit, update_request, validate,
)


class RequestViewSet(viewsets.GenericViewSet):
    serializer_class = RequestSerializer
    lookup_value_regex = "[0-9a-f-]{36}"

    def get_queryset(self):
        return CommunicationRequest.objects.filter(case__in=visible_cases(self.request.user)).select_related("case__unit", "author", "issuance").prefetch_related("items", "acts")

    def get_object(self):
        obj = super().get_object()
        if not can(self.request.user, "case.read", obj.case):
            raise PermissionDenied()
        return obj

    def _validated(self, serializer_class, data):
        serializer = serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data

    @extend_schema(parameters=[OpenApiParameter("case", OpenApiTypes.UUID, required=True)], responses=RequestSerializer(many=True))
    def list(self, request):
        if set(request.query_params) - {"case", "page", "page_size", "format"}:
            raise ValidationError({"filters": ["Filtre non autorisé."]})
        try:
            case_id = uuid.UUID(request.query_params["case"])
        except (KeyError, ValueError, TypeError):
            raise ValidationError({"case": ["Identifiant de dossier requis."]})
        case = get_object_or_404(visible_cases(request.user), pk=case_id)
        page = self.paginate_queryset(self.get_queryset().filter(case=case))
        with transaction.atomic():
            record(request, action="request.list", unit=case.unit, resource=case)
        return self.get_paginated_response(RequestSerializer(page, many=True).data)

    @extend_schema(responses=RequestSerializer)
    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        with transaction.atomic():
            record(request, action="request.read", unit=obj.unit, resource=obj.case, details={"request_id": str(obj.pk)})
        return Response(RequestSerializer(obj).data)

    @extend_schema(request=RequestCreateSerializer, responses={201: RequestSerializer})
    def create(self, request):
        data = self._validated(RequestCreateSerializer, request.data)
        case = get_object_or_404(visible_cases(request.user), pk=data["case"])
        obj = create_request(request, case, data)
        return Response(RequestSerializer(obj).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=RequestUpdateSerializer, responses=RequestSerializer)
    def partial_update(self, request, *args, **kwargs):
        obj = self.get_object()
        return Response(RequestSerializer(update_request(request, obj, self._validated(RequestUpdateSerializer, request.data))).data)

    @extend_schema(responses=OpenApiTypes.OBJECT)
    @action(detail=True, methods=["get"], url_path="apercu")
    def preview(self, request, *args, **kwargs):
        obj = self.get_object()
        with transaction.atomic():
            record(request, action="request.preview.read", unit=obj.unit, resource=obj.case, details={"request_id": str(obj.pk)})
        return Response({"project_only": True, "reference": obj.case.reference, "target_type": obj.target_type, "target_name": obj.target_name, "represented_name": obj.represented_name, "subject": obj.subject, "items": [{"number": item.number, "label": item.label} for item in obj.items.all()]})

    @extend_schema(request=PrepareSerializer, responses=ActSerializer)
    @action(detail=True, methods=["post"], url_path="preparer")
    def prepare(self, request, *args, **kwargs):
        obj = self.get_object()
        data = self._validated(PrepareSerializer, request.data)
        act = prepare_act(request, obj, **data)
        return Response(ActSerializer(act).data)

    @extend_schema(request=TransitionSerializer, responses=RequestSerializer)
    @action(detail=True, methods=["post"], url_path="soumettre")
    def submit(self, request, *args, **kwargs):
        obj = self.get_object()
        data = self._validated(TransitionSerializer, request.data)
        return Response(RequestSerializer(submit(request, obj, data["version"])).data)

    @extend_schema(request=TransitionSerializer, responses=RequestSerializer)
    @action(detail=True, methods=["post"], url_path="valider")
    def validate(self, request, *args, **kwargs):
        obj = self.get_object()
        data = self._validated(TransitionSerializer, request.data)
        return Response(RequestSerializer(validate(request, obj, data["version"])).data)

    @extend_schema(request=RequestReturnSerializer, responses=RequestSerializer)
    @action(detail=True, methods=["post"], url_path="retourner")
    def return_for_changes(self, request, *args, **kwargs):
        obj = self.get_object()
        data = self._validated(RequestReturnSerializer, request.data)
        return Response(RequestSerializer(return_request(request, obj, **data)).data)

    @extend_schema(request=SignSerializer, responses=RequestSerializer)
    @action(detail=True, methods=["post"], url_path="constater-signature")
    def record_signature(self, request, *args, **kwargs):
        obj = self.get_object()
        data = self._validated(SignSerializer, request.data)
        return Response(RequestSerializer(sign(request, obj, **data)).data)

    @extend_schema(request=IssueSerializer, responses=RequestSerializer)
    @action(detail=True, methods=["post"], url_path="constater-emission")
    def record_issuance(self, request, *args, **kwargs):
        obj = self.get_object()
        data = self._validated(IssueSerializer, request.data)
        return Response(RequestSerializer(issue(request, obj, data["version"], data["idempotency_key"], data["dispatch_proof"], data["sent_at"])).data)

    @extend_schema(responses=EventSerializer(many=True))
    @action(detail=True, methods=["get"], url_path="historique")
    def history(self, request, *args, **kwargs):
        obj = self.get_object()
        page = self.paginate_queryset(obj.events.all())
        with transaction.atomic():
            record(request, action="request.history.read", unit=obj.unit, resource=obj.case, details={"request_id": str(obj.pk)})
        return self.get_paginated_response(EventSerializer(page, many=True).data)

    @extend_schema(request=ResponseCreateSerializer, responses={201: ResponseSerializer})
    @action(detail=True, methods=["post"], url_path="reponses")
    def responses(self, request, *args, **kwargs):
        obj = self.get_object()
        data = self._validated(ResponseCreateSerializer, request.data)
        response = create_response(request, obj, data)
        return Response(ResponseSerializer(response).data, status=201)

    @extend_schema(responses=ResponseSerializer(many=True))
    @responses.mapping.get
    def list_responses(self, request, *args, **kwargs):
        obj = self.get_object()
        page = self.paginate_queryset(obj.responses.all().prefetch_related("item_links", "annexes"))
        with transaction.atomic():
            record(request, action="request.responses.read", unit=obj.unit, resource=obj.case, details={"request_id": str(obj.pk)})
        return self.get_paginated_response(ResponseSerializer(page, many=True).data)

    @extend_schema(request=AssessmentInputSerializer, responses={201: AssessmentSerializer})
    @action(detail=True, methods=["post"], url_path=r"elements/(?P<item_id>[0-9a-f-]{36})/appreciations")
    def assess(self, request, item_id=None, *args, **kwargs):
        obj = self.get_object()
        item = get_object_or_404(obj.items.all(), pk=item_id)
        data = self._validated(AssessmentInputSerializer, request.data)
        assessment = assess_item(request, item, data)
        return Response(AssessmentSerializer(assessment).data, status=201)

    @extend_schema(responses=AssessmentSerializer(many=True))
    @assess.mapping.get
    def list_assessments(self, request, item_id=None, *args, **kwargs):
        obj = self.get_object()
        item = get_object_or_404(obj.items.all(), pk=item_id)
        page = self.paginate_queryset(item.assessments.all())
        with transaction.atomic():
            record(request, action="request.item.assessments.read", unit=obj.unit, resource=obj.case, details={"item_id": str(item.pk)})
        return self.get_paginated_response(AssessmentSerializer(page, many=True).data)


class ActViewSet(viewsets.GenericViewSet):
    serializer_class = ActSerializer
    lookup_value_regex = "[0-9a-f-]{36}"

    def get_queryset(self):
        return ActVersion.objects.filter(request__case__in=visible_cases(self.request.user)).select_related("request__case__unit", "imported_document")

    @extend_schema(responses={(200, "application/pdf"): bytes})
    @action(detail=True, methods=["get"], url_path="telecharger")
    def download(self, request, *args, **kwargs):
        act = self.get_object()
        if not can(request.user, "case.read", act.request.case):
            raise PermissionDenied()
        path = act_file(act)
        try:
            stream = path.open("rb")
        except OSError:
            raise ValidationError({"act": ["Fichier indisponible."]})
        try:
            with transaction.atomic():
                record(request, action="request.act.download", unit=act.request.unit, resource=act.request.case, details={"act_id": str(act.pk)})
            response = FileResponse(stream, as_attachment=True, filename=f"projet-{act.pk}.pdf", content_type="application/pdf")
            response["Cache-Control"] = "no-store"
            response["X-Content-Type-Options"] = "nosniff"
            return response
        except Exception:
            stream.close()
            raise


class ResponseViewSet(viewsets.GenericViewSet):
    serializer_class = ResponseSerializer
    lookup_value_regex = "[0-9a-f-]{36}"

    def get_queryset(self):
        return RequestResponse.objects.filter(request__case__in=visible_cases(self.request.user)).select_related("request__case__unit", "letter").prefetch_related("item_links", "annexes")

    @extend_schema(responses=ResponseSerializer)
    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        with transaction.atomic():
            record(request, action="request.response.read", unit=obj.request.unit, resource=obj.request.case, details={"response_id": str(obj.pk)})
        return Response(ResponseSerializer(obj).data)

    @extend_schema(request=RectifySerializer, responses=ResponseSerializer)
    @action(detail=True, methods=["post"], url_path="rectifier-liens")
    def rectify(self, request, *args, **kwargs):
        obj = self.get_object()
        data = RectifySerializer(data=request.data)
        data.is_valid(raise_exception=True)
        return Response(ResponseSerializer(rectify_links(request, obj, data.validated_data)).data)
