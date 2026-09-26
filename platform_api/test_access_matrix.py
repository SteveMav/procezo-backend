import hashlib
import tempfile
import uuid
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from cases.models import Case
from decisions.models import Decision, GelecTransfer
from documents.models import Document
from identity.models import Membership, Unit
from inspections.models import ObservationSheet, SheetProject
from intelligence.models import Intelligence, ProtectedSource
from requests_app.models import ActVersion, CommunicationRequest, ItemAssessment, RequestedItem


class CrossDomainAccessTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.private = override_settings(PROCEZO_PRIVATE_FILES_ROOT=self.temp.name)
        self.private.enable()
        self.addCleanup(self.private.disable)
        users = get_user_model().objects
        self.owner = users.create_user("matrix-owner")
        self.outsider = users.create_user("matrix-outsider", is_staff=True, is_superuser=True)
        self.unit = Unit.objects.create(code="MATRIX-A", name="Unité A")
        other_unit = Unit.objects.create(code="MATRIX-B", name="Unité B")
        now = timezone.now()
        Membership.objects.create(user=self.owner, unit=self.unit, role="manager", clearance=1, valid_from=now)
        Membership.objects.create(user=self.outsider, unit=other_unit, role="manager", clearance=1, valid_from=now)
        self.case = Case.objects.create(unit=self.unit, classification=1, assignee=self.owner, created_by=self.owner, next_action="Dossier très réservé")
        self.intelligence = Intelligence.objects.create(unit=self.unit, classification=1, subject="Sujet réservé", summary="Résumé réservé", provenance="rapport", occurred_on=now.date(), assignee=self.owner, created_by=self.owner)
        ProtectedSource.objects.create(intelligence=self.intelligence, identity="Identité source très protégée")
        payload = b"%PDF-1.4\nsource fictive"
        self.document = Document.objects.create(case=self.case, original_name="preuve réservée.pdf", content_type="application/pdf", size=len(payload), sha256=hashlib.sha256(payload).hexdigest(), state="accepted", slot=1, uploaded_by=self.owner)
        path = Path(self.temp.name) / "quarantine" / str(self.document.storage_name)
        path.parent.mkdir()
        path.write_bytes(payload)
        self.request = CommunicationRequest.objects.create(case=self.case, author=self.owner, target_type="broker", target_name="Tiers réservé", subject="Objet", mode="generated")
        item = RequestedItem.objects.create(request=self.request, number=1, label="Pièce")
        assessment = ItemAssessment.objects.create(item=item, version=1, receipt="received", completeness="complete", substance="satisfactory", reason="Apprécié", actor=self.owner)
        self.act = ActVersion.objects.create(request=self.request, request_version=1, mode="generated", storage_name=uuid.uuid4(), sha256="0" * 64, prepared_by=self.owner)
        self.sheet = ObservationSheet.objects.create(case=self.case, author=self.owner, origin="field", recipient_address="Adresse", concerned_party="Tiers", facts="Constats")
        self.project = SheetProject.objects.create(sheet=self.sheet, sheet_version=1, storage_name=uuid.uuid4(), sha256="0" * 64, prepared_by=self.owner)
        self.decision = Decision.objects.create(case=self.case, author=self.owner, kind="gelec", reason="Motif", request_assessment=assessment, state="validated", validator=self.owner, validated_at=now)
        self.transfer = GelecTransfer.objects.create(decision=self.decision, prepared_by=self.owner)
        self.client = APIClient()
        self.client.force_login(self.outsider)

    def _assert_hidden(self, response):
        self.assertEqual(response.status_code, 404, response.content)
        self.assertEqual(response.data["code"], "not_found")
        self.assertIn("request_id", response.data)
        self.assertNotIn("réservé", str(response.data).lower())
        self.assertNotIn("protégée", str(response.data).lower())

    def test_lists_details_files_and_aggregates_do_not_reveal_foreign_unit(self):
        for url in (
            "/api/v1/dossiers/", "/api/v1/renseignements/", "/api/v1/mon-travail/?kind=cases",
            "/api/v1/mon-travail/?kind=requests", "/api/v1/mon-travail/?kind=decisions",
            "/api/v1/a-valider/?kind=requests", "/api/v1/a-valider/?kind=decisions",
        ):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, (url, response.content))
            self.assertEqual(response.data["count"], 0, url)
            self.assertNotIn(str(self.case.pk), str(response.data))
        for url in (
            f"/api/v1/dossiers/{self.case.pk}/", f"/api/v1/renseignements/{self.intelligence.pk}/",
            f"/api/v1/renseignements/{self.intelligence.pk}/source/", f"/api/v1/documents/{self.document.pk}/",
            f"/api/v1/documents/{self.document.pk}/telecharger/", f"/api/v1/demandes/{self.request.pk}/",
            f"/api/v1/actes/{self.act.pk}/telecharger/", f"/api/v1/feuilles/{self.sheet.pk}/",
            f"/api/v1/projets-feuille/{self.project.pk}/telecharger/", f"/api/v1/decisions/{self.decision.pk}/",
            f"/api/v1/transferts-gelec/{self.transfer.pk}/",
            f"/api/v1/documents/?case={self.case.pk}", f"/api/v1/demandes/?case={self.case.pk}",
            f"/api/v1/missions/?case={self.case.pk}", f"/api/v1/feuilles/?case={self.case.pk}",
            f"/api/v1/decisions/?case={self.case.pk}", f"/api/v1/transferts-gelec/?case={self.case.pk}",
            f"/api/v1/statistiques/?unit={self.unit.pk}&start={timezone.now().date()}&end={timezone.now().date()}",
        ):
            self._assert_hidden(self.client.get(url))

    def test_create_and_update_through_foreign_parent_are_refused(self):
        payload = {"case": str(self.case.pk), "target_type": "broker", "target_name": "Tiers", "subject": "Objet", "mode": "generated", "items": [{"label": "Pièce"}]}
        self._assert_hidden(self.client.post("/api/v1/demandes/", payload, format="json"))
        self._assert_hidden(self.client.patch(f"/api/v1/dossiers/{self.case.pk}/", {"version": 1, "next_action": "Interdit"}, format="json"))
        self._assert_hidden(self.client.post("/api/v1/documents/", {"case": str(self.case.pk), "file": SimpleUploadedFile("proof.pdf", b"%PDF-1.4\nfiction")}, format="multipart"))
        self.assertEqual(CommunicationRequest.objects.count(), 1)
        self.assertEqual(Document.objects.count(), 1)
        self.case.refresh_from_db()
        self.assertEqual(self.case.version, 1)

    def test_error_contract_does_not_echo_untrusted_input(self):
        response = self.client.get("/api/v1/dossiers/?ordering=SECRET_DO_NOT_ECHO")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "validation_error")
        self.assertNotIn("SECRET_DO_NOT_ECHO", str(response.data))
