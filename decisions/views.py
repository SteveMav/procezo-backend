import uuid

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema

from audit.service import record
from identity.policy import can, visible_cases

from .models import Decision, GelecTransfer
from .serializers import (
    ConfirmReceiptSerializer, DecisionCreateSerializer, DecisionEventSerializer,
    DecisionReturnSerializer, DecisionSerializer, DecisionTransitionSerializer,
    GelecTransferSerializer, TransferCreateSerializer, TransmitSerializer,
)
from .service import confirm_receipt, create_decision, prepare_transfer, transition_decision, transmit


def _case_filter(request):
    if set(request.query_params) - {"case", "page", "page_size", "format"}:
        raise ValidationError({"filters": ["Filtre non autorisé."]})
    try:
        case_id = uuid.UUID(request.query_params["case"])
    except (KeyError, ValueError, TypeError):
        raise ValidationError({"case": ["Identifiant de dossier requis."]})
    return get_object_or_404(visible_cases(request.user), pk=case_id)


def _validated(serializer_class, data):
    serializer = serializer_class(data=data)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


class DecisionViewSet(viewsets.GenericViewSet):
    serializer_class = DecisionSerializer
    lookup_value_regex = "[0-9a-f-]{36}"

    def get_queryset(self):
        return Decision.objects.filter(case__in=visible_cases(self.request.user)).select_related("case__unit", "author", "validator").prefetch_related("events")

    def get_object(self):
        obj = super().get_object()
        if not can(self.request.user, "case.read", obj.case):
            raise PermissionDenied()
        return obj

    @extend_schema(parameters=[OpenApiParameter("case", OpenApiTypes.UUID, required=True)], responses=DecisionSerializer(many=True))
    def list(self, request):
        case = _case_filter(request)
        page = self.paginate_queryset(self.get_queryset().filter(case=case))
        with transaction.atomic():
            record(request, action="decision.list", unit=case.unit, resource=case)
        return self.get_paginated_response(DecisionSerializer(page, many=True).data)

    @extend_schema(responses=DecisionSerializer)
    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        with transaction.atomic():
            record(request, action="decision.read", unit=obj.unit, resource=obj.case, details={"decision_id": str(obj.pk)})
        return Response(DecisionSerializer(obj).data)

    @extend_schema(request=DecisionCreateSerializer, responses={201: DecisionSerializer})
    def create(self, request):
        data = _validated(DecisionCreateSerializer, request.data)
        case = get_object_or_404(visible_cases(request.user), pk=data["case"])
        obj = create_decision(request, case, data)
        return Response(DecisionSerializer(obj).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=DecisionTransitionSerializer, responses=DecisionSerializer)
    @action(detail=True, methods=["post"], url_path="valider")
    def validate(self, request, *args, **kwargs):
        obj = self.get_object()
        data = _validated(DecisionTransitionSerializer, request.data)
        return Response(DecisionSerializer(transition_decision(request, obj, version=data["version"], target=Decision.State.VALIDATED)).data)

    @extend_schema(request=DecisionReturnSerializer, responses=DecisionSerializer)
    @action(detail=True, methods=["post"], url_path="retourner")
    def return_for_changes(self, request, *args, **kwargs):
        obj = self.get_object()
        data = _validated(DecisionReturnSerializer, request.data)
        return Response(DecisionSerializer(transition_decision(request, obj, target=Decision.State.RETURNED, **data)).data)

    @extend_schema(responses=DecisionEventSerializer(many=True))
    @action(detail=True, methods=["get"], url_path="historique")
    def history(self, request, *args, **kwargs):
        obj = self.get_object()
        page = self.paginate_queryset(obj.events.all())
        with transaction.atomic():
            record(request, action="decision.history.read", unit=obj.unit, resource=obj.case, details={"decision_id": str(obj.pk)})
        return self.get_paginated_response(DecisionEventSerializer(page, many=True).data)


class GelecTransferViewSet(viewsets.GenericViewSet):
    serializer_class = GelecTransferSerializer
    lookup_value_regex = "[0-9a-f-]{36}"

    def get_queryset(self):
        return GelecTransfer.objects.filter(decision__case__in=visible_cases(self.request.user)).select_related("decision__case__unit", "transmission_proof", "receipt_proof")

    def get_object(self):
        obj = super().get_object()
        if not can(self.request.user, "case.read", obj.case):
            raise PermissionDenied()
        return obj

    @extend_schema(parameters=[OpenApiParameter("case", OpenApiTypes.UUID, required=True)], responses=GelecTransferSerializer(many=True))
    def list(self, request):
        case = _case_filter(request)
        page = self.paginate_queryset(self.get_queryset().filter(decision__case=case).order_by("-prepared_at", "-id"))
        with transaction.atomic():
            record(request, action="gelec.list", unit=case.unit, resource=case)
        return self.get_paginated_response(GelecTransferSerializer(page, many=True).data)

    @extend_schema(responses=GelecTransferSerializer)
    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        with transaction.atomic():
            record(request, action="gelec.read", unit=obj.unit, resource=obj.case, details={"transfer_id": str(obj.pk)})
        return Response(GelecTransferSerializer(obj).data)

    @extend_schema(request=TransferCreateSerializer, responses={201: GelecTransferSerializer, 200: GelecTransferSerializer})
    def create(self, request):
        data = _validated(TransferCreateSerializer, request.data)
        decision = get_object_or_404(Decision.objects.filter(case__in=visible_cases(request.user)).select_related("case__unit"), pk=data["decision"])
        transfer, created = prepare_transfer(request, decision)
        return Response(GelecTransferSerializer(transfer).data, status=201 if created else 200)

    @extend_schema(request=TransmitSerializer, responses=GelecTransferSerializer)
    @action(detail=True, methods=["post"], url_path="transmettre")
    def record_transmission(self, request, *args, **kwargs):
        obj = self.get_object()
        data = _validated(TransmitSerializer, request.data)
        return Response(GelecTransferSerializer(transmit(request, obj, data)).data)

    @extend_schema(request=ConfirmReceiptSerializer, responses=GelecTransferSerializer)
    @action(detail=True, methods=["post"], url_path="confirmer-reception")
    def record_receipt(self, request, *args, **kwargs):
        obj = self.get_object()
        data = _validated(ConfirmReceiptSerializer, request.data)
        return Response(GelecTransferSerializer(confirm_receipt(request, obj, data)).data)
