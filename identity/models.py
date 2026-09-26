import uuid

from django.conf import settings
from django.db import models


class Unit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=160)

    def __str__(self):
        return self.code


class Membership(models.Model):
    class Role(models.TextChoices):
        MANAGER = "manager", "Responsable"
        INVESTIGATOR = "investigator", "Enquêteur"
        AUDITOR = "auditor", "Contrôleur d'audit"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT)
    role = models.CharField(max_length=20, choices=Role.choices)
    clearance = models.PositiveSmallIntegerField(default=0)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["user", "unit", "role"])]
        constraints = [models.CheckConstraint(condition=models.Q(clearance__lte=1), name="membership_clearance_max_1")]


class Delegation(models.Model):
    class Action(models.TextChoices):
        CASE_CREATE = "case.create", "Créer un dossier"
        CASE_ASSIGN = "case.assign", "Affecter un dossier"
        AUDIT_READ = "audit.read", "Lire l'audit"
        INTELLIGENCE_DISTRIBUTE = "intelligence.distribute", "Diffuser un renseignement"
        SOURCE_READ = "source.read", "Lire une source protégée"
        SOURCE_WRITE = "source.write", "Enregistrer une source protégée"
        REQUEST_VALIDATE = "request.validate", "Valider une demande"
        REQUEST_SIGN = "request.sign", "Constater la signature"
        REQUEST_ISSUE = "request.issue", "Constater l'émission"
        DECISION_VALIDATE = "decision.validate", "Valider une suite"
        GELEC_TRANSFER = "gelec.transfer", "Transmettre vers GELEC"
        GELEC_CONFIRM = "gelec.confirm", "Confirmer la réception GELEC"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT)
    action = models.CharField(max_length=32, choices=Action.choices)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    granted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="delegations_granted", null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["user", "unit", "action"])]
