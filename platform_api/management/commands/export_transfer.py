import hashlib
import json
import os
from pathlib import Path

from django.apps import apps
from django.core import serializers
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone


MODEL_LABELS = [
    "auth.Group", "auth.User", "identity.Unit", "identity.Membership", "identity.Delegation",
    "cases.Case", "cases.CaseAssignment", "cases.CaseAction",
    "intelligence.Intelligence", "intelligence.ProtectedSource", "intelligence.CaseIntelligence",
    "intelligence.Dissemination", "intelligence.DisseminationReturn",
    "documents.Document", "documents.FileOperation", "audit.AuditEvent",
]


class Command(BaseCommand):
    help = "Exporter les données applicatives fictives vers un paquet versionné pour répétition PostgreSQL."

    def add_arguments(self, parser):
        parser.add_argument("directory")

    def handle(self, *args, **options):
        target = Path(options["directory"]).resolve()
        if target.exists():
            raise CommandError("Le répertoire cible doit être nouveau.")
        target.mkdir(mode=0o700, parents=True)
        try:
            fixture = []
            counts = {}
            for label in MODEL_LABELS:
                model = apps.get_model(label)
                rows = list(model.objects.order_by("pk"))
                fixture.extend(json.loads(serializers.serialize("json", rows, use_natural_foreign_keys=True)))
                counts[label] = len(rows)
            payload = json.dumps(fixture, ensure_ascii=False, indent=2).encode("utf-8")
            data_path = target / "data.json"
            with data_path.open("xb") as stream:
                stream.write(payload)
            os.chmod(data_path, 0o600)
            manifest = {
                "format": "procezo-transfer-v1",
                "created_at": timezone.now().isoformat(),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "counts": counts,
                "documents": {str(obj.pk): obj.sha256 for obj in apps.get_model("documents.Document").objects.order_by("pk")},
            }
            manifest_path = target / "manifest.json"
            with manifest_path.open("x", encoding="utf-8") as stream:
                json.dump(manifest, stream, ensure_ascii=False, indent=2)
            os.chmod(manifest_path, 0o600)
        except Exception:
            for child in target.iterdir():
                child.unlink()
            target.rmdir()
            raise
        self.stdout.write(self.style.SUCCESS(f"Export versionné créé : {target}"))
