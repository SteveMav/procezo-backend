from rest_framework import serializers

from .models import Defense, InspectionMission, Observation, ObservationAssessment, ObservationSheet, SheetProject


class MissionInputSerializer(serializers.Serializer):
    case = serializers.UUIDField()
    context = serializers.CharField(max_length=500)
    findings = serializers.CharField(max_length=4000)
    occurred_on = serializers.DateField()
    participants = serializers.ListField(child=serializers.IntegerField(min_value=1), allow_empty=False, max_length=20)
    documents = serializers.ListField(child=serializers.UUIDField(), required=False, default=list, max_length=20)


class MissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = InspectionMission
        fields = ["id", "case", "author", "context", "findings", "occurred_on", "participants", "documents", "created_at"]


class ObservationInputSerializer(serializers.Serializer):
    facts = serializers.CharField(max_length=2000)
    documents = serializers.ListField(child=serializers.UUIDField(), required=False, default=list, max_length=20)


class SheetInputSerializer(serializers.Serializer):
    case = serializers.UUIDField()
    mission = serializers.UUIDField(required=False, allow_null=True)
    origin = serializers.ChoiceField(choices=ObservationSheet.Origin.choices)
    recipient_address = serializers.CharField(max_length=500)
    concerned_party = serializers.CharField(max_length=240)
    facts = serializers.CharField(max_length=4000)
    observations = ObservationInputSerializer(many=True, allow_empty=False)

    def validate_observations(self, value):
        if len(value) > 20:
            raise serializers.ValidationError("Vingt observations au maximum.")
        return value


class SheetUpdateSerializer(serializers.Serializer):
    version = serializers.IntegerField(min_value=1)
    recipient_address = serializers.CharField(max_length=500, required=False)
    concerned_party = serializers.CharField(max_length=240, required=False)
    facts = serializers.CharField(max_length=4000, required=False)
    observations = ObservationInputSerializer(many=True, allow_empty=False, required=False)

    def validate(self, attrs):
        if len(attrs) == 1:
            raise serializers.ValidationError({"non_field_errors": ["Une modification est requise."]})
        if len(attrs.get("observations", [])) > 20:
            raise serializers.ValidationError({"observations": ["Vingt observations au maximum."]})
        return attrs


class ObservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Observation
        fields = ["id", "number", "facts", "documents", "assessment_version"]


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = SheetProject
        fields = ["id", "sheet", "sheet_version", "sha256", "prepared_by", "prepared_at"]


class SheetSerializer(serializers.ModelSerializer):
    observations = ObservationSerializer(many=True, read_only=True)
    projects = ProjectSerializer(many=True, read_only=True)

    class Meta:
        model = ObservationSheet
        fields = ["id", "case", "author", "mission", "origin", "recipient_address", "concerned_party", "facts", "version", "prototype_only", "created_at", "updated_at", "observations", "projects"]


class VersionSerializer(serializers.Serializer):
    version = serializers.IntegerField(min_value=1)


class DefenseInputSerializer(serializers.Serializer):
    letter = serializers.UUIDField()
    annexes = serializers.ListField(child=serializers.UUIDField(), required=False, default=list, max_length=20)
    received_on = serializers.DateField()
    complement_of = serializers.UUIDField(required=False)
    observation_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False, max_length=20)


class DefenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Defense
        fields = ["id", "sheet", "letter", "annexes", "observations", "received_on", "recorded_at", "recorded_by", "complement_of"]


class ObservationAssessmentInputSerializer(serializers.Serializer):
    version = serializers.IntegerField(min_value=0)
    defense = serializers.UUIDField()
    conclusion = serializers.ChoiceField(choices=ObservationAssessment.Conclusion.choices)
    reason = serializers.CharField(max_length=500)


class ObservationAssessmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ObservationAssessment
        fields = ["id", "observation", "defense", "version", "conclusion", "reason", "actor", "recorded_at"]
