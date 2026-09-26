from rest_framework import serializers

from .models import Case, CaseAction, CaseAssignment


class CaseSerializer(serializers.ModelSerializer):
    unit_code = serializers.CharField(source="unit.code", read_only=True)
    assignee_username = serializers.CharField(source="assignee.username", read_only=True)

    class Meta:
        model = Case
        fields = ["id", "reference", "unit", "unit_code", "classification", "status", "assignee", "assignee_username", "next_action", "version", "created_at", "updated_at"]
        read_only_fields = fields


class CaseCreateSerializer(serializers.Serializer):
    unit = serializers.UUIDField()
    classification = serializers.ChoiceField(choices=[0, 1])
    assignee = serializers.IntegerField(min_value=1)
    next_action = serializers.CharField(max_length=240, allow_blank=False)
    assignment_reason = serializers.CharField(max_length=500, allow_blank=False)


class CaseUpdateSerializer(serializers.Serializer):
    version = serializers.IntegerField(min_value=1)
    next_action = serializers.CharField(max_length=240, allow_blank=False, required=False)
    status = serializers.ChoiceField(choices=Case.Status.choices, required=False)

    def validate(self, attrs):
        if not any(key in attrs for key in ("next_action", "status")):
            raise serializers.ValidationError({"non_field_errors": ["Une modification est requise."]})
        return attrs


class AssignmentSerializer(serializers.Serializer):
    version = serializers.IntegerField(min_value=1)
    assignee = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(max_length=500, allow_blank=False)


class CaseAssignmentReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaseAssignment
        fields = ["id", "previous_assignee", "new_assignee", "author", "reason", "created_at", "version"]


class CaseActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaseAction
        fields = ["id", "kind", "actor", "next_action", "status", "version", "created_at"]


class CaseTimelineSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    kind = serializers.CharField()
    actor = serializers.IntegerField()
    next_action = serializers.CharField(allow_null=True)
    status = serializers.CharField(allow_null=True)
    version = serializers.IntegerField(allow_null=True)
    created_at = serializers.DateTimeField()
    resource_id = serializers.UUIDField(allow_null=True, required=False)
