import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import OperationalError, close_old_connections
from django.test import Client, TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from audit.models import AuditEvent
from identity.models import Delegation, Membership, Unit
from identity.policy import can as real_can
from platform_api.errors import Conflict

from .models import Case, CaseAssignment
from .service import create_case, update_case


class CaseApiTests(TestCase):
    def setUp(self):
        user = get_user_model()
        self.manager = user.objects.create_user("manager", password="strong-demo-password")
        self.agent1 = user.objects.create_user("agent1", password="strong-demo-password")
        self.agent2 = user.objects.create_user("agent2", password="strong-demo-password")
        self.outsider = user.objects.create_user("outsider", password="strong-demo-password", is_staff=True, is_superuser=True)
        self.auditor = user.objects.create_user("auditor", password="strong-demo-password")
        self.unit = Unit.objects.create(code="PILOTE", name="Unité pilote")
        self.other_unit = Unit.objects.create(code="AUTRE", name="Autre unité")
        now = timezone.now()
        for actor, role, unit, clearance in [
            (self.manager, Membership.Role.MANAGER, self.unit, 1),
            (self.agent1, Membership.Role.INVESTIGATOR, self.unit, 1),
            (self.agent2, Membership.Role.INVESTIGATOR, self.unit, 1),
            (self.outsider, Membership.Role.MANAGER, self.other_unit, 1),
            (self.auditor, Membership.Role.AUDITOR, self.unit, 1),
        ]:
            Membership.objects.create(user=actor, role=role, unit=unit, clearance=clearance, valid_from=now)
        for actor, action in [(self.manager, Delegation.Action.CASE_CREATE), (self.manager, Delegation.Action.CASE_ASSIGN), (self.auditor, Delegation.Action.AUDIT_READ)]:
            Delegation.objects.create(user=actor, unit=self.unit, action=action, valid_from=now)
        self.client = APIClient()
        self.client.force_login(self.manager)

    def create_case(self, classification=0):
        return self.client.post("/api/v1/dossiers/", {
            "unit": str(self.unit.pk), "classification": classification,
            "assignee": self.agent1.pk, "next_action": "Contrôler la pièce fictive",
            "assignment_reason": "Affectation initiale fictive",
        }, format="json")

    def test_create_read_filter_and_audit(self):
        response = self.create_case()
        self.assertEqual(response.status_code, 201, response.content)
        case_id = response.data["id"]
        self.assertEqual(response.data["version"], 1)
        self.assertEqual(response.data["assignee"], self.agent1.pk)
        self.assertEqual(CaseAssignment.objects.count(), 1)
        self.assertTrue(AuditEvent.objects.filter(action="case.created", resource_id=case_id).exists())
        detail = self.client.get(f"/api/v1/dossiers/{case_id}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data["next_action"], "Contrôler la pièce fictive")
        self.assertTrue(AuditEvent.objects.filter(action="case.read", resource_id=case_id).exists())
        listing = self.client.get("/api/v1/dossiers/", {"ordering": "reference"})
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.data["count"], 1)
        self.assertEqual(self.client.get("/api/v1/dossiers/", {"ordering": "assignee"}).status_code, 400)
        self.assertEqual(self.client.get("/api/v1/dossiers/", {"unit": "bad"}).status_code, 400)
        self.assertEqual(self.client.get("/api/v1/dossiers/", {"page_size": "1000"}).status_code, 400)

    def test_invisible_case_is_404_and_staff_has_no_business_access(self):
        case_id = self.create_case().data["id"]
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(f"/api/v1/dossiers/{case_id}/").status_code, 404)
        self.assertEqual(self.client.get("/api/v1/dossiers/").data["count"], 0)
        self.assertEqual(self.client.post("/api/v1/dossiers/", {"unit": str(self.unit.pk), "classification": 0, "assignee": self.agent1.pk, "next_action": "X", "assignment_reason": "X"}, format="json").status_code, 404)

    def test_reassignment_revocation_and_history(self):
        case_id = self.create_case().data["id"]
        self.client.force_login(self.agent1)
        self.assertEqual(self.client.get(f"/api/v1/dossiers/{case_id}/").status_code, 200)
        self.client.force_login(self.manager)
        reassigned = self.client.post(f"/api/v1/dossiers/{case_id}/affectations/", {"version": 1, "assignee": self.agent2.pk, "reason": "Rééquilibrage fictif"}, format="json")
        self.assertEqual(reassigned.status_code, 200, reassigned.content)
        self.assertEqual(reassigned.data["version"], 2)
        history = self.client.get(f"/api/v1/dossiers/{case_id}/affectations/")
        self.assertEqual(history.data["count"], 2)
        self.assertEqual(history.data["results"][1]["previous_assignee"], self.agent1.pk)
        self.assertEqual(history.data["results"][1]["new_assignee"], self.agent2.pk)
        self.assertEqual(history.data["results"][1]["reason"], "Rééquilibrage fictif")
        self.assertEqual(self.client.get(f"/api/v1/dossiers/{case_id}/chronologie/").data["count"], 2)
        self.client.force_login(self.agent1)
        self.assertEqual(self.client.get(f"/api/v1/dossiers/{case_id}/").status_code, 404)
        self.client.force_login(self.agent2)
        self.assertEqual(self.client.get(f"/api/v1/dossiers/{case_id}/").status_code, 200)
        Membership.objects.filter(user=self.agent2, unit=self.unit).update(revoked_at=timezone.now())
        self.assertEqual(self.client.get(f"/api/v1/dossiers/{case_id}/").status_code, 404)

    def test_stale_version_returns_409_without_overwrite(self):
        case_id = self.create_case().data["id"]
        first = self.client.patch(f"/api/v1/dossiers/{case_id}/", {"version": 1, "next_action": "Premier changement"}, format="json")
        self.assertEqual(first.status_code, 200)
        second = self.client.patch(f"/api/v1/dossiers/{case_id}/", {"version": 1, "next_action": "Écrasement"}, format="json")
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.data["code"], "conflict")
        self.assertEqual(second.data["request_id"], second["X-Request-ID"])
        self.assertEqual(Case.objects.get(pk=case_id).next_action, "Premier changement")
        self.assertEqual(AuditEvent.objects.filter(action="case.updated").count(), 1)

    def test_visible_case_forbidden_action_is_403_and_delegation_revokes(self):
        case_id = self.create_case().data["id"]
        self.client.force_login(self.agent1)
        response = self.client.post(f"/api/v1/dossiers/{case_id}/affectations/", {"version": 1, "assignee": self.agent2.pk, "reason": "Non autorisé"}, format="json")
        self.assertEqual(response.status_code, 403)
        self.client.force_login(self.manager)
        Delegation.objects.filter(user=self.manager, action=Delegation.Action.CASE_ASSIGN).update(revoked_at=timezone.now())
        self.assertEqual(self.client.post(f"/api/v1/dossiers/{case_id}/affectations/", {"version": 1, "assignee": self.agent2.pk, "reason": "Révoqué"}, format="json").status_code, 403)

    def test_audit_failure_rolls_back_mutation_and_blocks_read(self):
        with patch("cases.service.record", side_effect=OperationalError("audit unavailable")):
            response = self.create_case()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(Case.objects.count(), 0)
        case_id = self.create_case().data["id"]
        with patch("cases.views.record", side_effect=OperationalError("audit unavailable")):
            response = self.client.get(f"/api/v1/dossiers/{case_id}/")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("audit unavailable", response.content.decode())

    def test_audit_failure_rolls_back_update_and_reassignment(self):
        case_id = self.create_case().data["id"]
        with patch("cases.service.record", side_effect=OperationalError("audit unavailable")):
            updated = self.client.patch(f"/api/v1/dossiers/{case_id}/", {"version": 1, "next_action": "Ne doit pas rester"}, format="json")
        self.assertEqual(updated.status_code, 503)
        self.assertEqual(Case.objects.get(pk=case_id).version, 1)
        self.assertEqual(Case.objects.get(pk=case_id).next_action, "Contrôler la pièce fictive")
        with patch("cases.service.record", side_effect=OperationalError("audit unavailable")):
            assigned = self.client.post(f"/api/v1/dossiers/{case_id}/affectations/", {"version": 1, "assignee": self.agent2.pk, "reason": "Ne doit pas rester"}, format="json")
        self.assertEqual(assigned.status_code, 503)
        self.assertEqual(Case.objects.get(pk=case_id).assignee_id, self.agent1.pk)
        self.assertEqual(CaseAssignment.objects.filter(case_id=case_id).count(), 1)

    def test_classification_and_expired_delegation(self):
        Membership.objects.filter(user=self.agent1, unit=self.unit).update(clearance=0)
        self.assertEqual(self.create_case(classification=1).status_code, 400)
        self.assertEqual(Case.objects.count(), 0)
        Membership.objects.filter(user=self.agent1, unit=self.unit).update(clearance=1)
        Delegation.objects.filter(user=self.manager, action=Delegation.Action.CASE_CREATE).update(valid_until=timezone.now())
        self.assertEqual(self.create_case(classification=1).status_code, 403)

    def test_clearance_downgrade_hides_restricted_case(self):
        case_id = self.create_case(classification=1).data["id"]
        self.client.force_login(self.agent1)
        self.assertEqual(self.client.get(f"/api/v1/dossiers/{case_id}/").status_code, 200)
        Membership.objects.filter(user=self.agent1, unit=self.unit).update(clearance=0)
        self.assertEqual(self.client.get(f"/api/v1/dossiers/{case_id}/").status_code, 404)

    def test_stale_reassignment_preserves_history(self):
        case_id = self.create_case().data["id"]
        self.assertEqual(self.client.post(f"/api/v1/dossiers/{case_id}/affectations/", {"version": 1, "assignee": self.agent2.pk, "reason": "Premier"}, format="json").status_code, 200)
        stale = self.client.post(f"/api/v1/dossiers/{case_id}/affectations/", {"version": 1, "assignee": self.agent1.pk, "reason": "Second"}, format="json")
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(CaseAssignment.objects.filter(case_id=case_id).count(), 2)

    def test_auditor_can_read_only_own_unit_audit_and_cannot_modify_event(self):
        self.create_case()
        self.client.force_login(self.auditor)
        response = self.client.get("/api/v1/audit/", {"unit": str(self.unit.pk)})
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.data["count"], 1)
        self.assertEqual(self.client.get("/api/v1/audit/", {"unit": str(self.other_unit.pk)}).status_code, 404)
        event = AuditEvent.objects.first()
        event.action = "tampered"
        with self.assertRaises(TypeError):
            event.save()
        with self.assertRaises(TypeError):
            AuditEvent.objects.all().delete()

    def test_audit_classification_is_filtered(self):
        case_id = self.create_case(classification=1).data["id"]
        Membership.objects.filter(user=self.auditor, unit=self.unit).update(clearance=0)
        self.client.force_login(self.auditor)
        response = self.client.get("/api/v1/audit/", {"unit": str(self.unit.pk)})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(any(str(item["resource_id"]) == str(case_id) for item in response.data["results"]))

    def test_csrf_login_and_session_expiry(self):
        browser = Client(enforce_csrf_checks=True)
        bad = browser.post("/api/v1/session/", data='{"username":"manager","password":"strong-demo-password"}', content_type="application/json")
        self.assertEqual(bad.status_code, 403)
        self.assertEqual(bad.json()["code"], "csrf_failed")
        browser.get("/api/v1/session/")
        token = browser.cookies["csrftoken"].value
        good = browser.post("/api/v1/session/", data='{"username":"manager","password":"strong-demo-password"}', content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(good.status_code, 200, good.content)
        self.assertEqual(browser.get("/api/v1/dossiers/").status_code, 200)
        token = browser.cookies["csrftoken"].value
        self.assertEqual(browser.delete("/api/v1/session/", HTTP_X_CSRFTOKEN=token).status_code, 204)
        self.assertEqual(browser.get("/api/v1/dossiers/").status_code, 403)
        browser.force_login(self.manager)
        session = browser.session
        session.set_expiry(-1)
        session.save()
        self.assertEqual(browser.get("/api/v1/dossiers/").status_code, 403)


class ConcurrentCaseTests(TransactionTestCase):
    def test_two_sqlite_writers_keep_one_version(self):
        manager = get_user_model().objects.create_user("manager_concurrent", password="strong-demo-password")
        agent = get_user_model().objects.create_user("agent_concurrent", password="strong-demo-password")
        unit = Unit.objects.create(code="CONCURRENT", name="Concurrence fictive")
        now = timezone.now()
        Membership.objects.create(user=manager, unit=unit, role=Membership.Role.MANAGER, clearance=1, valid_from=now)
        Membership.objects.create(user=agent, unit=unit, role=Membership.Role.INVESTIGATOR, clearance=1, valid_from=now)
        for action in (Delegation.Action.CASE_CREATE, Delegation.Action.CASE_ASSIGN):
            Delegation.objects.create(user=manager, unit=unit, action=action, valid_from=now)
        case = create_case(SimpleNamespace(user=manager, request_id=uuid.uuid4()), unit=unit, classification=0, assignee=agent.pk, next_action="Initiale", assignment_reason="Initiale")
        barrier = threading.Barrier(2)
        thread_state = threading.local()

        def gated_can(actor, action, resource=None, context=None):
            result = real_can(actor, action, resource, context)
            if action == "case.update" and not getattr(thread_state, "waited", False):
                thread_state.waited = True
                barrier.wait(timeout=5)
            return result

        def write(next_action):
            close_old_connections()
            try:
                current = Case.objects.get(pk=case.pk)
                update_case(SimpleNamespace(user=manager, request_id=uuid.uuid4()), current, version=1, next_action=next_action)
                return "updated"
            except Conflict:
                return "conflict"
            finally:
                close_old_connections()

        with patch("cases.service.can", side_effect=gated_can):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(write, ["A", "B"]))
        self.assertCountEqual(results, ["updated", "conflict"])
        case.refresh_from_db()
        self.assertEqual(case.version, 2)
        self.assertIn(case.next_action, ("A", "B"))
        self.assertEqual(AuditEvent.objects.filter(action="case.updated", resource_id=case.pk).count(), 1)
