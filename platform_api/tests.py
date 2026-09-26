import hashlib
import json
import tempfile
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError
from django.contrib.auth import get_user_model
from django.test import TestCase

from identity.models import Unit


class TransferTests(TestCase):
    def test_export_manifest_and_verification(self):
        get_user_model().objects.create_user("transfer-demo", password="test-password")
        Unit.objects.create(code="DEMO", name="Unité fictive")
        with tempfile.TemporaryDirectory() as root:
            target = Path(root) / "transfer"
            call_command("export_transfer", str(target), verbosity=0)
            manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["format"], "procezo-transfer-v1")
            self.assertEqual(manifest["counts"]["auth.User"], 1)
            self.assertEqual(manifest["counts"]["identity.Unit"], 1)
            self.assertEqual(manifest["sha256"], hashlib.sha256((target / "data.json").read_bytes()).hexdigest())
            call_command("verify_transfer", str(target), verbosity=0)
            (target / "data.json").write_text('{"tampered":true}', encoding="utf-8")
            with self.assertRaises(CommandError):
                call_command("verify_transfer", str(target), verbosity=0)
