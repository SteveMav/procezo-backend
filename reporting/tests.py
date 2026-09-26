from datetime import timedelta
import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import OperationalError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from audit.models import AuditEvent
from cases.models import Case
from decisions.models import Decision, GelecTransfer
from documents.models import Document
from identity.models import Delegation, Membership, Unit
from inspections.models import Defense, ObservationSheet
from intelligence.models import CaseIntelligence, Dissemination, DisseminationReturn, Intelligence, ProtectedSource
from requests_app.models import ActVersion, CommunicationRequest, RequestIssuance, RequestResponse


class StatisticsTests(TestCase):
    def setUp(self):
        users = get_user_model().objects
        self.manager = users.create_user("report-manager", password="test-password")
        self.agent = users.create_user("report-agent", password="test-password")
        self.other = users.create_user("report-other", password="test-password", is_staff=True, is_superuser=True)
        self.unit = Unit.objects.create(code="REPORT", name="Rapports")
        self.other_unit = Unit.objects.create(code="REPORT-OTHER", name="Autre unité")
        now = timezone.now()
        for user, role, unit in [(self.manager, "manager", self.unit), (self.agent, "investigator", self.unit), (self.other, "manager", self.other_unit)]:
            Membership.objects.create(user=user, role=role, unit=unit, clearance=1, valid_from=now)
        Delegation.objects.create(user=self.manager, unit=self.unit, action=Delegation.Action.INTELLIGENCE_DISTRIBUTE, valid_from=now)
        self.case = Case.objects.create(unit=self.unit, classification=1, assignee=self.agent, created_by=self.manager, next_action="Examiner")
        self.second_case = Case.objects.create(unit=self.unit, classification=1, assignee=self.agent, created_by=self.manager, next_action="Contrôler")
        self.hidden_case = Case.objects.create(unit=self.other_unit, classification=1, assignee=self.other, created_by=self.other, next_action="Autre")
        self.item = Intelligence.objects.create(unit=self.unit, classification=1, subject="Fait fictif", summary="Résumé", provenance="rapport de service", occurred_on=now.date(), assignee=self.agent, created_by=self.manager)
        self.second_item = Intelligence.objects.create(unit=self.unit, classification=1, subject="Autre fait", summary="Résumé", provenance="douane", occurred_on=now.date(), assignee=self.manager, created_by=self.manager)
        self.hidden_item = Intelligence.objects.create(unit=self.other_unit, classification=1, subject="Secret", summary="Résumé", provenance="secret externe", occurred_on=now.date(), assignee=self.other, created_by=self.other)
        ProtectedSource.objects.create(intelligence=self.item, identity="Identité très protégée")
        for case in (self.case, self.second_case):
            CaseIntelligence.objects.create(intelligence=self.item, case=case, linked_by=self.manager)
        CaseIntelligence.objects.create(intelligence=self.second_item, case=self.case, linked_by=self.manager)
        CaseIntelligence.objects.create(intelligence=self.hidden_item, case=self.hidden_case, linked_by=self.other)
        for _ in range(2):
            dissemination = Dissemination.objects.create(intelligence=self.item, recipient_unit=self.other_unit, channel="note", expected_action="Examiner", sent_at=now, idempotency_key=uuid.uuid4(), created_by=self.manager)
            DisseminationReturn.objects.create(dissemination=dissemination, acknowledged=True, received_at=now, idempotency_key=uuid.uuid4(), recorded_by=self.other)
        self.request = CommunicationRequest.objects.create(case=self.case, author=self.agent, target_type="broker", target_name="Tiers", subject="Pièces", mode="generated", state="issued")
        document = Document.objects.create(case=self.case, original_name="preuve.pdf", content_type="application/pdf", size=1, sha256="0" * 64, state="accepted", slot=1, uploaded_by=self.agent)
        act = ActVersion.objects.create(request=self.request, request_version=1, mode="generated", sha256="0" * 64, prepared_by=self.agent)
        RequestIssuance.objects.create(request=self.request, act=act, signature_proof=document, dispatch_proof=document, issued_by=self.manager, issued_at=now, idempotency_key=uuid.uuid4())
        self.response = RequestResponse.objects.create(request=self.request, letter=document, received_on=now.date(), recorded_by=self.agent)
        self.sheet = ObservationSheet.objects.create(case=self.case, author=self.agent, origin="field", recipient_address="Adresse", concerned_party="Tiers", facts="Faits")
        self.defense = Defense.objects.create(sheet=self.sheet, letter=document, received_on=now.date(), recorded_by=self.agent)
        self.client = APIClient()
        self.client.force_login(self.manager)
        today = now.date().isoformat()
        self.params = {"unit": str(self.unit.pk), "start": today, "end": today}

    def _indicator(self, result, key, provenance=None):
        return next(item for family in result.data["families"] for item in family["indicators"] if item["key"] == key and item.get("provenance") == provenance)

    def test_families_drilldown_deduplication_and_masks(self):
        response = self.client.get("/api/v1/statistiques/", self.params)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual([family["key"] for family in response.data["families"]], ["requests", "sheets", "classifications", "pv", "intelligence"])
        for key in ("requests.issued", "requests.responses", "sheets.created", "sheets.defenses"):
            metric = self._indicator(response, key)
            self.assertEqual(metric["value"], 1)
            detail = self.client.get(metric["detail_url"])
            self.assertEqual(detail.status_code, 200, detail.content)
            self.assertEqual(detail.data["count"], metric["value"])
            self.assertEqual(len(detail.data["results"]), 1)
        received = self._indicator(response, "intelligence.received")
        self.assertEqual(received["value"], 2)
        linked = self._indicator(response, "intelligence.linked_cases")
        self.assertEqual(linked["value"], 2)
        detail = self.client.get(linked["detail_url"])
        self.assertEqual(detail.data["count"], 2)
        self.assertEqual({row["id"] for row in detail.data["results"]}, {str(self.item.pk), str(self.second_item.pk)})
        linked_cases = self._indicator(response, "cases.with_intelligence")
        self.assertEqual(linked_cases["value"], 2)
        self.assertEqual({row["id"] for row in self.client.get(linked_cases["detail_url"]).data["results"]}, {str(self.case.pk), str(self.second_case.pk)})
        self.assertEqual(self._indicator(response, "intelligence.received", "rapport de service")["value"], 1)
        for key in ("intelligence.distributed", "intelligence.with_returns"):
            metric = self._indicator(response, key)
            self.assertEqual(metric["value"], 1)
            self.assertEqual(self.client.get(metric["detail_url"]).data["count"], 1)
        self.assertIsNone(self._indicator(response, "cases.pv_proven")["value"])
        self.assertIsNone(self._indicator(response, "cases.pv_proven")["detail_url"])
        self.assertIsNone(self._indicator(response, "sheets.issued")["value"])
        self.assertIsNone(self._indicator(response, "intelligence.effects")["value"])
        self.assertNotIn("Identité très protégée", str(response.data) + str(detail.data))
        self.assertNotIn("secret externe", str(response.data))
        self.assertTrue(AuditEvent.objects.filter(action="statistics.read", unit=self.unit).exists())
        self.assertTrue(AuditEvent.objects.filter(action="statistics.detail.read", unit=self.unit).exists())

    def test_classification_current_decision_and_gelec_not_pv(self):
        from requests_app.models import ItemAssessment, RequestedItem
        item = RequestedItem.objects.create(request=self.request, number=1, label="Pièce", assessment_version=1)
        assessment = ItemAssessment.objects.create(item=item, version=1, receipt="received", completeness="complete", substance="satisfactory", reason="Motif", actor=self.agent)
        now = timezone.now()
        first = Decision.objects.create(case=self.case, author=self.agent, kind="classification", reason="Motif", state="validated", validator=self.manager, validated_at=now, request_assessment=assessment)
        Decision.objects.create(case=self.second_case, author=self.agent, kind="gelec", reason="Motif", state="validated", validator=self.manager, validated_at=now, request_assessment=assessment)
        response = self.client.get("/api/v1/statistiques/", self.params)
        self.assertEqual(self._indicator(response, "cases.classified")["value"], 1)
        self.assertEqual(self.client.get(self._indicator(response, "cases.classified")["detail_url"]).data["results"][0]["id"], str(self.case.pk))
        corrected = Decision.objects.create(case=self.case, author=self.agent, kind="gelec", reason="Rectification", state="validated", validator=self.manager, validated_at=now, request_assessment=assessment, replaces=first)
        GelecTransfer.objects.create(decision=corrected, prepared_by=self.manager, state="confirmed", reference="REF", transmitted_at=now, received_at=now)
        response = self.client.get("/api/v1/statistiques/", self.params)
        self.assertEqual(self._indicator(response, "cases.classified")["value"], 0)
        self.assertIsNone(self._indicator(response, "cases.pv_proven")["value"])

    def test_scope_revocation_dates_and_audit_failure(self):
        self.client.force_login(self.agent)
        response = self.client.get("/api/v1/statistiques/", self.params)
        self.assertEqual(self._indicator(response, "intelligence.received")["value"], 1)
        self.assertEqual(self._indicator(response, "intelligence.linked_cases")["value"], 1)
        self.assertIsNone(self._indicator(response, "intelligence.distributed")["value"])
        self.assertEqual(self.client.get("/api/v1/statistiques/intelligence.distributed/", self.params).status_code, 404)
        self.assertEqual(self.client.get("/api/v1/statistiques/", {**self.params, "unit": str(self.other_unit.pk)}).status_code, 404)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get("/api/v1/statistiques/", self.params).status_code, 404)
        self.client.force_login(self.manager)
        yesterday = (timezone.now().date() - timedelta(days=1)).isoformat()
        self.assertEqual(self._indicator(self.client.get("/api/v1/statistiques/", {**self.params, "start": yesterday, "end": yesterday}), "intelligence.received")["value"], 0)
        self.assertEqual(self.client.get("/api/v1/statistiques/", {**self.params, "start": self.params["end"], "end": yesterday}).status_code, 400)
        self.assertEqual(self.client.get("/api/v1/statistiques/unknown/", self.params).status_code, 404)
        self.assertEqual(self.client.get("/api/v1/statistiques/requests.issued/", {**self.params, "provenance": "douane"}).status_code, 400)
        with patch("reporting.views.record", side_effect=OperationalError("audit unavailable")):
            self.assertEqual(self.client.get("/api/v1/statistiques/", self.params).status_code, 503)
            self.assertEqual(self.client.get("/api/v1/statistiques/intelligence.received/", self.params).status_code, 503)
        Membership.objects.filter(user=self.manager).update(revoked_at=timezone.now())
        self.assertEqual(self.client.get("/api/v1/statistiques/", self.params).status_code, 404)

    def test_detail_pagination_preserves_aggregate(self):
        for number in range(23):
            Intelligence.objects.create(unit=self.unit, classification=0, subject=f"Fait {number}", summary="Résumé", provenance="douane", occurred_on=timezone.now().date(), assignee=self.manager, created_by=self.manager)
        response = self.client.get("/api/v1/statistiques/", self.params)
        metric = self._indicator(response, "intelligence.received")
        self.assertEqual(metric["value"], 25)
        first = self.client.get(metric["detail_url"] + "&page_size=10")
        self.assertEqual(first.data["count"], 25)
        self.assertEqual(len(first.data["results"]), 10)
        self.assertIsNotNone(first.data["next"])
        second = self.client.get(first.data["next"])
        self.assertEqual(second.data["count"], 25)
        self.assertEqual(len(second.data["results"]), 10)
        self.assertFalse(set(row["id"] for row in first.data["results"]) & set(row["id"] for row in second.data["results"]))
