import json
import os
import tempfile
import unittest
from pathlib import Path

import config
from agent.chat import answer_question
from agent.tools import ToolLayer
from tests.session_fixtures import make_session


class ChatScenarioTests(unittest.TestCase):
    def setUp(self):
        self.previous_aws_enabled = os.environ.get("AWS_ENABLED")
        self.previous_config_aws_enabled = config.AWS_ENABLED
        os.environ["AWS_ENABLED"] = "false"
        config.AWS_ENABLED = False
        root = Path(__file__).resolve().parents[1] / ".tmp"
        root.mkdir(exist_ok=True)
        self.temp_dir = tempfile.TemporaryDirectory(dir=root)

    def tearDown(self):
        self.temp_dir.cleanup()
        if self.previous_aws_enabled is None:
            os.environ.pop("AWS_ENABLED", None)
        else:
            os.environ["AWS_ENABLED"] = self.previous_aws_enabled
        config.AWS_ENABLED = self.previous_config_aws_enabled

    def test_density_and_contest_sessions_return_only_linked_evidence(self):
        for name, kinds in (("density", ["zone_density", "zone_density", "zone_contest"]),
                            ("contest", ["zone_contest", "zone_contest", "zone_density"])):
            with self.subTest(name=name):
                run_dir = make_session(Path(self.temp_dir.name), name, kinds)
                tools = ToolLayer()
                tools.run_perception(run_dir=run_dir)
                result = answer_question(tools, "Show candidate evidence in r1c1")
                self.assertEqual(result["status"], "evidence_backed_candidate")
                self.assertEqual(result["evidence"]["events"], ["evt-0001"])
                self.assertEqual(result["evidence"]["clips"][0]["eventId"], "evt-0001")
                self.assertIn("zoneMatrix", result["evidence"]["artifacts"])

    def test_missing_clip_returns_evidence_incomplete_without_a_claim(self):
        run_dir = make_session(Path(self.temp_dir.name), "missing-clip", ["zone_density"], include_clip=False)
        tools = ToolLayer()
        tools.run_perception(run_dir=run_dir)
        result = answer_question(tools, "Show candidate evidence in r1c1")
        self.assertEqual(result["status"], "evidence_incomplete")
        self.assertEqual(result["evidence"]["clips"], [])
        trace = json.loads((run_dir / "trace.json").read_text())["steps"]
        self.assertEqual(trace[-1]["details"]["nextTool"], "stop")

    def test_no_event_session_stops_without_a_plan_or_claim(self):
        run_dir = make_session(Path(self.temp_dir.name), "no-events", [])
        tools = ToolLayer()
        tools.run_perception(run_dir=run_dir)
        result = answer_question(tools, "Where are we exposed?")
        self.assertEqual(result["status"], "no_evidence")
        self.assertFalse((run_dir / "plan.json").exists())
