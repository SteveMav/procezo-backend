import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class Decision(models.Model):
    class Kind(models.TextChoices):
        CLASSIFICATION = "classification", "Classement sans suite"
        MISSION = "mission", "Mission complémentaire"
        COMPLEMENT = "complement", "Demande de complément"
        GELEC = "gelec", "Relais GELEC"

    class State(models.TextChoices):
        PROPOSED = "proposed", "Proposée"
        RETURNED = "returned", "Retournée"
        VALIDATED = "validated", "Validée"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey("cases.Case", on_delete=models.PROTECT, related_name="decisions")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="authored_decisions")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    reason = models.CharField(max_length=1000)
    request_assessment = models.ForeignKey("requests_app.ItemAssessment", on_delete=models.PROTECT, null=True, blank=True)
    observation_assessment = models.ForeignKey("inspections.ObservationAssessment", on_delete=models.PROTECT, null=True, blank=True)
    replaces = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True, related_name="corrections")
    state = models.CharField(max_length=20, choices=State.choices, default=State.PROPOSED)
    version = models.PositiveIntegerField(default=1)
    validator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="validated_decisions")
    return_comment = models.CharField(max_length=500, blank=True)
    validated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    prototype_only = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(condition=(Q(request_assessment__isnull=False, observation_assessment__isnull=True) | Q(request_assessment__isnull=True, observation_assessment__isnull=False)), name="decision_one_assessment"),
            models.UniqueConstraint(fields=["case"], condition=Q(state="proposed"), name="one_proposed_decision_per_case"),
        ]

    @property
    def unit(self):
        return self.case.unit

    @property
    def classification(self):
        return self.case.classification


class DecisionEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    decision = models.ForeignKey(Decision, on_delete=models.PROTECT, related_name="events")
    kind = models.CharField(max_length=20)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    comment = models.CharField(max_length=500, blank=True)
    version = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        constraints = [models.UniqueConstraint(fields=["decision", "version"], name="unique_decision_event_version")]


class GelecTransfer(models.Model):
    class State(models.TextChoices):
        PREPARED = "prepared", "Préparé"
        TRANSMITTED = "transmitted", "Transmis"
        CONFIRMED = "confirmed", "Réception confirmée"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    decision = models.OneToOneField(Decision, on_delete=models.PROTECT, related_name="gelec_transfer")
    prepared_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="prepared_gelec_transfers")
    prepared_at = models.DateTimeField(auto_now_add=True)
    state = models.CharField(max_length=20, choices=State.choices, default=State.PREPARED)
    version = models.PositiveIntegerField(default=1)
    reference = models.CharField(max_length=120, blank=True)
    transmission_reference = models.CharField(max_length=120, blank=True)
    transmission_proof = models.ForeignKey("documents.Document", on_delete=models.PROTECT, null=True, blank=True, related_name="gelec_transmission_proofs")
    transmission_key = models.UUIDField(null=True, blank=True)
    transmitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="transmitted_gelec_transfers")
    transmitted_at = models.DateTimeField(null=True, blank=True)
    transmission_recorded_at = models.DateTimeField(null=True, blank=True)
    receipt_proof = models.ForeignKey("documents.Document", on_delete=models.PROTECT, null=True, blank=True, related_name="gelec_receipt_proofs")
    confirmation_key = models.UUIDField(null=True, blank=True)
    confirmed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="confirmed_gelec_transfers")
    received_at = models.DateTimeField(null=True, blank=True)
    confirmation_recorded_at = models.DateTimeField(null=True, blank=True)
    prototype_only = models.BooleanField(default=True)

    @property
    def case(self):
        return self.decision.case

    @property
    def unit(self):
        return self.decision.case.unit

    @property
    def classification(self):
        return self.decision.case.classification
