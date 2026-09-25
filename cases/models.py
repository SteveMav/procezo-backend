import uuid

from django.conf import settings
from django.db import models


class Case(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Ouvert"
        IN_PROGRESS = "in_progress", "En cours"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(max_length=24, unique=True, editable=False)
    unit = models.ForeignKey("identity.Unit", on_delete=models.PROTECT)
    classification = models.PositiveSmallIntegerField(default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="assigned_cases")
    next_action = models.CharField(max_length=240)
    version = models.PositiveIntegerField(default=1)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_cases")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["unit", "status", "created_at"])]
        constraints = [models.CheckConstraint(condition=models.Q(classification__in=[0, 1]), name="case_classification_allowed")]

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = f"DOS-{self.id.hex[:12].upper()}"
        super().save(*args, **kwargs)


class CaseAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(Case, on_delete=models.PROTECT, related_name="assignments")
    previous_assignee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="previous_case_assignments", null=True, blank=True)
    new_assignee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="new_case_assignments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="authored_case_assignments")
    reason = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    version = models.PositiveIntegerField()

    class Meta:
        ordering = ["created_at", "id"]
        constraints = [models.UniqueConstraint(fields=["case", "version"], name="unique_case_assignment_version")]


class CaseAction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(Case, on_delete=models.PROTECT, related_name="actions")
    kind = models.CharField(max_length=24)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    next_action = models.CharField(max_length=240)
    status = models.CharField(max_length=20)
    version = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        constraints = [models.UniqueConstraint(fields=["case", "version"], name="unique_case_action_version")]
