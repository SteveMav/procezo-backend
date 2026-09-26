import json
import os
import subprocess
import sys
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import LiveServerTestCase
from django.utils import timezone

from cases.models import Case
from identity.models import Membership, Unit


class PilotMeasurementTests(LiveServerTestCase):
    def test_network_probe_authenticates_and_measures_visible_case(self):
        username = "measure-agent"
        password = "fiction-only-password"
        user = get_user_model().objects.create_user(username, password=password)
        unit = Unit.objects.create(code="MEASURE", name="Unité fictive")
        Membership.objects.create(user=user, unit=unit, role="manager", clearance=0, valid_from=timezone.now())
        case = Case.objects.create(unit=unit, classification=0, assignee=user, created_by=user, next_action="Mesurer")
        env = dict(os.environ, PROCEZO_PILOT_USERNAME=username, PROCEZO_PILOT_PASSWORD=password)
        script = Path(__file__).resolve().parents[1] / "scripts" / "measure_pilot.py"
        result = subprocess.run([sys.executable, str(script), self.live_server_url, case.reference, str(case.pk), "--samples", "5"], env=env, capture_output=True, text=True, timeout=30, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["samples_per_operation"], 5)
        self.assertEqual(report["case_id"], str(case.pk))
        self.assertGreaterEqual(report["search"]["p95_ms"], 0)
        self.assertGreaterEqual(report["open"]["p95_ms"], 0)
