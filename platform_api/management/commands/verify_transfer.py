import hashlib
import json
from pathlib import Path

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError

from documents.models import Document
from documents.service import private_path


class Command(BaseCommand):
    help = "Vérifier un paquet de transfert contre la base cible et les pièces privées."

    def add_arguments(self, parser):
        parser.add_argument("directory")

    def handle(self, *args, **options):
        target = Path(options["directory"])
        try:
            manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
            payload = (target / "data.json").read_bytes()
        except (OSError, ValueError) as exc:
            raise CommandError("Paquet de transfert illisible.") from exc
        if manifest.get("format") != "procezo-transfer-v1" or hashlib.sha256(payload).hexdigest() != manifest.get("sha256"):
            raise CommandError("Version ou empreinte du paquet invalide.")
        for label, expected in manifest["counts"].items():
            actual = apps.get_model(label).objects.count()
            if actual != expected:
                raise CommandError(f"Nombre divergent pour {label}: {actual} au lieu de {expected}.")
        for obj in Document.objects.filter(state=Document.State.ACCEPTED):
            path = private_path(obj.storage_name)
            if not path.is_file():
                raise CommandError(f"Pièce acceptée manquante: {obj.pk}.")
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            if digest.hexdigest() != obj.sha256 or manifest["documents"].get(str(obj.pk)) != obj.sha256:
                raise CommandError(f"Empreinte divergente: {obj.pk}.")
        self.stdout.write(self.style.SUCCESS("Transfert vérifié : paquet, nombres et pièces acceptées."))
