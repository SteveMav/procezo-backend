from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from platform_api.snapshot import SnapshotError, restore_snapshot


class Command(BaseCommand):
    help = "Restaurer une sauvegarde dans des chemins neufs, sans toucher à l'instance courante."

    def add_arguments(self, parser):
        parser.add_argument("directory")
        parser.add_argument("--database", required=True)
        parser.add_argument("--private-root", required=True)

    def handle(self, *args, **options):
        try:
            manifest = restore_snapshot(options["directory"], options["database"], options["private_root"])
        except (SnapshotError, OSError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f"Restauration vérifiée : {Path(options['database']).resolve()} ; {len(manifest['files'])} fichiers."))
