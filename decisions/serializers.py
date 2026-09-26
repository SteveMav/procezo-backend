from django.utils import timezone
from rest_framework import serializers

from .models import Decision, DecisionEvent, GelecTransfer


class DecisionCreateSerializer(serializers.Serializer):
    case = serializers.UUIDField()
    case_version = serializers.IntegerField(min_value=1)
    kind = serializers.ChoiceField(choices=Decision.Kind.choices)
    reason = serializers.CharField(max_length=1000, allow_blank=False)
    request_assessment = serializers.UUIDField(required=False)
    observation_assessment = serializers.UUIDField(required=False)
    replaces = serializers.UUIDField(required=False)

    def validate(self, attrs):
        if ("request_assessment" in attrs) == ("observation_assessment" in attrs):
            raise serializers.ValidationError({"assessment": ["Une seule appréciation est requise."]})
        return attrs


class DecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Decision
        fields = ["id", "case", "author", "kind", "reason", "request_assessment", "observation_assessment", "replaces", "state", "version", "validator", "return_comment", "validated_at", "created_at", "updated_at", "prototype_only"]


class DecisionEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = DecisionEvent
        fields = ["id", "kind", "actor", "comment", "version", "created_at"]


class DecisionTransitionSerializer(serializers.Serializer):
    version = serializers.IntegerField(min_value=1)


class DecisionReturnSerializer(DecisionTransitionSerializer):
    comment = serializers.CharField(max_length=500, allow_blank=False)


class TransferCreateSerializer(serializers.Serializer):
    decision = serializers.UUIDField()


class GelecTransferSerializer(serializers.ModelSerializer):
    case = serializers.UUIDField(source="decision.case_id", read_only=True)

    class Meta:
        model = GelecTransfer
        fields = ["id", "decision", "case", "prepared_by", "prepared_at", "state", "version", "reference", "transmission_reference", "transmission_proof", "transmitted_by", "transmitted_at", "transmission_recorded_at", "receipt_proof", "confirmed_by", "received_at", "confirmation_recorded_at", "prototype_only"]


class TransmitSerializer(serializers.Serializer):
    version = serializers.IntegerField(min_value=1)
    idempotency_key = serializers.UUIDField()
    proof = serializers.UUIDField()
    transmitted_at = serializers.DateTimeField()
    reference = serializers.CharField(max_length=120, allow_blank=True, required=False, default="")

    def validate_transmitted_at(self, value):
        if value > timezone.now():
            raise serializers.ValidationError("Date de transmission future interdite.")
        return value


class ConfirmReceiptSerializer(serializers.Serializer):
    version = serializers.IntegerField(min_value=1)
    idempotency_key = serializers.UUIDField()
    proof = serializers.UUIDField()
    received_at = serializers.DateTimeField()
    reference = serializers.CharField(max_length=120, allow_blank=True, required=False, default="")

    def validate_received_at(self, value):
        if value > timezone.now():
            raise serializers.ValidationError("Date de réception future interdite.")
        return value
