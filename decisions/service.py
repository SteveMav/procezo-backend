import hashlib

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from audit.service import record
from cases.models import Case, CaseAction
from documents.models import Document
from documents.service import private_path
from identity.policy import can
from inspections.models import ObservationAssessment
from platform_api.errors import Conflict
from requests_app.models import ItemAssessment

from .models import Decision, DecisionEvent, GelecTransfer


def _source_assessment(case, data):
    if "request_assessment" in data:
        assessment = ItemAssessment.objects.select_related("item__request__case").filter(pk=data["request_assessment"], item__request__case=case).first()
        if assessment is None or assessment.substance == ItemAssessment.Substance.PENDING:
            raise ValidationError({"request_assessment": ["Appréciation de fond du dossier requise."]})
        if assessment.version != assessment.item.assessment_version:
            raise Conflict()
        return {"request_assessment": assessment}
    assessment = ObservationAssessment.objects.select_related("observation__sheet__case").filter(pk=data["observation_assessment"], observation__sheet__case=case).first()
    if assessment is None or assessment.conclusion == ObservationAssessment.Conclusion.PENDING:
        raise ValidationError({"observation_assessment": ["Appréciation de fond du dossier requise."]})
    if assessment.version != assessment.observation.assessment_version:
        raise Conflict()
    return {"observation_assessment": assessment}


def _check_source_current(decision):
    if decision.request_assessment_id:
        assessment = decision.request_assessment
        current = ItemAssessment.objects.filter(pk=assessment.pk, item__assessment_version=assessment.version).exists()
    else:
        assessment = decision.observation_assessment
        current = ObservationAssessment.objects.filter(pk=assessment.pk, observation__assessment_version=assessment.version).exists()
    if not current:
        raise Conflict()


def _proof(case, identifier):
    document = Document.objects.filter(pk=identifier, case=case, state=Document.State.ACCEPTED, content_type="application/pdf").first()
    if document is None:
        raise ValidationError({"proof": ["PDF accepté du dossier requis."]})
    try:
        digest = hashlib.sha256()
        with private_path(document.storage_name).open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        raise ValidationError({"proof": ["Fichier de preuve indisponible."]})
    if digest.hexdigest() != document.sha256:
        raise ValidationError({"proof": ["Empreinte de preuve invalide."]})
    return document


def create_decision(request, case, data):
    with transaction.atomic():
        if not can(request.user, "case.update", case):
            raise PermissionDenied()
        version = data["case_version"]
        if Case.objects.filter(pk=case.pk, version=version).update(version=version + 1, updated_at=timezone.now()) != 1:
            raise Conflict()
        previous = Decision.objects.filter(case=case).first()
        if previous is not None and (previous.state == Decision.State.PROPOSED or data.get("replaces") != previous.pk):
            raise Conflict()
        if previous is None and "replaces" in data:
            raise ValidationError({"replaces": ["Aucune décision à rectifier."]})
        source = _source_assessment(case, data)
        decision = Decision.objects.create(case=case, author=request.user, kind=data["kind"], reason=data["reason"], replaces=previous, **source)
        DecisionEvent.objects.create(decision=decision, kind="proposed", actor=request.user, version=1)
        case.refresh_from_db()
        CaseAction.objects.create(case=case, kind="decision.proposed", actor=request.user, next_action=case.next_action, status=case.status, version=case.version)
        record(request, action="decision.proposed", unit=case.unit, resource=case, details={"decision_id": str(decision.pk), "kind": decision.kind, "replaces": str(previous.pk) if previous else None})
        return decision


def transition_decision(request, decision, *, version, target, comment=""):
    with transaction.atomic():
        if not can(request.user, "decision.validate", decision) or request.user.pk == decision.author_id:
            raise PermissionDenied()
        if target == Decision.State.VALIDATED:
            _check_source_current(decision)
        changed = {"state": target, "version": version + 1, "updated_at": timezone.now()}
        if target == Decision.State.VALIDATED:
            changed.update(validator=request.user, validated_at=timezone.now())
        else:
            changed["return_comment"] = comment
        if Decision.objects.filter(pk=decision.pk, state=Decision.State.PROPOSED, version=version).update(**changed) != 1:
            raise Conflict()
        kind = "validated" if target == Decision.State.VALIDATED else "returned"
        DecisionEvent.objects.create(decision=decision, kind=kind, actor=request.user, comment=comment, version=version + 1)
        record(request, action=f"decision.{kind}", unit=decision.unit, resource=decision.case, details={"decision_id": str(decision.pk), "version": version + 1})
        decision.refresh_from_db()
        return decision


def _latest_validated(case):
    return Decision.objects.filter(case=case, state=Decision.State.VALIDATED).first()


def prepare_transfer(request, decision):
    with transaction.atomic():
        if not can(request.user, "gelec.transfer", decision):
            raise PermissionDenied()
        if decision.kind != Decision.Kind.GELEC or decision.state != Decision.State.VALIDATED or _latest_validated(decision.case) != decision:
            raise Conflict()
        transfer, created = GelecTransfer.objects.get_or_create(decision=decision, defaults={"prepared_by": request.user})
        if created:
            record(request, action="gelec.prepared", unit=decision.unit, resource=decision.case, details={"transfer_id": str(transfer.pk), "decision_id": str(decision.pk)})
        return transfer, created


def transmit(request, transfer, data):
    with transaction.atomic():
        if not can(request.user, "gelec.transfer", transfer):
            raise PermissionDenied()
        if transfer.state != GelecTransfer.State.PREPARED:
            if transfer.transmission_key == data["idempotency_key"] and transfer.transmitted_by_id == request.user.pk and transfer.transmission_proof_id == data["proof"] and transfer.transmitted_at == data["transmitted_at"] and transfer.transmission_reference == data["reference"]:
                return transfer
            raise Conflict()
        if _latest_validated(transfer.case) != transfer.decision:
            raise Conflict()
        if data["transmitted_at"] < transfer.decision.validated_at:
            raise ValidationError({"transmitted_at": ["La transmission précède la validation."]})
        proof = _proof(transfer.case, data["proof"])
        version = data["version"]
        if GelecTransfer.objects.filter(pk=transfer.pk, state=GelecTransfer.State.PREPARED, version=version).update(state=GelecTransfer.State.TRANSMITTED, version=version + 1, reference=data["reference"], transmission_reference=data["reference"], transmission_proof=proof, transmission_key=data["idempotency_key"], transmitted_by=request.user, transmitted_at=data["transmitted_at"], transmission_recorded_at=timezone.now()) != 1:
            raise Conflict()
        record(request, action="gelec.transmitted", unit=transfer.unit, resource=transfer.case, details={"transfer_id": str(transfer.pk), "proof_id": str(proof.pk)})
        transfer.refresh_from_db()
        return transfer


def confirm_receipt(request, transfer, data):
    with transaction.atomic():
        if not can(request.user, "gelec.confirm", transfer):
            raise PermissionDenied()
        if transfer.state == GelecTransfer.State.CONFIRMED:
            if transfer.confirmation_key == data["idempotency_key"] and transfer.confirmed_by_id == request.user.pk and transfer.receipt_proof_id == data["proof"] and transfer.received_at == data["received_at"] and (not data["reference"] or transfer.reference == data["reference"]):
                return transfer
            raise Conflict()
        if transfer.state != GelecTransfer.State.TRANSMITTED:
            raise Conflict()
        if data["received_at"] < transfer.transmitted_at:
            raise ValidationError({"received_at": ["La réception précède la transmission."]})
        if data["reference"] and transfer.reference and data["reference"] != transfer.reference:
            raise ValidationError({"reference": ["Référence GELEC contradictoire."]})
        proof = _proof(transfer.case, data["proof"])
        version = data["version"]
        reference = data["reference"] or transfer.reference
        if GelecTransfer.objects.filter(pk=transfer.pk, state=GelecTransfer.State.TRANSMITTED, version=version).update(state=GelecTransfer.State.CONFIRMED, version=version + 1, reference=reference, receipt_proof=proof, confirmation_key=data["idempotency_key"], confirmed_by=request.user, received_at=data["received_at"], confirmation_recorded_at=timezone.now()) != 1:
            raise Conflict()
        record(request, action="gelec.receipt.confirmed", unit=transfer.unit, resource=transfer.case, details={"transfer_id": str(transfer.pk), "proof_id": str(proof.pk)})
        transfer.refresh_from_db()
        return transfer
