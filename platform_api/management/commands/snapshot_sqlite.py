from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from platform_api.snapshot import SnapshotError, create_snapshot


class Command(BaseCommand):
    help = "Sauvegarder SQLite et les pièces privées après suspension des écritures."

    def add_arguments(self, parser):
        parser.add_argument("directory", help="Nouveau répertoire de sauvegarde, hors hôte de préférence")
        parser.add_argument("--writes-suspended", action="store_true", help="Confirme que les écritures applicatives et travaux de fichiers sont arrêtés")

    def handle(self, *args, **options):
        if settings.DATABASES["default"]["ENGINE"] != "django.db.backends.sqlite3":
            raise CommandError("Cette commande exige SQLite.")
        if not options["writes_suspended"]:
            raise CommandError("Suspendre les écritures, puis fournir --writes-suspended.")
        try:
            manifest = create_snapshot(settings.DATABASES["default"]["NAME"], settings.PROCEZO_PRIVATE_FILES_ROOT, options["directory"])
        except (SnapshotError, OSError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f"Sauvegarde vérifiée : {Path(options['directory']).resolve()} ({len(manifest['files'])} fichiers)."))
