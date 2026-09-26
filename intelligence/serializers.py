from rest_framework import serializers

from .models import Dissemination, DisseminationReturn, Intelligence


class IntelligenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Intelligence
        fields = ["id", "unit", "classification", "subject", "summary", "provenance", "occurred_on", "assignee", "version", "created_at", "updated_at"]
        read_only_fields = fields


class IntelligenceCreateSerializer(serializers.Serializer):
    unit = serializers.UUIDField()
    classification = serializers.ChoiceField(choices=[0, 1])
    subject = serializers.CharField(max_length=240)
    summary = serializers.CharField(max_length=4000)
    provenance = serializers.CharField(max_length=120)
    occurred_on = serializers.DateField()
    assignee = serializers.IntegerField(min_value=1)
    source_identity = serializers.CharField(max_length=1000, required=False, write_only=True)


class IntelligenceUpdateSerializer(serializers.Serializer):
    version = serializers.IntegerField(min_value=1)
    subject = serializers.CharField(max_length=240, required=False)
    summary = serializers.CharField(max_length=4000, required=False)
    provenance = serializers.CharField(max_length=120, required=False)
    occurred_on = serializers.DateField(required=False)

    def validate(self, attrs):
        if len(attrs) == 1:
            raise serializers.ValidationError({"non_field_errors": ["Une modification est requise."]})
        return attrs


class CaseLinkSerializer(serializers.Serializer):
    version = serializers.IntegerField(min_value=1)
    case = serializers.UUIDField()


class DisseminationCreateSerializer(serializers.Serializer):
    recipient_unit = serializers.UUIDField()
    channel = serializers.CharField(max_length=80)
    reference = serializers.CharField(max_length=120, required=False, allow_blank=True)
    expected_action = serializers.CharField(max_length=500)
    sent_at = serializers.DateTimeField(required=False, allow_null=True)
    idempotency_key = serializers.UUIDField()


class DisseminationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dissemination
        fields = ["id", "intelligence", "recipient_unit", "channel", "reference", "expected_action", "sent_at", "created_at"]
        read_only_fields = fields


class ConfirmDisseminationSerializer(serializers.Serializer):
    sent_at = serializers.DateTimeField()


class ReturnCreateSerializer(serializers.Serializer):
    acknowledged = serializers.BooleanField(default=False)
    received_at = serializers.DateTimeField()
    note = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    idempotency_key = serializers.UUIDField()


class ReturnSerializer(serializers.ModelSerializer):
    class Meta:
        model = DisseminationReturn
        fields = ["id", "dissemination", "acknowledged", "received_at", "note", "recorded_at"]
        read_only_fields = fields
