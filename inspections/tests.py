import hashlib
import tempfile
import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import OperationalError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from audit.models import AuditEvent
from cases.models import Case, CaseAction
from documents.models import Document
from documents.service import private_path
from identity.models import Membership, Unit

from .models import Defense, InspectionMission, ObservationAssessment, ObservationSheet, SheetProject


class InspectionApiTests(TestCase):
    def setUp(self):
        self.private = tempfile.TemporaryDirectory()
        self.addCleanup(self.private.cleanup)
        settings_override = override_settings(PROCEZO_PRIVATE_FILES_ROOT=self.private.name)
        settings_override.enable()
        self.addCleanup(settings_override.disable)
        users = get_user_model().objects
        self.agent = users.create_user("inspection-agent", password="strong-demo-password")
        self.colleague = users.create_user("inspection-colleague", password="strong-demo-password")
        self.manager = users.create_user("inspection-manager", password="strong-demo-password")
        self.other = users.create_user("inspection-other", password="strong-demo-password", is_staff=True, is_superuser=True)
        self.unit = Unit.objects.create(code="INS", name="Inspections")
        self.other_unit = Unit.objects.create(code="OUT", name="Autre unité")
        for actor, role, unit in [
            (self.agent, Membership.Role.INVESTIGATOR, self.unit),
            (self.colleague, Membership.Role.INVESTIGATOR, self.unit),
            (self.manager, Membership.Role.MANAGER, self.unit),
            (self.other, Membership.Role.MANAGER, self.other_unit),
        ]:
            Membership.objects.create(user=actor, unit=unit, role=role, clearance=1, valid_from=timezone.now())
        self.case = Case.objects.create(unit=self.unit, classification=1, assignee=self.agent, created_by=self.manager, next_action="Contrôler")
        self.client = APIClient()
        self.client.force_login(self.agent)

    def document(self, content=b"%PDF-1.4\nfictif\n", case=None):
        case = case or self.case
        name = uuid.uuid4()
        path = private_path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return Document.objects.create(case=case, original_name="fictif.pdf", content_type="application/pdf", size=len(content), sha256=hashlib.sha256(content).hexdigest(), state=Document.State.ACCEPTED, storage_name=name, slot=Document.objects.filter(case=case).count() + 1, uploaded_by=self.agent)

    def mission_payload(self, docs):
        return {"case": str(self.case.pk), "context": "Contrôle fictif", "findings": "Trois constats", "occurred_on": str(timezone.localdate()), "participants": [self.agent.pk, self.colleague.pk], "documents": [str(doc.pk) for doc in docs]}

    def sheet_payload(self, *, origin="field", mission=None, docs=None):
        data = {"case": str(self.case.pk), "origin": origin, "recipient_address": "Adresse fictive", "concerned_party": "Société fictive", "facts": "Faits contrôlés", "observations": [{"facts": "Premier constat", "documents": [str(doc.pk) for doc in (docs or [])]}, {"facts": "Second constat", "documents": []}]}
        if mission:
            data["mission"] = mission
        return data

    def create_sheet(self, **kwargs):
        response = self.client.post("/api/v1/feuilles/", self.sheet_payload(**kwargs), format="json")
        self.assertEqual(response.status_code, 201, response.content)
        return response.data

    def test_mission_pieces_timeline_and_mission_sheet(self):
        docs = [self.document() for _ in range(3)]
        response = self.client.post("/api/v1/missions/", self.mission_payload(docs), format="json")
        self.assertEqual(response.status_code, 201, response.content)
        mission = response.data
        self.assertEqual(len(mission["participants"]), 2)
        self.assertEqual(len(mission["documents"]), 3)
        self.assertEqual(self.client.get("/api/v1/missions/", {"case": str(self.case.pk)}).data["count"], 1)
        self.assertEqual(self.client.get(f"/api/v1/missions/{mission['id']}/").status_code, 200)
        CaseAction.objects.create(case=self.case, kind="updated", actor=self.agent, next_action="Contrôler", status="open", version=1)
        timeline_response = self.client.get(f"/api/v1/dossiers/{self.case.pk}/chronologie/")
        self.assertEqual(timeline_response.data["count"], 2)
        timeline = timeline_response.data["results"]
        self.assertTrue(any(item["kind"] == "mission.created" and item["resource_id"] == mission["id"] for item in timeline))
        self.assertTrue(any(item["kind"] == "updated" for item in timeline))
        self.assertEqual(ObservationSheet.objects.count(), 0)
        sheet = self.create_sheet(origin="mission", mission=mission["id"], docs=docs[:1])
        self.assertEqual(sheet["mission"], uuid.UUID(mission["id"]))
        self.assertEqual([item["number"] for item in sheet["observations"]], [1, 2])
        self.assertEqual(sheet["observations"][0]["documents"], [uuid.UUID(str(docs[0].pk))])
        self.assertTrue(AuditEvent.objects.filter(action="inspection.mission.created").exists())
        self.assertEqual(Defense.objects.count(), 0)

    def test_origin_rules_versioned_pdf_and_failed_generation(self):
        invalid = self.client.post("/api/v1/feuilles/", self.sheet_payload(origin="system"), format="json")
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(ObservationSheet.objects.count(), 0)
        sheet = self.create_sheet()
        url = f"/api/v1/feuilles/{sheet['id']}/"
        self.assertTrue(self.client.get(url + "apercu/").data["project_only"])
        with patch("inspections.service._render_project", side_effect=OSError("interrupted")):
            with self.assertRaises(OSError):
                self.client.post(url + "preparer/", {"version": 1}, format="json")
        self.assertEqual(SheetProject.objects.count(), 0)
        project = self.client.post(url + "preparer/", {"version": 1}, format="json")
        self.assertEqual(project.status_code, 200, project.content)
        self.assertEqual(self.client.post(url + "preparer/", {"version": 1}, format="json").data["id"], project.data["id"])
        download = self.client.get(f"/api/v1/projets-feuille/{project.data['id']}/telecharger/")
        self.assertEqual(download.status_code, 200)
        self.assertTrue(b"".join(download.streaming_content).startswith(b"%PDF-"))
        download.close()
        updated = self.client.patch(url, {"version": 1, "facts": "Faits corrigés"}, format="json")
        self.assertEqual(updated.status_code, 200, updated.content)
        self.assertEqual(updated.data["version"], 2)
        self.assertEqual(self.client.patch(url, {"version": 1, "facts": "Écrasement"}, format="json").status_code, 409)
        self.assertEqual(self.client.post(url + "preparer/", {"version": 1}, format="json").status_code, 409)
        second = self.client.post(url + "preparer/", {"version": 2}, format="json")
        self.assertEqual(second.status_code, 200)
        self.assertNotEqual(second.data["id"], project.data["id"])
        self.assertEqual(SheetProject.objects.count(), 2)
        older = self.client.get(f"/api/v1/projets-feuille/{project.data['id']}/telecharger/")
        self.assertEqual(older.status_code, 200)
        older.close()

    def test_partial_defense_complement_and_assessment_history(self):
        sheet = self.create_sheet()
        first, second = [item["id"] for item in sheet["observations"]]
        letter1, letter2 = self.document(), self.document()
        url = f"/api/v1/feuilles/{sheet['id']}/"
        payload = {"letter": str(letter1.pk), "received_on": str(timezone.localdate()), "observation_ids": [str(first)]}
        defense1 = self.client.post(url + "defenses/", payload, format="json")
        self.assertEqual(defense1.status_code, 201, defense1.content)
        self.assertEqual(self.client.get(url + "defenses/").data["count"], 1)
        self.assertEqual(self.client.get(f"/api/v1/defenses/{defense1.data['id']}/").status_code, 200)
        self.assertEqual(ObservationSheet.objects.get(pk=sheet["id"]).observations.get(pk=second).defenses.count(), 0)
        assess_url = url + f"observations/{first}/appreciations/"
        result = self.client.post(assess_url, {"version": 0, "defense": defense1.data["id"], "conclusion": "unsatisfactory", "reason": "Incomplet"}, format="json")
        self.assertEqual(result.status_code, 201, result.content)
        self.assertEqual(self.client.post(assess_url, {"version": 0, "defense": defense1.data["id"], "conclusion": "satisfactory", "reason": "Tardif"}, format="json").status_code, 409)
        defense2 = self.client.post(url + "defenses/", {"letter": str(letter2.pk), "received_on": str(timezone.localdate()), "observation_ids": [str(first)], "complement_of": defense1.data["id"]}, format="json")
        self.assertEqual(defense2.status_code, 201, defense2.content)
        self.assertEqual(self.client.post(assess_url, {"version": 1, "defense": defense2.data["id"], "conclusion": "satisfactory", "reason": "Complété"}, format="json").status_code, 201)
        self.assertEqual(self.client.get(assess_url).data["count"], 2)
        self.assertEqual(Defense.objects.count(), 2)
        self.assertEqual(ObservationAssessment.objects.count(), 2)
        self.assertEqual(self.client.patch(url, {"version": 1, "observations": [{"facts": "Effacer"}]}, format="json").status_code, 400)
        self.assertEqual(self.client.get(url + f"observations/{second}/appreciations/").data["count"], 0)

    def test_parent_scope_permissions_revocation_and_audit_rollback(self):
        doc = self.document()
        sheet = self.create_sheet()
        url = f"/api/v1/feuilles/{sheet['id']}/"
        self.client.force_login(self.colleague)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post("/api/v1/missions/", self.mission_payload([doc]), format="json").status_code, 404)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.get("/api/v1/feuilles/", {"case": str(self.case.pk)}).status_code, 404)
        self.client.force_login(self.agent)
        with patch("inspections.service.record", side_effect=OperationalError("audit unavailable")):
            self.assertEqual(self.client.post("/api/v1/missions/", self.mission_payload([doc]), format="json").status_code, 503)
        self.assertEqual(InspectionMission.objects.count(), 0)
        Membership.objects.filter(user=self.agent, unit=self.unit).update(revoked_at=timezone.now())
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_cross_case_documents_and_links_are_rejected(self):
        other_case = Case.objects.create(unit=self.unit, classification=1, assignee=self.agent, created_by=self.manager, next_action="Autre")
        alien_doc = self.document(case=other_case)
        mission = self.client.post("/api/v1/missions/", self.mission_payload([alien_doc]), format="json")
        self.assertEqual(mission.status_code, 400)
        self.assertEqual(InspectionMission.objects.count(), 0)
        sheet = self.create_sheet()
        defense = self.client.post(f"/api/v1/feuilles/{sheet['id']}/defenses/", {"letter": str(alien_doc.pk), "received_on": str(timezone.localdate()), "observation_ids": [str(sheet["observations"][0]["id"])]}, format="json")
        self.assertEqual(defense.status_code, 400)
        self.assertEqual(Defense.objects.count(), 0)
