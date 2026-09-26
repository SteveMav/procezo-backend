from django.core.management.base import BaseCommand, CommandError

from platform_api.snapshot import SnapshotError, verify_snapshot


class Command(BaseCommand):
    help = "Vérifier la base, les empreintes et les références d'une sauvegarde Procezo."

    def add_arguments(self, parser):
        parser.add_argument("directory")

    def handle(self, *args, **options):
        try:
            manifest = verify_snapshot(options["directory"])
        except SnapshotError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f"Sauvegarde valide : {manifest['referenced_files']} fichiers référencés, {manifest['counts']['audit_auditevent']} événements d'audit."))
