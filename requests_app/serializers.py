from rest_framework import serializers

from .models import ActVersion, CommunicationRequest, ItemAssessment, RequestEvent, RequestIssuance, RequestedItem, RequestResponse, ResponseItemLink


class ItemInputSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=500, allow_blank=False)


class RequestCreateSerializer(serializers.Serializer):
    case = serializers.UUIDField()
    target_type = serializers.ChoiceField(choices=CommunicationRequest.TargetType.choices)
    target_name = serializers.CharField(max_length=240, allow_blank=False)
    represented_name = serializers.CharField(max_length=240, allow_blank=True, required=False, default="")
    subject = serializers.CharField(max_length=240, allow_blank=False)
    mode = serializers.ChoiceField(choices=CommunicationRequest.Mode.choices)
    due_on = serializers.DateField(required=False, allow_null=True)
    items = ItemInputSerializer(many=True, allow_empty=False)

    def validate_items(self, value):
        if len(value) > 20:
            raise serializers.ValidationError("Vingt éléments au maximum.")
        return value


class RequestUpdateSerializer(serializers.Serializer):
    version = serializers.IntegerField(min_value=1)
    target_type = serializers.ChoiceField(choices=CommunicationRequest.TargetType.choices, required=False)
    target_name = serializers.CharField(max_length=240, allow_blank=False, required=False)
    represented_name = serializers.CharField(max_length=240, allow_blank=True, required=False)
    subject = serializers.CharField(max_length=240, allow_blank=False, required=False)
    mode = serializers.ChoiceField(choices=CommunicationRequest.Mode.choices, required=False)
    due_on = serializers.DateField(required=False, allow_null=True)
    items = ItemInputSerializer(many=True, allow_empty=False, required=False)

    def validate(self, attrs):
        if len(attrs) == 1:
            raise serializers.ValidationError({"non_field_errors": ["Une modification est requise."]})
        return attrs


class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestedItem
        fields = ["id", "number", "label", "assessment_version"]


class ActSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActVersion
        fields = ["id", "request_version", "mode", "imported_document", "sha256", "prepared_by", "prepared_at"]


class IssuanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestIssuance
        fields = ["act", "signature_proof", "dispatch_proof", "issued_at", "recorded_at", "prototype_only"]


class RequestSerializer(serializers.ModelSerializer):
    items = ItemSerializer(many=True, read_only=True)
    acts = ActSerializer(many=True, read_only=True)
    issuance = IssuanceSerializer(read_only=True)

    class Meta:
        model = CommunicationRequest
        fields = ["id", "case", "author", "target_type", "target_name", "represented_name", "subject", "mode", "due_on", "state", "version", "created_at", "updated_at", "items", "acts", "issuance"]


class PrepareSerializer(serializers.Serializer):
    version = serializers.IntegerField(min_value=1)
    document = serializers.UUIDField(required=False)


class TransitionSerializer(serializers.Serializer):
    version = serializers.IntegerField(min_value=1)


class RequestReturnSerializer(TransitionSerializer):
    comment = serializers.CharField(max_length=500, allow_blank=False)


class SignSerializer(TransitionSerializer):
    proof = serializers.UUIDField()
    signed_at = serializers.DateTimeField()

    def validate_signed_at(self, value):
        from django.utils import timezone
        if value > timezone.now():
            raise serializers.ValidationError("Date de signature future interdite.")
        return value


class IssueSerializer(TransitionSerializer):
    idempotency_key = serializers.UUIDField()
    dispatch_proof = serializers.UUIDField()
    sent_at = serializers.DateTimeField()

    def validate_sent_at(self, value):
        from django.utils import timezone
        if value > timezone.now():
            raise serializers.ValidationError("Date d'envoi future interdite.")
        return value


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestEvent
        fields = ["id", "kind", "actor", "act", "proof", "comment", "version", "factual_at", "occurred_at"]


class ResponseCreateSerializer(serializers.Serializer):
    letter = serializers.UUIDField()
    annexes = serializers.ListField(child=serializers.UUIDField(), required=False, default=list, max_length=20)
    received_on = serializers.DateField()
    complement_of = serializers.UUIDField(required=False)
    item_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False, max_length=20)


class LinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResponseItemLink
        fields = ["id", "item", "added_by", "added_at", "voided_by", "voided_at", "reason"]


class ResponseSerializer(serializers.ModelSerializer):
    item_links = LinkSerializer(many=True, read_only=True)

    class Meta:
        model = RequestResponse
        fields = ["id", "request", "letter", "annexes", "received_on", "recorded_at", "recorded_by", "complement_of", "version", "item_links"]


class RectifySerializer(serializers.Serializer):
    version = serializers.IntegerField(min_value=1)
    add_item_ids = serializers.ListField(child=serializers.UUIDField(), required=False, default=list, max_length=20)
    remove_link_ids = serializers.ListField(child=serializers.UUIDField(), required=False, default=list, max_length=20)
    reason = serializers.CharField(max_length=500, allow_blank=False)

    def validate(self, attrs):
        if not attrs["add_item_ids"] and not attrs["remove_link_ids"]:
            raise serializers.ValidationError({"non_field_errors": ["Une rectification est requise."]})
        return attrs


class AssessmentInputSerializer(serializers.Serializer):
    version = serializers.IntegerField(min_value=0)
    receipt = serializers.ChoiceField(choices=ItemAssessment.Receipt.choices)
    completeness = serializers.ChoiceField(choices=ItemAssessment.Completeness.choices)
    substance = serializers.ChoiceField(choices=ItemAssessment.Substance.choices)
    reason = serializers.CharField(max_length=500, allow_blank=False)

    def validate(self, attrs):
        if attrs["receipt"] == ItemAssessment.Receipt.NOT_RECEIVED and (attrs["completeness"] != ItemAssessment.Completeness.UNKNOWN or attrs["substance"] != ItemAssessment.Substance.PENDING):
            raise serializers.ValidationError({"receipt": ["Un élément non reçu ne peut pas être apprécié."]})
        return attrs


class AssessmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemAssessment
        fields = ["id", "version", "receipt", "completeness", "substance", "reason", "actor", "recorded_at"]
