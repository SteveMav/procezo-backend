import json

from django.core.management.base import BaseCommand, CommandError

from platform_api.operations import health_snapshot


class Command(BaseCommand):
    help = "Émettre des métriques agrégées et un code d'échec si un seuil d'exploitation est franchi."

    def add_arguments(self, parser):
        parser.add_argument("--request-log", help="Journal JSON structuré des requêtes (fichier local protégé)")
        parser.add_argument("--require-log", action="store_true")
        parser.add_argument("--window-minutes", type=int, default=15)
        parser.add_argument("--min-free-bytes", type=int, default=1024**3)
        parser.add_argument("--max-quarantine", type=int, default=0)
        parser.add_argument("--max-scan-failures", type=int, default=0)
        parser.add_argument("--max-api-5xx", type=int, default=0)
        parser.add_argument("--max-database-locks", type=int, default=0)

    def handle(self, *args, **options):
        if options["window_minutes"] < 1 or any(options[key] < 0 for key in ("min_free_bytes", "max_quarantine", "max_scan_failures", "max_api_5xx", "max_database_locks")):
            raise CommandError("Seuils invalides.")
        try:
            report = health_snapshot(**{key: options[key] for key in ("request_log", "require_log", "window_minutes", "min_free_bytes", "max_quarantine", "max_scan_failures", "max_api_5xx", "max_database_locks")})
        except OSError as exc:
            raise CommandError("Journal ou disque indisponible.") from exc
        self.stdout.write(json.dumps(report, ensure_ascii=False))
        if report["alerts"]:
            raise CommandError("Alertes d'exploitation : " + ", ".join(report["alerts"]))
