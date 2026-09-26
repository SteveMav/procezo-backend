import hashlib
import tempfile
import uuid
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from audit.models import AuditEvent
from decisions.models import Decision, GelecTransfer
from documents.models import Document
from identity.models import Delegation, Membership, Unit
from intelligence.models import Dissemination, DisseminationReturn
from inspections.models import Defense, ObservationAssessment, ObservationSheet
from requests_app.models import RequestIssuance, RequestResponse


class PilotJourneyTests(TestCase):
    def setUp(self):
        private = tempfile.TemporaryDirectory()
        self.addCleanup(private.cleanup)
        override = override_settings(PROCEZO_PRIVATE_FILES_ROOT=private.name)
        override.enable()
        self.addCleanup(override.disable)
        self.private_root = Path(private.name)
        users = get_user_model().objects
        self.agent = users.create_user("pilot-agent")
        self.colleague = users.create_user("pilot-colleague")
        self.manager = users.create_user("pilot-manager")
        self.recipient_b = users.create_user("pilot-b")
        self.recipient_c = users.create_user("pilot-c")
        self.outsider = users.create_user("pilot-outsider", is_superuser=True)
        self.unit = Unit.objects.create(code="PILOT-A", name="Bureau A")
        self.unit_b = Unit.objects.create(code="PILOT-B", name="Bureau B")
        self.unit_c = Unit.objects.create(code="PILOT-C", name="Bureau C")
        self.unit_d = Unit.objects.create(code="PILOT-D", name="Bureau D")
        now = timezone.now()
        for user, unit, role in ((self.agent, self.unit, "investigator"), (self.colleague, self.unit, "investigator"), (self.manager, self.unit, "manager"), (self.recipient_b, self.unit_b, "manager"), (self.recipient_c, self.unit_c, "manager"), (self.outsider, self.unit_d, "manager")):
            Membership.objects.create(user=user, unit=unit, role=role, clearance=1, valid_from=now)
        for action in (Delegation.Action.CASE_CREATE, Delegation.Action.CASE_ASSIGN, Delegation.Action.SOURCE_READ, Delegation.Action.SOURCE_WRITE, Delegation.Action.INTELLIGENCE_DISTRIBUTE, Delegation.Action.REQUEST_VALIDATE, Delegation.Action.REQUEST_SIGN, Delegation.Action.REQUEST_ISSUE, Delegation.Action.DECISION_VALIDATE, Delegation.Action.GELEC_TRANSFER, Delegation.Action.GELEC_CONFIRM):
            Delegation.objects.create(user=self.manager, unit=self.unit, action=action, valid_from=now)
        self.client = APIClient()
        self.client.force_login(self.manager)

    def post(self, url, data, expected=200):
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, expected, (url, response.content))
        return response.data

    def document(self, case, content=b"%PDF-1.4\npreuve fictive"):
        name = uuid.uuid4()
        path = self.private_root / "quarantine" / str(name)
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(content)
        return Document.objects.create(case_id=case, original_name="preuve.pdf", content_type="application/pdf", size=len(content), sha256=hashlib.sha256(content).hexdigest(), state="accepted", storage_name=name, slot=Document.objects.filter(case_id=case).count() + 1, uploaded_by=self.agent)

    def intelligence(self):
        return self.post("/api/v1/renseignements/", {"unit": str(self.unit.pk), "classification": 1, "subject": "Alerte fictive", "summary": "Faits fictifs anonymes", "provenance": "rapport de service", "occurred_on": str(timezone.localdate()), "assignee": self.agent.pk, "source_identity": "Source fictive cachée"}, 201)

    def case(self):
        return self.post("/api/v1/dossiers/", {"unit": str(self.unit.pk), "classification": 1, "assignee": self.agent.pk, "next_action": "Contrôler", "assignment_reason": "Recette fictive"}, 201)

    def test_journey_01_from_intelligence_to_classification_and_statistics(self):
        intel = self.intelligence()
        case = self.case()
        self.post(f"/api/v1/renseignements/{intel['id']}/dossiers/", {"version": 1, "case": case["id"]}, 201)
        self.client.force_login(self.agent)
        request = self.post("/api/v1/demandes/", {"case": case["id"], "target_type": "broker", "target_name": "Tiers fictif", "subject": "Pièces", "mode": "generated", "items": [{"label": "Facture"}]}, 201)
        url = f"/api/v1/demandes/{request['id']}/"
        self.post(url + "preparer/", {"version": 1})
        self.post(url + "soumettre/", {"version": 1})
        self.client.force_login(self.manager)
        self.post(url + "valider/", {"version": 2})
        proof = self.document(case["id"])
        self.post(url + "constater-signature/", {"version": 3, "proof": str(proof.pk), "signed_at": timezone.now().isoformat()})
        self.post(url + "constater-emission/", {"version": 4, "idempotency_key": str(uuid.uuid4()), "dispatch_proof": str(proof.pk), "sent_at": timezone.now().isoformat()})
        self.client.force_login(self.agent)
        letter = self.document(case["id"])
        self.post(url + "reponses/", {"letter": str(letter.pk), "received_on": str(timezone.localdate()), "item_ids": [request["items"][0]["id"]]}, 201)
        assessment = self.post(url + f"elements/{request['items'][0]['id']}/appreciations/", {"version": 0, "receipt": "received", "completeness": "complete", "substance": "satisfactory", "reason": "Contrôle fictif"}, 201)
        decision = self.post("/api/v1/decisions/", {"case": case["id"], "case_version": case["version"], "kind": "classification", "reason": "Réponse satisfaisante", "request_assessment": assessment["id"]}, 201)
        self.client.force_login(self.manager)
        self.post(f"/api/v1/decisions/{decision['id']}/valider/", {"version": decision["version"]})
        params = {"unit": str(self.unit.pk), "start": str(timezone.localdate()), "end": str(timezone.localdate())}
        response = self.client.get("/api/v1/statistiques/", params)
        self.assertEqual(response.status_code, 200, response.content)
        indicators = {item["key"]: item for family in response.data["families"] for item in family["indicators"]}
        for key in ("requests.issued", "requests.responses", "cases.classified"):
            self.assertEqual(indicators[key]["value"], 1)
            self.assertEqual(self.client.get(indicators[key]["detail_url"]).data["count"], 1)
        self.assertEqual(RequestIssuance.objects.count(), 1)
        self.assertEqual(RequestResponse.objects.count(), 1)
        self.assertEqual(Decision.objects.filter(state="validated").count(), 1)
        self.assertNotIn("Source fictive cachée", str(response.data))
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(f"/api/v1/dossiers/{case['id']}/").status_code, 404)
        self.assertTrue(AuditEvent.objects.filter(action="decision.validated").exists())

    def test_journey_03_alert_without_case_to_two_bureaus(self):
        intel = self.intelligence()
        base = f"/api/v1/renseignements/{intel['id']}/diffusions/"
        sent = timezone.now().isoformat()
        first = self.post(base, {"recipient_unit": str(self.unit_b.pk), "channel": "note", "expected_action": "Examiner", "sent_at": sent, "idempotency_key": str(uuid.uuid4())}, 201)
        second = self.post(base, {"recipient_unit": str(self.unit_c.pk), "channel": "message phonique", "expected_action": "Accuser réception", "sent_at": sent, "idempotency_key": str(uuid.uuid4())}, 201)
        self.client.force_login(self.recipient_b)
        self.assertEqual(self.client.get(f"/api/v1/renseignements/{intel['id']}/").status_code, 200)
        self.assertEqual(self.client.get(f"/api/v1/renseignements/{intel['id']}/source/").status_code, 403)
        self.post(f"/api/v1/diffusions/{first['id']}/retours/", {"acknowledged": True, "received_at": sent, "idempotency_key": str(uuid.uuid4())}, 201)
        self.client.force_login(self.recipient_c)
        self.post(f"/api/v1/diffusions/{second['id']}/retours/", {"acknowledged": True, "received_at": sent, "idempotency_key": str(uuid.uuid4())}, 201)
        self.client.force_login(self.manager)
        response = self.client.get("/api/v1/statistiques/", {"unit": str(self.unit.pk), "start": str(timezone.localdate()), "end": str(timezone.localdate())})
        indicators = {item["key"]: item for family in response.data["families"] for item in family["indicators"] if not item.get("provenance")}
        self.assertEqual(indicators["intelligence.received"]["value"], 1)
        self.assertEqual(indicators["intelligence.distributed"]["value"], 1)
        self.assertEqual(indicators["intelligence.with_returns"]["value"], 1)
        self.assertEqual(Dissemination.objects.count(), 2)
        self.assertEqual(DisseminationReturn.objects.count(), 2)
        self.assertEqual(self.client.get(base).data["count"], 2)
        self.assertNotIn("Source fictive cachée", str(response.data))

    def test_journey_02_partial_responses_mission_defense_and_gelec(self):
        case = self.case()
        self.client.force_login(self.agent)
        request = self.post("/api/v1/demandes/", {"case": case["id"], "target_type": "organization", "target_name": "Tiers fictif", "subject": "Trois éléments", "mode": "generated", "items": [{"label": "A"}, {"label": "B"}, {"label": "C"}]}, 201)
        request_url = f"/api/v1/demandes/{request['id']}/"
        first_letter = self.document(case["id"])
        second_letter = self.document(case["id"])
        first = self.post(request_url + "reponses/", {"letter": str(first_letter.pk), "received_on": str(timezone.localdate()), "item_ids": [request["items"][0]["id"]]}, 201)
        self.post(request_url + "reponses/", {"letter": str(second_letter.pk), "received_on": str(timezone.localdate()), "complement_of": first["id"], "item_ids": [request["items"][1]["id"]]}, 201)
        self.assertEqual(self.client.get(request_url + "reponses/").data["count"], 2)
        self.post(request_url + f"elements/{request['items'][2]['id']}/appreciations/", {"version": 0, "receipt": "not_received", "completeness": "unknown", "substance": "pending", "reason": "Non reçu"}, 201)
        self.assertEqual(Decision.objects.count(), 0)
        docs = [self.document(case["id"]) for _ in range(3)]
        mission = self.post("/api/v1/missions/", {"case": case["id"], "context": "Contrôle fictif", "findings": "Trois constats", "occurred_on": str(timezone.localdate()), "participants": [self.agent.pk, self.colleague.pk], "documents": [str(doc.pk) for doc in docs]}, 201)
        sheet = self.post("/api/v1/feuilles/", {"case": case["id"], "mission": mission["id"], "origin": "mission", "recipient_address": "Adresse fictive", "concerned_party": "Tiers fictif", "facts": "Faits fictifs", "observations": [{"facts": "Premier constat", "documents": [str(docs[0].pk)]}, {"facts": "Second constat", "documents": []}]}, 201)
        sheet_url = f"/api/v1/feuilles/{sheet['id']}/"
        project = self.post(sheet_url + "preparer/", {"version": 1})
        download = self.client.get(f"/api/v1/projets-feuille/{project['id']}/telecharger/")
        self.assertEqual(download.status_code, 200)
        download.close()
        observation = sheet["observations"][0]["id"]
        defense = self.post(sheet_url + "defenses/", {"letter": str(docs[1].pk), "received_on": str(timezone.localdate()), "observation_ids": [observation]}, 201)
        complement = self.post(sheet_url + "defenses/", {"letter": str(docs[2].pk), "received_on": str(timezone.localdate()), "observation_ids": [observation], "complement_of": defense["id"]}, 201)
        self.assertEqual(ObservationSheet.objects.get(pk=sheet["id"]).observations.get(pk=sheet["observations"][1]["id"]).defenses.count(), 0)
        assessment = self.post(sheet_url + f"observations/{observation}/appreciations/", {"version": 0, "defense": complement["id"], "conclusion": "unsatisfactory", "reason": "Constat maintenu"}, 201)
        decision = self.post("/api/v1/decisions/", {"case": case["id"], "case_version": case["version"], "kind": "gelec", "reason": "Suite proposée après défense", "observation_assessment": assessment["id"]}, 201)
        self.client.force_login(self.manager)
        self.post(f"/api/v1/decisions/{decision['id']}/valider/", {"version": decision["version"]})
        transfer = self.post("/api/v1/transferts-gelec/", {"decision": decision["id"]}, 201)
        transfer_url = f"/api/v1/transferts-gelec/{transfer['id']}/"
        proof = self.document(case["id"])
        sent = self.post(transfer_url + "transmettre/", {"version": 1, "idempotency_key": str(uuid.uuid4()), "proof": str(proof.pk), "transmitted_at": timezone.now().isoformat()})
        self.assertEqual(sent["state"], "transmitted")
        self.assertIsNone(sent["received_at"])
        confirmed = self.post(transfer_url + "confirmer-reception/", {"version": 2, "idempotency_key": str(uuid.uuid4()), "proof": str(proof.pk), "received_at": timezone.now().isoformat(), "reference": "GELEC-FICTIF"})
        self.assertEqual(confirmed["state"], "confirmed")
        self.assertEqual(Defense.objects.count(), 2)
        self.assertEqual(ObservationAssessment.objects.count(), 1)
        self.assertEqual(GelecTransfer.objects.count(), 1)
        stats = self.client.get("/api/v1/statistiques/", {"unit": str(self.unit.pk), "start": str(timezone.localdate()), "end": str(timezone.localdate())})
        indicators = {item["key"]: item for family in stats.data["families"] for item in family["indicators"]}
        self.assertIsNone(indicators["cases.pv_proven"]["value"])
