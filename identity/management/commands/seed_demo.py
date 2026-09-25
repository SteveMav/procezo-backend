import os
import uuid
from types import SimpleNamespace

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from cases.models import Case
from cases.service import create_case
from identity.models import Delegation, Membership, Unit


class Command(BaseCommand):
    help = "Crée une unité, des comptes et un dossier fictifs en développement uniquement."

    def handle(self, *args, **options):
        password = os.environ.get("PROCEZO_DEMO_PASSWORD", "")
        if not settings.DEBUG:
            raise CommandError("Commande réservée à l'environnement de développement.")
        if len(password) < 12:
            raise CommandError("Définissez PROCEZO_DEMO_PASSWORD (12 caractères minimum).")
        now = timezone.now()
        with transaction.atomic():
            unit, _ = Unit.objects.get_or_create(code="DEMO", defaults={"name": "Unité fictive"})
            accounts = {}
            for username in ("demo_manager", "demo_agent_1", "demo_agent_2", "demo_auditor"):
                account, created = get_user_model().objects.get_or_create(username=username)
                if created:
                    account.set_password(password)
                    account.save(update_fields=["password"])
                accounts[username] = account
            for username, role in [
                ("demo_manager", Membership.Role.MANAGER),
                ("demo_agent_1", Membership.Role.INVESTIGATOR),
                ("demo_agent_2", Membership.Role.INVESTIGATOR),
                ("demo_auditor", Membership.Role.AUDITOR),
            ]:
                Membership.objects.get_or_create(user=accounts[username], unit=unit, role=role, defaults={"clearance": 1, "valid_from": now})
            for username, action in [
                ("demo_manager", Delegation.Action.CASE_CREATE),
                ("demo_manager", Delegation.Action.CASE_ASSIGN),
                ("demo_auditor", Delegation.Action.AUDIT_READ),
            ]:
                Delegation.objects.get_or_create(user=accounts[username], unit=unit, action=action, defaults={"valid_from": now})
            case = Case.objects.filter(unit=unit).first()
            if case is None:
                request = SimpleNamespace(user=accounts["demo_manager"], request_id=uuid.uuid4())
                case = create_case(request, unit=unit, classification=0, assignee=accounts["demo_agent_1"].pk, next_action="Vérifier la pièce fictive", assignment_reason="Affectation initiale fictive")
        self.stdout.write(f"Unité fictive : {unit.code} ({unit.pk})")
        self.stdout.write(f"Dossier fictif : {case.reference} ({case.pk})")
        self.stdout.write("Comptes fictifs prêts : " + ", ".join(f"{name} (id {account.pk})" for name, account in accounts.items()))
