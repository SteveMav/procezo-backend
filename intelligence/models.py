import uuid

from django.conf import settings
from django.db import models


class Intelligence(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit = models.ForeignKey("identity.Unit", on_delete=models.PROTECT)
    classification = models.PositiveSmallIntegerField(default=0)
    subject = models.CharField(max_length=240)
    summary = models.TextField(max_length=4000)
    provenance = models.CharField(max_length=120)
    occurred_on = models.DateField()
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="assigned_intelligence")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_intelligence")
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cases = models.ManyToManyField("cases.Case", through="CaseIntelligence", related_name="intelligence")

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["unit", "created_at"])]
        constraints = [models.CheckConstraint(condition=models.Q(classification__in=[0, 1]), name="intelligence_classification_allowed")]


class ProtectedSource(models.Model):
    intelligence = models.OneToOneField(Intelligence, on_delete=models.PROTECT, related_name="protected_source")
    identity = models.TextField(max_length=1000)
    recorded_at = models.DateTimeField(auto_now_add=True)


class CaseIntelligence(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    intelligence = models.ForeignKey(Intelligence, on_delete=models.PROTECT)
    case = models.ForeignKey("cases.Case", on_delete=models.PROTECT)
    linked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    linked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["intelligence", "case"], name="unique_case_intelligence")]


class Dissemination(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    intelligence = models.ForeignKey(Intelligence, on_delete=models.PROTECT, related_name="disseminations")
    recipient_unit = models.ForeignKey("identity.Unit", on_delete=models.PROTECT)
    channel = models.CharField(max_length=80)
    reference = models.CharField(max_length=120, blank=True)
    expected_action = models.CharField(max_length=500)
    sent_at = models.DateTimeField(null=True, blank=True)
    idempotency_key = models.UUIDField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        constraints = [models.UniqueConstraint(fields=["intelligence", "idempotency_key"], name="unique_dissemination_retry")]


class DisseminationReturn(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dissemination = models.ForeignKey(Dissemination, on_delete=models.PROTECT, related_name="returns")
    acknowledged = models.BooleanField(default=False)
    received_at = models.DateTimeField()
    note = models.CharField(max_length=1000, blank=True)
    idempotency_key = models.UUIDField()
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["received_at", "id"]
        constraints = [models.UniqueConstraint(fields=["dissemination", "idempotency_key"], name="unique_return_retry")]
