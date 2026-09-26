from rest_framework import serializers

from .models import Document


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ["id", "case", "intelligence", "original_name", "content_type", "size", "sha256", "state", "uploaded_at", "scanned_at"]
        read_only_fields = fields


class UploadSerializer(serializers.Serializer):
    case = serializers.UUIDField(required=False)
    intelligence = serializers.UUIDField(required=False)
    file = serializers.FileField()

    def validate(self, attrs):
        if ("case" in attrs) == ("intelligence" in attrs):
            raise serializers.ValidationError({"parent": ["Un seul parent est requis."]})
        return attrs
