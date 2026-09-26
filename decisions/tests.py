import hashlib
import tempfile
import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import OperationalError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from audit.models import AuditEvent
from cases.models import Case
from documents.models import Document
from documents.service import private_path
from identity.models import Delegation, Membership, Unit
from inspections.models import Defense, Observation, ObservationAssessment, ObservationSheet
from requests_app.models import CommunicationRequest, ItemAssessment, RequestedItem

from .models import Decision, DecisionEvent, GelecTransfer


class DecisionApiTests(TestCase):
    def setUp(self):
        private = tempfile.TemporaryDirectory()
        self.addCleanup(private.cleanup)
        override = override_settings(PROCEZO_PRIVATE_FILES_ROOT=private.name)
        override.enable()
        self.addCleanup(override.disable)
        users = get_user_model().objects
        self.agent = users.create_user("decision-agent", password="strong-demo-password")
        self.manager = users.create_user("decision-manager", password="strong-demo-password")
        self.undel = users.create_user("decision-undel", password="strong-demo-password")
        self.outsider = users.create_user("decision-out", password="strong-demo-password", is_staff=True, is_superuser=True)
        self.unit = Unit.objects.create(code="DEC", name="Décisions")
        self.other_unit = Unit.objects.create(code="EXT", name="Autre unité")
        now = timezone.now()
        for actor, role, unit in [
            (self.agent, Membership.Role.INVESTIGATOR, self.unit),
            (self.manager, Membership.Role.MANAGER, self.unit),
            (self.undel, Membership.Role.MANAGER, self.unit),
            (self.outsider, Membership.Role.MANAGER, self.other_unit),
        ]:
            Membership.objects.create(user=actor, unit=unit, role=role, clearance=1, valid_from=now)
        for action in [Delegation.Action.DECISION_VALIDATE, Delegation.Action.GELEC_TRANSFER, Delegation.Action.GELEC_CONFIRM]:
            Delegation.objects.create(user=self.manager, unit=self.unit, action=action, valid_from=now)
        self.case = Case.objects.create(unit=self.unit, classification=1, assignee=self.agent, created_by=self.manager, next_action="Apprécier")
        self.other_case = Case.objects.create(unit=self.other_unit, classification=1, assignee=self.outsider, created_by=self.outsider, next_action="Autre")
        req = CommunicationRequest.objects.create(case=self.case, author=self.agent, target_type="broker", target_name="Tiers fictif", subject="Pièces", mode="generated")
        item = RequestedItem.objects.create(request=req, number=1, label="Facture", assessment_version=1)
        self.assessment = ItemAssessment.objects.create(item=item, version=1, receipt="received", completeness="complete", substance="satisfactory", reason="Correspondance vérifiée", actor=self.agent)
        self.client = APIClient()
        self.client.force_login(self.agent)

    def document(self, *, case=None, content=b"%PDF-1.4\npreuve fictive\n"):
        case = case or self.case
        name = uuid.uuid4()
        path = private_path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return Document.objects.create(case=case, original_name="preuve.pdf", content_type="application/pdf", size=len(content), sha256=hashlib.sha256(content).hexdigest(), state=Document.State.ACCEPTED, storage_name=name, slot=Document.objects.filter(case=case).count() + 1, uploaded_by=self.agent)

    def propose(self, *, kind="classification", **overrides):
        self.case.refresh_from_db()
        payload = {"case": str(self.case.pk), "case_version": self.case.version, "kind": kind, "reason": "Motif fictif explicite", "request_assessment": str(self.assessment.pk)}
        payload.update(overrides)
        return self.client.post("/api/v1/decisions/", payload, format="json")

    def validate(self, decision):
        self.client.force_login(self.manager)
        return self.client.post(f"/api/v1/decisions/{decision['id']}/valider/", {"version": decision["version"]}, format="json")

    def test_proposal_return_correction_and_validation_history(self):
        self.assertEqual(Decision.objects.count(), 0)
        self.assertEqual(self.propose(reason="").status_code, 400)
        self.assertEqual(self.propose(request_assessment=str(uuid.uuid4())).status_code, 400)
        first = self.propose()
        self.assertEqual(first.status_code, 201, first.content)
        self.assertEqual(self.client.get("/api/v1/mon-travail/", {"kind": "decisions"}).data["count"], 1)
        self.assertEqual(self.propose().status_code, 409)
        self.assertEqual(self.client.post(f"/api/v1/decisions/{first.data['id']}/valider/", {"version": 1}, format="json").status_code, 403)
        self.client.force_login(self.undel)
        self.assertEqual(self.client.post(f"/api/v1/decisions/{first.data['id']}/valider/", {"version": 1}, format="json").status_code, 403)
        self.client.force_login(self.manager)
        self.assertEqual(self.client.get("/api/v1/a-valider/", {"kind": "decisions"}).data["count"], 1)
        url = f"/api/v1/decisions/{first.data['id']}/"
        self.assertEqual(self.client.post(url + "retourner/", {"version": 1, "comment": "Préciser les faits"}, format="json").status_code, 200)
        self.assertEqual(self.client.get("/api/v1/a-valider/", {"kind": "decisions"}).data["count"], 0)
        self.assertEqual(self.client.post(url + "valider/", {"version": 1}, format="json").status_code, 409)
        self.client.force_login(self.agent)
        self.assertTrue(self.client.get("/api/v1/mon-travail/", {"kind": "decisions"}).data["results"][0]["returned"])
        second = self.propose(replaces=first.data["id"], kind="gelec")
        self.assertEqual(second.status_code, 201, second.content)
        validated = self.validate(second.data)
        self.assertEqual(validated.status_code, 200, validated.content)
        self.assertEqual(validated.data["state"], "validated")
        self.assertEqual(self.client.post(f"/api/v1/decisions/{second.data['id']}/valider/", {"version": 1}, format="json").status_code, 409)
        self.assertEqual(self.client.get(url + "historique/").data["results"][1]["comment"], "Préciser les faits")
        self.assertEqual(self.client.get("/api/v1/decisions/", {"case": str(self.case.pk)}).data["count"], 2)
        self.client.force_login(self.agent)
        third = self.propose(replaces=second.data["id"], kind="classification")
        self.assertEqual(third.status_code, 201, third.content)
        self.assertEqual(Decision.objects.get(pk=second.data["id"]).state, Decision.State.VALIDATED)
        self.assertEqual(DecisionEvent.objects.filter(decision_id=second.data["id"]).count(), 2)
        self.assertTrue(AuditEvent.objects.filter(action="decision.validated").exists())

    def test_observation_source_visibility_revocation_and_audit_failure(self):
        letter = self.document()
        sheet = ObservationSheet.objects.create(case=self.case, author=self.agent, origin="field", recipient_address="Adresse", concerned_party="Tiers", facts="Faits")
        observation = Observation.objects.create(sheet=sheet, number=1, facts="Observation", assessment_version=1)
        defense = Defense.objects.create(sheet=sheet, letter=letter, received_on=timezone.localdate(), recorded_by=self.agent)
        defense.observations.add(observation)
        assessment = ObservationAssessment.objects.create(observation=observation, defense=defense, version=1, conclusion="unsatisfactory", reason="Non justifié", actor=self.agent)
        response = self.propose(request_assessment=None, observation_assessment=str(assessment.pk))
        self.assertEqual(response.status_code, 400)  # Two source fields are rejected.
        self.case.refresh_from_db()
        payload = {"case": str(self.case.pk), "case_version": self.case.version, "kind": "gelec", "reason": "Motif constaté", "observation_assessment": str(assessment.pk)}
        response = self.client.post("/api/v1/decisions/", payload, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(f"/api/v1/decisions/{response.data['id']}/").status_code, 404)
        self.assertEqual(self.client.get("/api/v1/decisions/", {"case": str(self.case.pk)}).status_code, 404)
        self.client.force_login(self.manager)
        with patch("decisions.service.record", side_effect=OperationalError("audit unavailable")):
            self.assertEqual(self.client.post(f"/api/v1/decisions/{response.data['id']}/valider/", {"version": 1}, format="json").status_code, 503)
        self.assertEqual(Decision.objects.get(pk=response.data["id"]).state, Decision.State.PROPOSED)
        Delegation.objects.filter(user=self.manager, action=Delegation.Action.DECISION_VALIDATE).update(revoked_at=timezone.now())
        self.assertEqual(self.client.post(f"/api/v1/decisions/{response.data['id']}/valider/", {"version": 1}, format="json").status_code, 403)

    def test_stale_assessment_blocks_proposal_and_validation(self):
        self.assessment.item.assessment_version = 2
        self.assessment.item.save(update_fields=["assessment_version"])
        self.assertEqual(self.propose().status_code, 409)
        self.case.refresh_from_db()
        self.assertEqual(self.case.version, 1)
        newer = ItemAssessment.objects.create(item=self.assessment.item, version=2, receipt="received", completeness="complete", substance="unsatisfactory", reason="Correction", actor=self.agent)
        proposal = self.propose(request_assessment=str(newer.pk))
        self.assertEqual(proposal.status_code, 201, proposal.content)
        self.assessment.item.assessment_version = 3
        self.assessment.item.save(update_fields=["assessment_version"])
        self.assertEqual(self.validate(proposal.data).status_code, 409)
        self.assertEqual(Decision.objects.get(pk=proposal.data["id"]).state, Decision.State.PROPOSED)

    def test_gelec_transmission_and_late_receipt_are_distinct_and_idempotent(self):
        proposed = self.propose(kind="gelec")
        self.assertEqual(proposed.status_code, 201, proposed.content)
        transfer_url = "/api/v1/transferts-gelec/"
        self.assertEqual(self.client.post(transfer_url, {"decision": proposed.data["id"]}, format="json").status_code, 403)
        self.client.force_login(self.manager)
        self.assertEqual(self.client.post(transfer_url, {"decision": proposed.data["id"]}, format="json").status_code, 409)
        self.assertEqual(self.validate(proposed.data).status_code, 200)
        prepared = self.client.post(transfer_url, {"decision": proposed.data["id"]}, format="json")
        self.assertEqual(prepared.status_code, 201, prepared.content)
        self.assertEqual(self.client.post(transfer_url, {"decision": proposed.data["id"]}, format="json").status_code, 200)
        url = f"{transfer_url}{prepared.data['id']}/"
        self.assertEqual(self.client.post(url + "confirmer-reception/", {"version": 1, "idempotency_key": str(uuid.uuid4()), "proof": str(uuid.uuid4()), "received_at": timezone.now().isoformat()}, format="json").status_code, 409)
        proof = self.document()
        sent_at = timezone.now()
        payload = {"version": 1, "idempotency_key": str(uuid.uuid4()), "proof": str(proof.pk), "transmitted_at": sent_at.isoformat()}
        with patch("decisions.service.record", side_effect=OperationalError("audit unavailable")):
            self.assertEqual(self.client.post(url + "transmettre/", payload, format="json").status_code, 503)
        self.assertEqual(GelecTransfer.objects.get(pk=prepared.data["id"]).state, GelecTransfer.State.PREPARED)
        transmitted = self.client.post(url + "transmettre/", payload, format="json")
        self.assertEqual(transmitted.status_code, 200, transmitted.content)
        self.assertEqual(transmitted.data["state"], "transmitted")
        self.assertEqual(transmitted.data["reference"], "")
        self.assertIsNone(transmitted.data["received_at"])
        self.assertNotIn("transmission_key", transmitted.data)
        self.assertEqual(self.client.get(transfer_url, {"case": str(self.case.pk)}).data["count"], 1)
        self.assertEqual(self.client.post(url + "transmettre/", payload, format="json").status_code, 200)
        self.assertEqual(self.client.post(url + "transmettre/", {**payload, "idempotency_key": str(uuid.uuid4())}, format="json").status_code, 409)
        self.assertEqual(GelecTransfer.objects.count(), 1)
        receipt = self.document()
        received_at = timezone.now()
        confirm = {"version": 2, "idempotency_key": str(uuid.uuid4()), "proof": str(receipt.pk), "received_at": received_at.isoformat(), "reference": "REF-FICTIVE-1"}
        confirmed = self.client.post(url + "confirmer-reception/", confirm, format="json")
        self.assertEqual(confirmed.status_code, 200, confirmed.content)
        self.assertEqual(confirmed.data["state"], "confirmed")
        self.assertEqual(confirmed.data["reference"], "REF-FICTIVE-1")
        self.assertEqual(self.client.post(url + "confirmer-reception/", confirm, format="json").status_code, 200)
        self.assertEqual(self.client.post(url + "transmettre/", payload, format="json").status_code, 200)
        self.assertEqual(self.client.post(url + "confirmer-reception/", {**confirm, "idempotency_key": str(uuid.uuid4())}, format="json").status_code, 409)
        self.assertEqual(AuditEvent.objects.filter(action="gelec.transmitted").count(), 1)
        self.assertEqual(AuditEvent.objects.filter(action="gelec.receipt.confirmed").count(), 1)
        Delegation.objects.filter(user=self.manager, action=Delegation.Action.GELEC_CONFIRM).update(revoked_at=timezone.now())
        self.assertEqual(self.client.post(url + "confirmer-reception/", confirm, format="json").status_code, 403)

    def test_classification_never_prepares_gelec_and_proofs_are_scoped(self):
        proposed = self.propose()
        self.assertEqual(proposed.status_code, 201, proposed.content)
        self.validate(proposed.data)
        self.assertEqual(self.client.post("/api/v1/transferts-gelec/", {"decision": proposed.data["id"]}, format="json").status_code, 409)
        self.client.force_login(self.agent)
        correction = self.propose(replaces=proposed.data["id"], kind="gelec")
        self.assertEqual(correction.status_code, 201, correction.content)
        self.validate(correction.data)
        prepared = self.client.post("/api/v1/transferts-gelec/", {"decision": correction.data["id"]}, format="json")
        wrong = self.document(case=self.other_case)
        payload = {"version": 1, "idempotency_key": str(uuid.uuid4()), "proof": str(wrong.pk), "transmitted_at": timezone.now().isoformat()}
        self.assertEqual(self.client.post(f"/api/v1/transferts-gelec/{prepared.data['id']}/transmettre/", payload, format="json").status_code, 400)
        self.assertEqual(GelecTransfer.objects.get(pk=prepared.data["id"]).state, GelecTransfer.State.PREPARED)
        valid = self.document()
        url = f"/api/v1/transferts-gelec/{prepared.data['id']}/"
        payload.update(proof=str(valid.pk), transmitted_at=timezone.now().isoformat(), reference="REF-A")
        self.assertEqual(self.client.post(url + "transmettre/", payload, format="json").status_code, 200)
        confirmation = {"version": 2, "idempotency_key": str(uuid.uuid4()), "proof": str(valid.pk), "received_at": timezone.now().isoformat(), "reference": "REF-B"}
        self.assertEqual(self.client.post(url + "confirmer-reception/", confirmation, format="json").status_code, 400)
        self.assertEqual(GelecTransfer.objects.get(pk=prepared.data["id"]).state, GelecTransfer.State.TRANSMITTED)
