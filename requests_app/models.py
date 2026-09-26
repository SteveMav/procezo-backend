import uuid

from django.conf import settings
from django.db import models


class CommunicationRequest(models.Model):
    class TargetType(models.TextChoices):
        BROKER = "broker", "Commissionnaire en douane"
        ORGANIZATION = "organization", "Entreprise ou ONG"

    class Mode(models.TextChoices):
        GENERATED = "generated", "Format Procezo"
        IMPORTED = "imported", "Document de l'agent"

    class State(models.TextChoices):
        DRAFT = "draft", "Brouillon"
        SUBMITTED = "submitted", "Soumis"
        VALIDATED = "validated", "Validé"
        SIGNED = "signed", "Signature constatée"
        ISSUED = "issued", "Émis"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey("cases.Case", on_delete=models.PROTECT, related_name="communication_requests")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="authored_requests")
    target_type = models.CharField(max_length=20, choices=TargetType.choices)
    target_name = models.CharField(max_length=240)
    represented_name = models.CharField(max_length=240, blank=True)
    subject = models.CharField(max_length=240)
    mode = models.CharField(max_length=20, choices=Mode.choices)
    due_on = models.DateField(null=True, blank=True)
    state = models.CharField(max_length=20, choices=State.choices, default=State.DRAFT)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["case", "state", "created_at"])]

    @property
    def unit(self):
        return self.case.unit

    @property
    def classification(self):
        return self.case.classification


class RequestedItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request = models.ForeignKey(CommunicationRequest, on_delete=models.PROTECT, related_name="items")
    number = models.PositiveSmallIntegerField()
    label = models.CharField(max_length=500)
    assessment_version = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["number"]
        constraints = [models.UniqueConstraint(fields=["request", "number"], name="unique_requested_item_number")]


class ActVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request = models.ForeignKey(CommunicationRequest, on_delete=models.PROTECT, related_name="acts")
    request_version = models.PositiveIntegerField()
    mode = models.CharField(max_length=20, choices=CommunicationRequest.Mode.choices)
    imported_document = models.ForeignKey("documents.Document", on_delete=models.PROTECT, null=True, blank=True)
    storage_name = models.UUIDField(null=True, blank=True, unique=True)
    sha256 = models.CharField(max_length=64)
    prepared_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    prepared_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["request", "request_version"], name="unique_request_act_version")]


class RequestEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request = models.ForeignKey(CommunicationRequest, on_delete=models.PROTECT, related_name="events")
    kind = models.CharField(max_length=24)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    act = models.ForeignKey(ActVersion, on_delete=models.PROTECT, null=True, blank=True)
    proof = models.ForeignKey("documents.Document", on_delete=models.PROTECT, null=True, blank=True)
    comment = models.CharField(max_length=500, blank=True)
    version = models.PositiveIntegerField()
    factual_at = models.DateTimeField(null=True, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["occurred_at", "id"]


class RequestIssuance(models.Model):
    request = models.OneToOneField(CommunicationRequest, on_delete=models.PROTECT, primary_key=True, related_name="issuance")
    act = models.ForeignKey(ActVersion, on_delete=models.PROTECT)
    signature_proof = models.ForeignKey("documents.Document", on_delete=models.PROTECT, related_name="signature_proofs")
    dispatch_proof = models.ForeignKey("documents.Document", on_delete=models.PROTECT, related_name="dispatch_proofs")
    idempotency_key = models.UUIDField()
    issued_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    issued_at = models.DateTimeField()
    recorded_at = models.DateTimeField(auto_now_add=True)
    prototype_only = models.BooleanField(default=True)


class RequestResponse(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request = models.ForeignKey(CommunicationRequest, on_delete=models.PROTECT, related_name="responses")
    letter = models.ForeignKey("documents.Document", on_delete=models.PROTECT, related_name="response_letters")
    annexes = models.ManyToManyField("documents.Document", related_name="response_annexes", blank=True)
    received_on = models.DateField()
    recorded_at = models.DateTimeField(auto_now_add=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    complement_of = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["received_on", "recorded_at", "id"]


class ResponseItemLink(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    response = models.ForeignKey(RequestResponse, on_delete=models.PROTECT, related_name="item_links")
    item = models.ForeignKey(RequestedItem, on_delete=models.PROTECT, related_name="response_links")
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="added_response_links")
    added_at = models.DateTimeField(auto_now_add=True)
    voided_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="voided_response_links", null=True, blank=True)
    voided_at = models.DateTimeField(null=True, blank=True)
    reason = models.CharField(max_length=500, blank=True)


class ItemAssessment(models.Model):
    class Receipt(models.TextChoices):
        NOT_RECEIVED = "not_received", "Non reçu"
        RECEIVED = "received", "Reçu"

    class Completeness(models.TextChoices):
        UNKNOWN = "unknown", "Non évalué"
        COMPLETE = "complete", "Complet"
        INSUFFICIENT = "insufficient", "Insuffisant"

    class Substance(models.TextChoices):
        PENDING = "pending", "Non apprécié"
        SATISFACTORY = "satisfactory", "Satisfaisant"
        UNSATISFACTORY = "unsatisfactory", "Non satisfaisant"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.ForeignKey(RequestedItem, on_delete=models.PROTECT, related_name="assessments")
    version = models.PositiveIntegerField()
    receipt = models.CharField(max_length=20, choices=Receipt.choices)
    completeness = models.CharField(max_length=20, choices=Completeness.choices)
    substance = models.CharField(max_length=20, choices=Substance.choices)
    reason = models.CharField(max_length=500)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["version"]
        constraints = [models.UniqueConstraint(fields=["item", "version"], name="unique_item_assessment_version")]
