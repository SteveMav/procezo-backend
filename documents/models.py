import uuid

from django.conf import settings
from django.db import models


class Document(models.Model):
    class State(models.TextChoices):
        QUARANTINE = "quarantine", "En quarantaine"
        ACCEPTED = "accepted", "Accepté"
        REJECTED = "rejected", "Rejeté"
        MISSING = "missing", "Fichier manquant"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey("cases.Case", null=True, blank=True, on_delete=models.PROTECT, related_name="documents")
    intelligence = models.ForeignKey("intelligence.Intelligence", null=True, blank=True, on_delete=models.PROTECT, related_name="documents")
    original_name = models.CharField(max_length=240)
    content_type = models.CharField(max_length=40)
    size = models.PositiveIntegerField()
    sha256 = models.CharField(max_length=64)
    state = models.CharField(max_length=20, choices=State.choices, default=State.QUARANTINE)
    storage_name = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    slot = models.PositiveSmallIntegerField()
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    scanned_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-uploaded_at", "-id"]
        constraints = [
            models.CheckConstraint(condition=(models.Q(case__isnull=False, intelligence__isnull=True) | models.Q(case__isnull=True, intelligence__isnull=False)), name="document_one_parent"),
            models.CheckConstraint(condition=models.Q(slot__gte=1, slot__lte=20), name="document_slot_range"),
            models.UniqueConstraint(fields=["case", "slot"], condition=models.Q(case__isnull=False), name="unique_case_document_slot"),
            models.UniqueConstraint(fields=["intelligence", "slot"], condition=models.Q(intelligence__isnull=False), name="unique_intelligence_document_slot"),
        ]

    @property
    def parent(self):
        return self.case or self.intelligence


class FileOperation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.PROTECT, related_name="operations")
    kind = models.CharField(max_length=24)
    result = models.CharField(max_length=24)
    occurred_at = models.DateTimeField(auto_now_add=True)
