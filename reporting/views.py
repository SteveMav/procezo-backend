from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from audit.service import record
from identity.models import Membership, Unit
from identity.policy import active_memberships

from .serializers import DetailQuerySerializer, DetailSerializer, PeriodQuerySerializer, StatisticsSerializer
from .service import DEFINITIONS, DEFINITION_VERSION, can_read_distribution, dashboard, object_url, rows_for


PERIOD_PARAMETERS = [
    OpenApiParameter("unit", OpenApiTypes.UUID, required=True),
    OpenApiParameter("start", OpenApiTypes.DATE, required=True),
    OpenApiParameter("end", OpenApiTypes.DATE, required=True),
]


class StatisticsBase(GenericAPIView):
    def scope(self, request, serializer_class):
        allowed = {"unit", "start", "end", "format"}
        if serializer_class is DetailQuerySerializer:
            allowed |= {"provenance", "page", "page_size"}
        if set(request.query_params) - allowed:
            raise ValidationError({"filters": ["Filtre non autorisé."]})
        serializer = serializer_class(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        membership_units = active_memberships(request.user).filter(role__in=[Membership.Role.MANAGER, Membership.Role.INVESTIGATOR]).values("unit_id")
        unit = get_object_or_404(Unit.objects.filter(pk__in=membership_units), pk=data["unit"])
        return unit, data


class StatisticsView(StatisticsBase):
    serializer_class = StatisticsSerializer

    @extend_schema(operation_id="statistics_summary", parameters=PERIOD_PARAMETERS, responses=StatisticsSerializer)
    def get(self, request):
        unit, data = self.scope(request, PeriodQuerySerializer)
        with transaction.atomic():
            result = dashboard(request.user, unit, data["start"], data["end"])
            record(request, action="statistics.read", unit=unit, details={"definition_version": DEFINITION_VERSION, "start": data["start"].isoformat(), "end": data["end"].isoformat()})
        return Response(StatisticsSerializer(result).data)


class StatisticsDetailView(StatisticsBase):
    serializer_class = DetailSerializer

    @extend_schema(operation_id="statistics_detail", parameters=PERIOD_PARAMETERS + [
        OpenApiParameter("provenance", OpenApiTypes.STR),
        OpenApiParameter("page", OpenApiTypes.INT),
        OpenApiParameter("page_size", OpenApiTypes.INT),
    ], responses=DetailSerializer)
    def get(self, request, key):
        if key not in DEFINITIONS:
            from django.http import Http404
            raise Http404
        unit, data = self.scope(request, DetailQuerySerializer)
        if key in {"intelligence.distributed", "intelligence.with_returns"} and not can_read_distribution(request.user, unit):
            from django.http import Http404
            raise Http404
        if "provenance" in data and not key.startswith("intelligence."):
            raise ValidationError({"provenance": ["Filtre non autorisé pour cet indicateur."]})
        with transaction.atomic():
            rows = rows_for(request.user, unit, data["start"], data["end"], key, provenance=data.get("provenance"))
            page = self.paginate_queryset(rows)
            result = {"key": key, "label": DEFINITIONS[key][0], "definition": DEFINITIONS[key][1], "definition_version": DEFINITION_VERSION, "unit": unit.pk, "start": data["start"], "end": data["end"], "count": self.paginator.page.paginator.count, "next": self.paginator.get_next_link(), "previous": self.paginator.get_previous_link(), "results": [{"id": obj.pk, "url": object_url(key, obj.pk)} for obj in page]}
            if "provenance" in data:
                result["provenance"] = data["provenance"]
            record(request, action="statistics.detail.read", unit=unit, details={"indicator": key, "definition_version": DEFINITION_VERSION, "start": data["start"].isoformat(), "end": data["end"].isoformat()})
        return Response(DetailSerializer(result).data)
