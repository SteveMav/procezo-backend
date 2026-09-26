import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from audit.models import AuditEvent
from cases.models import Case
from identity.models import Delegation, Membership, Unit

from .models import CaseIntelligence, Dissemination, DisseminationReturn, Intelligence


class IntelligenceApiTests(TestCase):
    def setUp(self):
        users = get_user_model().objects
        self.manager = users.create_user("manager", password="test-password")
        self.agent = users.create_user("agent", password="test-password")
        self.outsider = users.create_user("outsider", password="test-password", is_superuser=True)
        self.recipient = users.create_user("recipient", password="test-password")
        self.unit = Unit.objects.create(code="U1", name="Unité 1")
        self.unit2 = Unit.objects.create(code="U2", name="Unité 2")
        now = timezone.now()
        for user, role, unit in [(self.manager, "manager", self.unit), (self.agent, "investigator", self.unit), (self.outsider, "manager", self.unit2), (self.recipient, "manager", self.unit2)]:
            Membership.objects.create(user=user, role=role, unit=unit, clearance=1, valid_from=now)
        for action in [Delegation.Action.INTELLIGENCE_DISTRIBUTE, Delegation.Action.SOURCE_READ, Delegation.Action.SOURCE_WRITE]:
            Delegation.objects.create(user=self.manager, unit=self.unit, action=action, valid_from=now)
        self.client = APIClient()
        self.client.force_login(self.manager)

    def create_intelligence(self, **extra):
        payload = {"unit": str(self.unit.pk), "classification": 1, "subject": "Alerte fictive", "summary": "Faits anonymisés", "provenance": "rapport de service", "occurred_on": "2026-09-01", "assignee": self.agent.pk}
        payload.update(extra)
        return self.client.post("/api/v1/renseignements/", payload, format="json")

    def test_without_target_source_separated_and_revocation(self):
        response = self.create_intelligence(source_identity="Source fictive X")
        self.assertEqual(response.status_code, 201, response.content)
        item_id = response.data["id"]
        self.assertNotIn("Source fictive X", str(response.data))
        self.client.force_login(self.agent)
        detail = self.client.get(f"/api/v1/renseignements/{item_id}/")
        self.assertEqual(detail.status_code, 200)
        self.assertNotIn("Source fictive X", str(detail.data))
        self.assertEqual(self.client.get(f"/api/v1/renseignements/{item_id}/source/").status_code, 403)
        Membership.objects.filter(user=self.agent).update(revoked_at=timezone.now())
        self.assertEqual(self.client.get(f"/api/v1/renseignements/{item_id}/").status_code, 404)
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(f"/api/v1/renseignements/{item_id}/").status_code, 404)
        self.client.force_login(self.manager)
        self.assertEqual(self.client.get(f"/api/v1/renseignements/{item_id}/source/").data["identity"], "Source fictive X")
        self.assertTrue(AuditEvent.objects.filter(action="source.read", resource_id=item_id).exists())

    def test_link_two_cases_and_version_conflict(self):
        item = self.create_intelligence()
        self.assertEqual(item.status_code, 201)
        cases = [Case.objects.create(unit=self.unit, classification=1, assignee=self.agent, created_by=self.manager, next_action="Suite fictive") for _ in range(2)]
        for version, case in enumerate(cases, 1):
            linked = self.client.post(f"/api/v1/renseignements/{item.data['id']}/dossiers/", {"version": version, "case": str(case.pk)}, format="json")
            self.assertEqual(linked.status_code, 201, linked.content)
        self.assertEqual(CaseIntelligence.objects.filter(intelligence_id=item.data["id"]).count(), 2)
        self.assertEqual(self.client.post(f"/api/v1/renseignements/{item.data['id']}/dossiers/", {"version": 1, "case": str(cases[0].pk)}, format="json").status_code, 409)

    def test_two_disseminations_independent_returns_and_retry(self):
        item = self.create_intelligence(source_identity="Source fictive X")
        url = f"/api/v1/renseignements/{item.data['id']}/diffusions/"
        payload = {"recipient_unit": str(self.unit2.pk), "channel": "note", "expected_action": "Examiner", "sent_at": timezone.now().isoformat(), "idempotency_key": str(uuid.uuid4())}
        first = self.client.post(url, payload, format="json")
        self.assertEqual(first.status_code, 201, first.content)
        self.assertEqual(self.client.post(url, payload, format="json").status_code, 200)
        payload["idempotency_key"] = str(uuid.uuid4())
        second = self.client.post(url, payload, format="json")
        self.assertEqual(second.status_code, 201)
        self.assertEqual(Dissemination.objects.count(), 2)
        return_url = f"/api/v1/diffusions/{first.data['id']}/retours/"
        ret = {"acknowledged": True, "received_at": timezone.now().isoformat(), "note": "Accusé fictif", "idempotency_key": str(uuid.uuid4())}
        self.assertEqual(self.client.post(return_url, ret, format="json").status_code, 201)
        self.assertEqual(self.client.post(return_url, ret, format="json").status_code, 200)
        self.assertEqual(DisseminationReturn.objects.count(), 1)
        self.assertEqual(Dissemination.objects.get(pk=second.data["id"]).returns.count(), 0)
        self.assertNotIn("Source fictive X", str(self.client.get(url).data))
        self.client.force_login(self.recipient)
        self.assertEqual(self.client.get(f"/api/v1/renseignements/{item.data['id']}/").status_code, 200)
        self.assertEqual(self.client.get(f"/api/v1/renseignements/{item.data['id']}/source/").status_code, 403)
        self.assertEqual(self.client.get(f"/api/v1/diffusions/{first.data['id']}/").status_code, 200)
        self.assertEqual(self.client.post(f"/api/v1/diffusions/{second.data['id']}/retours/", {**ret, "idempotency_key": str(uuid.uuid4())}, format="json").status_code, 201)
        self.assertEqual(Dissemination.objects.get(pk=second.data["id"]).returns.count(), 1)

    def test_audit_failure_rolls_back_creation(self):
        with patch("intelligence.views.record", side_effect=RuntimeError("audit down")):
            with self.assertRaises(RuntimeError):
                self.create_intelligence()
        self.assertEqual(Intelligence.objects.count(), 0)

    def test_pending_dissemination_is_hidden_until_confirmation(self):
        item = self.create_intelligence()
        payload = {"recipient_unit": str(self.unit2.pk), "channel": "note", "expected_action": "Examiner", "idempotency_key": str(uuid.uuid4())}
        response = self.client.post(f"/api/v1/renseignements/{item.data['id']}/diffusions/", payload, format="json")
        self.assertEqual(response.status_code, 201)
        url = f"/api/v1/diffusions/{response.data['id']}/"
        self.client.force_login(self.recipient)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.manager)
        sent_at = timezone.now().isoformat()
        confirm = self.client.post(f"{url}confirmer/", {"sent_at": sent_at}, format="json")
        self.assertEqual(confirm.status_code, 200)
        self.assertEqual(self.client.post(f"{url}confirmer/", {"sent_at": sent_at}, format="json").status_code, 200)
        self.client.force_login(self.recipient)
        self.assertEqual(self.client.get(url).status_code, 200)
