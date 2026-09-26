import uuid

from django.conf import settings
from django.db import models


class InspectionMission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey("cases.Case", on_delete=models.PROTECT, related_name="missions")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    context = models.CharField(max_length=500)
    findings = models.TextField(max_length=4000)
    occurred_on = models.DateField()
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="inspection_missions")
    documents = models.ManyToManyField("documents.Document", related_name="inspection_missions", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]


class ObservationSheet(models.Model):
    class Origin(models.TextChoices):
        MISSION = "mission", "Mission"
        INTELLIGENCE = "intelligence", "Renseignement"
        SYSTEM = "system", "Système"
        FIELD = "field", "Constat terrain"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey("cases.Case", on_delete=models.PROTECT, related_name="observation_sheets")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    mission = models.ForeignKey(InspectionMission, on_delete=models.PROTECT, null=True, blank=True, related_name="sheets")
    origin = models.CharField(max_length=20, choices=Origin.choices)
    recipient_address = models.CharField(max_length=500)
    concerned_party = models.CharField(max_length=240)
    facts = models.TextField(max_length=4000)
    version = models.PositiveIntegerField(default=1)
    prototype_only = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]


class Observation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sheet = models.ForeignKey(ObservationSheet, on_delete=models.PROTECT, related_name="observations")
    number = models.PositiveSmallIntegerField()
    facts = models.TextField(max_length=2000)
    documents = models.ManyToManyField("documents.Document", related_name="observations", blank=True)
    assessment_version = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["number"]
        constraints = [models.UniqueConstraint(fields=["sheet", "number"], name="unique_observation_number")]


class SheetProject(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sheet = models.ForeignKey(ObservationSheet, on_delete=models.PROTECT, related_name="projects")
    sheet_version = models.PositiveIntegerField()
    storage_name = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    sha256 = models.CharField(max_length=64)
    prepared_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    prepared_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["sheet", "sheet_version"], name="unique_sheet_project_version")]


class Defense(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sheet = models.ForeignKey(ObservationSheet, on_delete=models.PROTECT, related_name="defenses")
    letter = models.ForeignKey("documents.Document", on_delete=models.PROTECT, related_name="defense_letters")
    annexes = models.ManyToManyField("documents.Document", related_name="defense_annexes", blank=True)
    observations = models.ManyToManyField(Observation, related_name="defenses")
    received_on = models.DateField()
    recorded_at = models.DateTimeField(auto_now_add=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    complement_of = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True)

    class Meta:
        ordering = ["received_on", "recorded_at", "id"]


class ObservationAssessment(models.Model):
    class Conclusion(models.TextChoices):
        PENDING = "pending", "À apprécier"
        SATISFACTORY = "satisfactory", "Satisfaisante"
        UNSATISFACTORY = "unsatisfactory", "Insuffisante"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    observation = models.ForeignKey(Observation, on_delete=models.PROTECT, related_name="assessments")
    defense = models.ForeignKey(Defense, on_delete=models.PROTECT)
    version = models.PositiveIntegerField()
    conclusion = models.CharField(max_length=20, choices=Conclusion.choices)
    reason = models.CharField(max_length=500)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["version"]
        constraints = [models.UniqueConstraint(fields=["observation", "version"], name="unique_observation_assessment_version")]


class InspectionEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey("cases.Case", on_delete=models.PROTECT, related_name="inspection_events")
    kind = models.CharField(max_length=32)
    resource_id = models.UUIDField()
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
