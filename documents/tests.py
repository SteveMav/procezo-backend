import tempfile
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from audit.models import AuditEvent
from cases.models import Case
from identity.models import Delegation, Membership, Unit
from intelligence.models import Dissemination, Intelligence
from platform_api.errors import DependencyUnavailable

from .models import Document
from .service import private_path
from .service import upload_document


class DocumentApiTests(TestCase):
    def setUp(self):
        self.private = tempfile.TemporaryDirectory()
        self.addCleanup(self.private.cleanup)
        self.settings = override_settings(PROCEZO_PRIVATE_FILES_ROOT=self.private.name, PROCEZO_CLAMSCAN_PATH="")
        self.settings.enable()
        self.addCleanup(self.settings.disable)
        users = get_user_model().objects
        self.manager = users.create_user("manager", password="test-password")
        self.outsider = users.create_user("outsider", password="test-password", is_staff=True)
        self.unit = Unit.objects.create(code="U1", name="Unité 1")
        Membership.objects.create(user=self.manager, unit=self.unit, role="manager", clearance=1, valid_from=timezone.now())
        self.case = Case.objects.create(unit=self.unit, classification=1, assignee=self.manager, created_by=self.manager, next_action="Suite fictive")
        self.client = APIClient()
        self.client.force_login(self.manager)

    def upload(self, content=b"%PDF-1.4\nfiction", name="../../source.pdf"):
        return self.client.post("/api/v1/documents/", {"case": str(self.case.pk), "file": SimpleUploadedFile(name, content, content_type="application/pdf")}, format="multipart")

    def test_quarantine_rescan_download_and_revocation(self):
        response = self.upload()
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.data["state"], "quarantine")
        document_id = response.data["id"]
        url = f"/api/v1/documents/{document_id}/telecharger/"
        self.assertEqual(self.client.get(url).status_code, 403)
        with patch("documents.service.scan", return_value="clean"):
            rescan = self.client.post(f"/api/v1/documents/{document_id}/reanalyser/")
        self.assertEqual(rescan.data["state"], "accepted")
        download = self.client.get(url)
        self.assertEqual(download.status_code, 200)
        self.assertEqual(b"".join(download.streaming_content), b"%PDF-1.4\nfiction")
        self.assertTrue(AuditEvent.objects.filter(action="document.download").exists())
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.manager)
        Membership.objects.filter(user=self.manager).update(revoked_at=timezone.now())
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_invalid_type_and_missing_file(self):
        self.assertEqual(self.upload(b"not a PDF").status_code, 400)
        with patch("documents.service.scan", return_value="clean"):
            response = self.upload()
        document = Document.objects.get(pk=response.data["id"])
        Path(private_path(document.storage_name)).unlink()
        self.assertEqual(self.client.get(f"/api/v1/documents/{document.pk}/telecharger/").status_code, 503)
        document.refresh_from_db()
        self.assertEqual(document.state, "missing")

    def test_infected_file_never_downloads(self):
        with patch("documents.service.scan", return_value="infected"):
            response = self.upload()
        self.assertEqual(response.data["state"], "rejected")
        self.assertEqual(self.client.get(f"/api/v1/documents/{response.data['id']}/telecharger/").status_code, 403)

    def test_interrupted_upload_has_no_document_or_partial_file(self):
        def broken_chunks():
            yield b"%PDF-1.4"
            raise OSError("storage interrupted")

        upload = SimpleNamespace(name="fiction.pdf", size=100, chunks=broken_chunks)
        request = SimpleNamespace(user=self.manager, request_id=uuid.uuid4())
        with self.assertRaises(DependencyUnavailable):
            upload_document(request, parent=self.case, upload=upload)
        self.assertEqual(Document.objects.count(), 0)
        self.assertEqual(list((Path(self.private.name) / "quarantine").iterdir()), [])

    def test_download_fails_if_audit_cannot_persist(self):
        with patch("documents.service.scan", return_value="clean"):
            response = self.upload()
        with patch("documents.views.record", side_effect=RuntimeError("audit down")):
            with self.assertRaises(RuntimeError):
                self.client.get(f"/api/v1/documents/{response.data['id']}/telecharger/")

    def test_intelligence_attachment_stays_source_restricted_after_dissemination(self):
        recipient = get_user_model().objects.create_user("recipient", password="test-password")
        recipient_unit = Unit.objects.create(code="U2", name="Unité 2")
        Membership.objects.create(user=recipient, unit=recipient_unit, role="manager", clearance=1, valid_from=timezone.now())
        for action in [Delegation.Action.SOURCE_WRITE, Delegation.Action.SOURCE_READ]:
            Delegation.objects.create(user=self.manager, unit=self.unit, action=action, valid_from=timezone.now())
        item = Intelligence.objects.create(unit=self.unit, classification=1, subject="Fiction", summary="Résumé fictif", provenance="note", occurred_on=timezone.now().date(), assignee=self.manager, created_by=self.manager)
        Dissemination.objects.create(intelligence=item, recipient_unit=recipient_unit, channel="note", expected_action="Lire", sent_at=timezone.now(), idempotency_key=uuid.uuid4(), created_by=self.manager)
        with patch("documents.service.scan", return_value="clean"):
            response = self.client.post("/api/v1/documents/", {"intelligence": str(item.pk), "file": SimpleUploadedFile("source.pdf", b"%PDF-1.4\nfiction")}, format="multipart")
        self.assertEqual(response.status_code, 201, response.content)
        self.client.force_login(recipient)
        self.assertEqual(self.client.get(f"/api/v1/renseignements/{item.pk}/").status_code, 200)
        self.assertEqual(self.client.get(f"/api/v1/documents/{response.data['id']}/").status_code, 403)
        self.assertEqual(self.client.get(f"/api/v1/documents/{response.data['id']}/telecharger/").status_code, 403)
