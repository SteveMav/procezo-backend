import hashlib
import io
import sqlite3
import tempfile
import uuid
from contextlib import closing
from pathlib import Path
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection
from django.test import SimpleTestCase, TransactionTestCase
from django.utils import timezone

from audit.models import AuditEvent
from cases.models import Case
from documents.models import Document
from identity.models import Unit
from inspections.models import ObservationSheet, SheetProject
from requests_app.models import ActVersion, CommunicationRequest, RequestResponse

from platform_api.snapshot import TABLES, SnapshotError, create_snapshot, restore_snapshot, verify_snapshot


class SnapshotTests(SimpleTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = self.root / "live" / "database.sqlite3"
        self.db.parent.mkdir()
        self.files = self.root / "live-files"
        self.files.mkdir()
        self.target = self.root / "snapshot"
        names = [uuid.uuid4() for _ in range(3)]
        contents = [b"%PDF-document", b"%PDF-act", b"%PDF-sheet"]
        for folder, name, content in zip(("quarantine", "acts", "sheets"), names, contents):
            path = self.files / folder / str(name)
            path.parent.mkdir()
            path.write_bytes(content)
        with closing(sqlite3.connect(self.db)) as conn:
            for table in TABLES:
                fields = "storage_name TEXT, sha256 TEXT, state TEXT" if table == "documents_document" else "storage_name TEXT, sha256 TEXT" if table in ("requests_app_actversion", "inspections_sheetproject") else "id TEXT"
                conn.execute(f'CREATE TABLE "{table}" ({fields})')
            conn.execute("INSERT INTO documents_document VALUES (?, ?, 'accepted')", (names[0].hex, hashlib.sha256(contents[0]).hexdigest()))
            conn.execute("INSERT INTO requests_app_actversion VALUES (?, ?)", (names[1].hex, hashlib.sha256(contents[1]).hexdigest()))
            conn.execute("INSERT INTO inspections_sheetproject VALUES (?, ?)", (names[2].hex, hashlib.sha256(contents[2]).hexdigest()))
            for table in ("audit_auditevent", "requests_app_requestresponse", "inspections_defense", "decisions_decision", "decisions_gelectransfer"):
                conn.execute(f'INSERT INTO "{table}" VALUES (?)', (str(uuid.uuid4()),))
            conn.commit()

    def test_backup_restore_and_reference_reconciliation(self):
        manifest = create_snapshot(self.db, self.files, self.target)
        self.assertEqual(manifest["referenced_files"], 3)
        self.assertEqual(manifest["counts"]["audit_auditevent"], 1)
        verify_snapshot(self.target)
        call_command("verify_snapshot", str(self.target), stdout=io.StringIO())
        restored_db = self.root / "restored" / "database.sqlite3"
        restored_files = self.root / "restored-files"
        call_command("restore_snapshot", str(self.target), database=str(restored_db), private_root=str(restored_files), stdout=io.StringIO())
        self.assertEqual(restored_db.read_bytes(), (self.target / "database.sqlite3").read_bytes())
        self.assertEqual({p.relative_to(restored_files).as_posix() for p in restored_files.rglob("*") if p.is_file()}, set(manifest["files"]))
        with self.assertRaises(SnapshotError):
            restore_snapshot(self.target, restored_db, self.root / "another-files")

    def test_tampering_and_missing_reference_fail_closed(self):
        create_snapshot(self.db, self.files, self.target)
        path = next((self.target / "files" / "acts").iterdir())
        path.write_bytes(b"tampered")
        with self.assertRaises(SnapshotError):
            verify_snapshot(self.target)
        with self.assertRaises(SnapshotError):
            restore_snapshot(self.target, self.root / "recovered.sqlite3", self.root / "recovered-files")
        self.assertFalse((self.root / "recovered.sqlite3").exists())
        path.write_bytes(next((self.files / "acts").iterdir()).read_bytes())
        (self.files / "sheets" / next((self.files / "sheets").iterdir()).name).unlink()
        with self.assertRaises(SnapshotError):
            create_snapshot(self.db, self.files, self.root / "second-snapshot")
        self.assertFalse((self.root / "second-snapshot").exists())

    def test_manifest_rejects_inventory_change(self):
        create_snapshot(self.db, self.files, self.target)
        (self.target / "files" / "quarantine" / "unexpected").write_bytes(b"extra")
        with self.assertRaises(SnapshotError):
            verify_snapshot(self.target)


@skipUnless(connection.vendor == "sqlite", "Exercice de restauration spécifique à SQLite")
class SQLiteRestorationExercise(TransactionTestCase):
    def test_real_schema_restores_act_response_file_and_audit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            user = get_user_model().objects.create_user("restore-user")
            unit = Unit.objects.create(code="RESTORE", name="Unité fictive")
            case = Case.objects.create(unit=unit, classification=0, assignee=user, created_by=user, next_action="Vérifier")
            private = root / "private"
            private.mkdir()

            def stored(folder, content):
                name = uuid.uuid4()
                path = private / folder / str(name)
                path.parent.mkdir(exist_ok=True)
                path.write_bytes(content)
                return name, hashlib.sha256(content).hexdigest()

            document_name, document_hash = stored("quarantine", b"%PDF-document-fictif")
            document = Document.objects.create(case=case, original_name="réponse.pdf", content_type="application/pdf", size=21, sha256=document_hash, state="accepted", storage_name=document_name, slot=1, uploaded_by=user)
            request = CommunicationRequest.objects.create(case=case, author=user, target_type="broker", target_name="Tiers fictif", subject="Pièces", mode="generated")
            act_name, act_hash = stored("acts", b"%PDF-acte-fictif")
            ActVersion.objects.create(request=request, request_version=1, mode="generated", storage_name=act_name, sha256=act_hash, prepared_by=user)
            RequestResponse.objects.create(request=request, letter=document, received_on=timezone.localdate(), recorded_by=user)
            sheet = ObservationSheet.objects.create(case=case, author=user, origin="field", recipient_address="Adresse", concerned_party="Tiers", facts="Faits")
            sheet_name, sheet_hash = stored("sheets", b"%PDF-feuille-fictive")
            SheetProject.objects.create(sheet=sheet, sheet_version=1, storage_name=sheet_name, sha256=sheet_hash, prepared_by=user)
            AuditEvent.objects.create(actor=user, unit=unit, action="request.response.recorded", resource_type="case", resource_id=case.pk, request_id=uuid.uuid4())
            source = root / "source" / "database.sqlite3"
            source.parent.mkdir()
            with closing(sqlite3.connect(source)) as destination:
                connection.connection.backup(destination)
            snapshot = root / "snapshot"
            manifest = create_snapshot(source, private, snapshot)
            restored_db = root / "recovered" / "database.sqlite3"
            restored_files = root / "recovered-files"
            restore_snapshot(snapshot, restored_db, restored_files)
            self.assertEqual(manifest["referenced_files"], 3)
            for table in ("audit_auditevent", "documents_document", "requests_app_actversion", "requests_app_requestresponse", "inspections_sheetproject"):
                self.assertEqual(manifest["counts"][table], 1)
            self.assertEqual({name: hashlib.sha256((restored_files / folder / str(name)).read_bytes()).hexdigest() for folder, name in (("quarantine", document_name), ("acts", act_name), ("sheets", sheet_name))}, {document_name: document_hash, act_name: act_hash, sheet_name: sheet_hash})
            with closing(sqlite3.connect(restored_db)) as recovered:
                self.assertEqual(recovered.execute("SELECT count(*) FROM audit_auditevent").fetchone()[0], 1)
                self.assertEqual(recovered.execute("SELECT count(*) FROM requests_app_requestresponse").fetchone()[0], 1)
