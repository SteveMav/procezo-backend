from datetime import date

from rest_framework import serializers


class PeriodQuerySerializer(serializers.Serializer):
    unit = serializers.UUIDField()
    start = serializers.DateField()
    end = serializers.DateField()

    def validate(self, attrs):
        if attrs["start"] > attrs["end"]:
            raise serializers.ValidationError({"end": "La fin doit suivre le début."})
        if attrs["end"] == date.max:
            raise serializers.ValidationError({"end": "Date de fin hors plage."})
        return attrs


class DetailQuerySerializer(PeriodQuerySerializer):
    provenance = serializers.CharField(required=False, max_length=120, allow_blank=False)


class IndicatorSerializer(serializers.Serializer):
    key = serializers.CharField()
    unit = serializers.UUIDField()
    start = serializers.DateField()
    end = serializers.DateField()
    label = serializers.CharField()
    definition = serializers.CharField()
    definition_version = serializers.CharField()
    value = serializers.IntegerField(allow_null=True)
    detail_url = serializers.CharField(allow_null=True)
    status = serializers.CharField()
    reason = serializers.CharField(required=False)
    provenance = serializers.CharField(required=False)


class FamilySerializer(serializers.Serializer):
    key = serializers.CharField()
    indicators = IndicatorSerializer(many=True)


class StatisticsSerializer(serializers.Serializer):
    unit = serializers.UUIDField()
    start = serializers.DateField()
    end = serializers.DateField()
    definition_version = serializers.CharField()
    prototype_only = serializers.BooleanField()
    families = FamilySerializer(many=True)


class DetailItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    url = serializers.CharField()


class DetailSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    definition = serializers.CharField()
    definition_version = serializers.CharField()
    unit = serializers.UUIDField()
    start = serializers.DateField()
    end = serializers.DateField()
    count = serializers.IntegerField()
    provenance = serializers.CharField(required=False)
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = DetailItemSerializer(many=True)
