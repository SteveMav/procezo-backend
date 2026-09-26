import hashlib
import tempfile
import uuid
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import OperationalError
from django.test import TestCase, override_settings
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from rest_framework.test import APIClient

from audit.models import AuditEvent
from cases.models import Case
from documents.models import Document
from documents.service import private_path
from identity.models import Delegation, Membership, Unit

from .models import ActVersion, CommunicationRequest, ItemAssessment, RequestIssuance, RequestResponse, ResponseItemLink


class RequestApiTests(TestCase):
    def setUp(self):
        self.private = tempfile.TemporaryDirectory()
        self.addCleanup(self.private.cleanup)
        self.override = override_settings(PROCEZO_PRIVATE_FILES_ROOT=self.private.name)
        self.override.enable()
        self.addCleanup(self.override.disable)
        users = get_user_model().objects
        self.agent = users.create_user("request-agent", password="strong-demo-password")
        self.manager = users.create_user("request-manager", password="strong-demo-password")
        self.other = users.create_user("request-other", password="strong-demo-password", is_staff=True, is_superuser=True)
        self.unit = Unit.objects.create(code="REQ", name="Demandes")
        self.other_unit = Unit.objects.create(code="OTHER", name="Autre")
        now = timezone.now()
        Membership.objects.create(user=self.agent, unit=self.unit, role=Membership.Role.INVESTIGATOR, clearance=1, valid_from=now)
        Membership.objects.create(user=self.manager, unit=self.unit, role=Membership.Role.MANAGER, clearance=1, valid_from=now)
        Membership.objects.create(user=self.other, unit=self.other_unit, role=Membership.Role.MANAGER, clearance=1, valid_from=now)
        for action in [Delegation.Action.REQUEST_VALIDATE, Delegation.Action.REQUEST_SIGN, Delegation.Action.REQUEST_ISSUE]:
            Delegation.objects.create(user=self.manager, unit=self.unit, action=action, valid_from=now)
        self.case = Case.objects.create(unit=self.unit, classification=1, assignee=self.agent, created_by=self.manager, next_action="Préparer une demande")
        self.client = APIClient()
        self.client.force_login(self.agent)

    def make_document(self, data=b"%PDF-1.4\nfiche fictive\n", *, case=None):
        storage_name = uuid.uuid4()
        path = private_path(storage_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return Document.objects.create(case=case or self.case, original_name="lettre.pdf", content_type="application/pdf", size=len(data), sha256=hashlib.sha256(data).hexdigest(), state=Document.State.ACCEPTED, storage_name=storage_name, slot=Document.objects.filter(case=case or self.case).count() + 1, uploaded_by=self.agent)

    def create_request(self, *, mode="generated", due_on=None):
        payload = {"case": str(self.case.pk), "target_type": "broker", "target_name": "Commissionnaire fictif", "represented_name": "Entreprise fictive", "subject": "Documents commerciaux", "mode": mode, "items": [{"label": "Déclaration"}, {"label": "Facture"}, {"label": "Preuve de transport"}]}
        if due_on:
            payload["due_on"] = due_on
        response = self.client.post("/api/v1/demandes/", payload, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        return response.data

    def test_generated_act_workflow_permissions_retry_and_audit(self):
        obj = self.create_request(due_on=timezone.localdate() - timedelta(days=1))
        url = f"/api/v1/demandes/{obj['id']}/"
        preview = self.client.get(url + "apercu/")
        self.assertEqual(preview.status_code, 200)
        self.assertTrue(preview.data["project_only"])
        self.assertEqual(preview.data["represented_name"], "Entreprise fictive")
        self.assertEqual(self.client.post(url + "soumettre/", {"version": 1}, format="json").status_code, 400)
        with patch("requests_app.service._render_project", side_effect=OSError("interrupted")):
            with self.assertRaises(OSError):
                self.client.post(url + "preparer/", {"version": 1}, format="json")
        self.assertEqual(CommunicationRequest.objects.get(pk=obj["id"]).state, "draft")
        prepared = self.client.post(url + "preparer/", {"version": 1}, format="json")
        self.assertEqual(prepared.status_code, 200, prepared.content)
        act_id = prepared.data["id"]
        self.assertEqual(self.client.post(url + "preparer/", {"version": 1}, format="json").data["id"], act_id)
        download = self.client.get(f"/api/v1/actes/{act_id}/telecharger/")
        self.assertEqual(download.status_code, 200)
        self.assertTrue(b"%PDF-" in b"".join(download.streaming_content)[:8])
        submitted = self.client.post(url + "soumettre/", {"version": 1}, format="json")
        self.assertEqual(submitted.status_code, 200, submitted.content)
        self.assertEqual(self.client.post(url + "valider/", {"version": 2}, format="json").status_code, 403)
        self.assertEqual(self.client.get("/api/v1/mon-travail/", {"kind": "requests"}).data["results"][0]["overdue"], True)
        self.client.force_login(self.manager)
        self.assertEqual(self.client.get("/api/v1/a-valider/").data["count"], 1)
        validated = self.client.post(url + "valider/", {"version": 2}, format="json")
        self.assertEqual(validated.status_code, 200, validated.content)
        self.assertEqual(self.client.get("/api/v1/a-valider/").data["count"], 0)
        proof = self.make_document()
        signed_at = timezone.now() - timedelta(hours=2)
        signed = self.client.post(url + "constater-signature/", {"version": 3, "proof": str(proof.pk), "signed_at": signed_at.isoformat()}, format="json")
        self.assertEqual(signed.status_code, 200, signed.content)
        dispatch = self.make_document()
        key = uuid.uuid4()
        sent_at = timezone.now() - timedelta(hours=1)
        payload = {"version": 4, "idempotency_key": str(key), "dispatch_proof": str(dispatch.pk), "sent_at": sent_at.isoformat()}
        issued = self.client.post(url + "constater-emission/", payload, format="json")
        self.assertEqual(issued.status_code, 200, issued.content)
        self.assertEqual(issued.data["state"], "issued")
        self.assertTrue(issued.data["issuance"]["prototype_only"])
        self.assertEqual(parse_datetime(issued.data["issuance"]["issued_at"]), sent_at)
        self.assertGreater(parse_datetime(issued.data["issuance"]["recorded_at"]), sent_at)
        self.assertEqual(self.client.post(url + "constater-emission/", payload, format="json").status_code, 200)
        self.assertEqual(RequestIssuance.objects.count(), 1)
        self.assertEqual(self.client.post(url + "constater-emission/", {**payload, "idempotency_key": str(uuid.uuid4())}, format="json").status_code, 409)
        self.assertTrue(AuditEvent.objects.filter(action="request.issued").exists())
        self.assertEqual(ActVersion.objects.count(), 1)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.get(f"/api/v1/actes/{act_id}/telecharger/").status_code, 404)
        self.assertEqual(self.client.get("/api/v1/a-valider/").data["count"], 0)

    def test_imported_act_return_and_version_conflict(self):
        obj = self.create_request(mode="imported")
        url = f"/api/v1/demandes/{obj['id']}/"
        letter = self.make_document()
        prepared = self.client.post(url + "preparer/", {"version": 1, "document": str(letter.pk)}, format="json")
        self.assertEqual(prepared.status_code, 200, prepared.content)
        self.assertEqual(prepared.data["imported_document"], letter.pk)
        self.assertEqual(self.client.post(url + "soumettre/", {"version": 1}, format="json").status_code, 200)
        self.client.force_login(self.manager)
        returned = self.client.post(url + "retourner/", {"version": 2, "comment": "Corriger l'objet"}, format="json")
        self.assertEqual(returned.status_code, 200, returned.content)
        self.client.force_login(self.agent)
        self.assertEqual(self.client.patch(url, {"version": 1, "subject": "Corrigé"}, format="json").status_code, 409)
        updated = self.client.patch(url, {"version": 3, "subject": "Corrigé"}, format="json")
        self.assertEqual(updated.status_code, 200, updated.content)
        self.assertEqual(self.client.post(url + "soumettre/", {"version": 4}, format="json").status_code, 400)
        reprepare = self.client.post(url + "preparer/", {"version": 4, "document": str(letter.pk)}, format="json")
        self.assertEqual(reprepare.status_code, 200, reprepare.content)
        self.assertNotEqual(reprepare.data["id"], prepared.data["id"])
        self.assertEqual(self.client.get(url + "historique/").data["count"], 2)

    def test_responses_complement_rectification_and_assessment(self):
        obj = self.create_request()
        url = f"/api/v1/demandes/{obj['id']}/"
        items = [entry["id"] for entry in obj["items"]]
        first_letter = self.make_document()
        first = self.client.post(url + "reponses/", {"letter": str(first_letter.pk), "received_on": "2026-09-10", "item_ids": [items[0]]}, format="json")
        self.assertEqual(first.status_code, 201, first.content)
        second_letter = self.make_document()
        second = self.client.post(url + "reponses/", {"letter": str(second_letter.pk), "received_on": "2026-09-12", "complement_of": first.data["id"], "item_ids": [items[1]]}, format="json")
        self.assertEqual(second.status_code, 201, second.content)
        self.assertEqual(self.client.get(url + "reponses/").data["count"], 2)
        rectify = self.client.post(f"/api/v1/reponses/{second.data['id']}/rectifier-liens/", {"version": 1, "remove_link_ids": [second.data["item_links"][0]["id"]], "add_item_ids": [items[2]], "reason": "Lien corrigé"}, format="json")
        self.assertEqual(rectify.status_code, 200, rectify.content)
        self.assertEqual(len(rectify.data["item_links"]), 2)
        self.assertEqual(ResponseItemLink.objects.filter(response_id=second.data["id"], voided_at__isnull=True).count(), 1)
        self.assertEqual(self.client.post(f"/api/v1/reponses/{second.data['id']}/rectifier-liens/", {"version": 1, "add_item_ids": [items[1]], "reason": "Ancien"}, format="json").status_code, 409)
        assessment_url = url + f"elements/{items[0]}/appreciations/"
        assessed = self.client.post(assessment_url, {"version": 0, "receipt": "received", "completeness": "insufficient", "substance": "unsatisfactory", "reason": "Pièce incomplète"}, format="json")
        self.assertEqual(assessed.status_code, 201, assessed.content)
        self.assertEqual(self.client.post(assessment_url, {"version": 0, "receipt": "received", "completeness": "complete", "substance": "satisfactory", "reason": "Correction"}, format="json").status_code, 409)
        corrected = self.client.post(assessment_url, {"version": 1, "receipt": "received", "completeness": "complete", "substance": "satisfactory", "reason": "Après revue"}, format="json")
        self.assertEqual(corrected.status_code, 201, corrected.content)
        self.assertEqual(ItemAssessment.objects.filter(item_id=items[0]).count(), 2)
        self.assertEqual(CommunicationRequest.objects.get(pk=obj["id"]).state, "draft")
        missing = self.client.post(url + f"elements/{items[1]}/appreciations/", {"version": 0, "receipt": "not_received", "completeness": "unknown", "substance": "pending", "reason": "Non reçu"}, format="json")
        self.assertEqual(missing.status_code, 201, missing.content)

    def test_parent_and_proof_scope_rejected(self):
        obj = self.create_request(mode="imported")
        url = f"/api/v1/demandes/{obj['id']}/"
        other_case = Case.objects.create(unit=self.other_unit, classification=0, assignee=self.other, created_by=self.other, next_action="X")
        wrong_doc = self.make_document(case=other_case)
        self.assertEqual(self.client.post(url + "preparer/", {"version": 1, "document": str(wrong_doc.pk)}, format="json").status_code, 400)
        self.client.force_login(self.other)
        self.assertEqual(self.client.post("/api/v1/demandes/", {"case": str(self.case.pk), "target_type": "broker", "target_name": "X", "subject": "X", "mode": "generated", "items": [{"label": "X"}]}, format="json").status_code, 404)
        self.assertEqual(self.client.get(url + "reponses/").status_code, 404)

    def test_audit_failure_rolls_back_and_validation_revocation_is_immediate(self):
        payload = {"case": str(self.case.pk), "target_type": "organization", "target_name": "Société fictive", "subject": "Pièces", "mode": "generated", "items": [{"label": "Facture"}]}
        with patch("requests_app.service.record", side_effect=OperationalError("audit unavailable")):
            failed = self.client.post("/api/v1/demandes/", payload, format="json")
        self.assertEqual(failed.status_code, 503)
        self.assertEqual(CommunicationRequest.objects.count(), 0)
        obj = self.create_request()
        url = f"/api/v1/demandes/{obj['id']}/"
        self.assertEqual(self.client.post(url + "preparer/", {"version": 1}, format="json").status_code, 200)
        self.assertEqual(self.client.post(url + "soumettre/", {"version": 1}, format="json").status_code, 200)
        self.client.force_login(self.manager)
        self.assertEqual(self.client.get("/api/v1/a-valider/").data["count"], 1)
        Delegation.objects.filter(user=self.manager, action=Delegation.Action.REQUEST_VALIDATE).update(revoked_at=timezone.now())
        self.assertEqual(self.client.get("/api/v1/a-valider/").data["count"], 0)
        self.assertEqual(self.client.post(url + "valider/", {"version": 2}, format="json").status_code, 403)
        self.assertEqual(CommunicationRequest.objects.get(pk=obj["id"]).state, "submitted")
