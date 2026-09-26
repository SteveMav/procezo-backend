import json
import tempfile
import uuid
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from audit.models import AuditEvent
from cases.models import Case
from documents.models import Document, FileOperation
from identity.models import Unit
from platform_api.operations import health_snapshot


class OperationsTests(TestCase):
    def test_health_alerts_use_aggregates_and_safe_logs(self):
        with tempfile.TemporaryDirectory() as directory, override_settings(PROCEZO_PRIVATE_FILES_ROOT=str(Path(directory) / "private")):
            user = get_user_model().objects.create_user("ops-user")
            unit = Unit.objects.create(code="OPS", name="Fictif")
            case = Case.objects.create(unit=unit, classification=0, assignee=user, created_by=user, next_action="Vérifier")
            document = Document.objects.create(case=case, original_name="identité protégée.pdf", content_type="application/pdf", size=1, sha256="0" * 64, slot=1, uploaded_by=user)
            FileOperation.objects.create(document=document, kind="scan", result="unavailable")
            AuditEvent.objects.create(actor=user, unit=unit, action="case.read", resource_type="case", resource_id=case.pk, request_id=uuid.uuid4())
            log = Path(directory) / "requests.jsonl"
            timestamp = timezone.now().isoformat()
            events = [
                {"timestamp": timestamp, "event": "database_locked"},
                {"timestamp": timestamp, "event": "audit_failure"},
                {"timestamp": timestamp, "event": "request", "route": "api/v1/demandes/.../preparer/", "status": 500},
            ]
            log.write_text("\n".join(json.dumps(event) for event in events), encoding="utf-8")
            report = health_snapshot(request_log=log, require_log=True, min_free_bytes=0)
            self.assertEqual(report["quarantine_count"], 1)
            self.assertEqual(report["scan_failures"], 1)
            self.assertEqual(set(report["alerts"]), {"quarantine_backlog", "scanner_unavailable", "scanner_unconfigured", "database_locks", "audit_failure", "api_errors", "pdf_failure"})
            self.assertNotIn("identité protégée", str(report))
            self.assertIn("request_log_missing", health_snapshot(require_log=True, min_free_bytes=0)["alerts"])
