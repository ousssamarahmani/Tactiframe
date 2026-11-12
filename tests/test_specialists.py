import os
import tempfile
import unittest
from pathlib import Path

import config
from agent.specialists import run_specialist_simulation
from agent.tools import ToolLayer
from tests.session_fixtures import make_session


class SpecialistSimulationTests(unittest.TestCase):
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

    def next_tool(self, run_dir: Path) -> str:
        run_specialist_simulation(ToolLayer(), run_dir=run_dir)
        import json
        trace = json.loads((run_dir / "trace.json").read_text())["steps"]
        decision = next(step for step in trace if step["kind"] == "decision")
        return decision["details"]["nextTool"]

    def test_density_evidence_routes_to_zone_analysis(self):
        self.assertEqual(self.next_tool(make_session(Path(self.temp_dir.name), "density", ["zone_density", "zone_density", "zone_contest"])), "analyze_zone")

    def test_contest_evidence_routes_to_clip(self):
        self.assertEqual(self.next_tool(make_session(Path(self.temp_dir.name), "contest", ["zone_contest", "zone_contest", "zone_density"])), "get_clip")

    def test_video_quality_concern_overrides_tactical_order(self):
        self.assertEqual(self.next_tool(make_session(Path(self.temp_dir.name), "uncalibrated", ["zone_density", "zone_density"], calibration="unavailable")), "get_clip")

    def test_no_events_stops_without_a_plan(self):
        run_dir = make_session(Path(self.temp_dir.name), "empty", [])
        result = run_specialist_simulation(ToolLayer(), run_dir=run_dir)
        self.assertEqual(result["status"], "no_evidence")
        self.assertFalse((run_dir / "plan.json").exists())

    def test_missing_clip_stops_before_any_tactical_tool(self):
        run_dir = make_session(Path(self.temp_dir.name), "missing-clip", ["zone_density"], include_clip=False)
        result = run_specialist_simulation(ToolLayer(), run_dir=run_dir)
        self.assertEqual(result["status"], "evidence_incomplete")
        trace = __import__("json").loads((run_dir / "trace.json").read_text())["steps"]
        self.assertEqual(trace[-1]["details"]["nextTool"], "stop")
        self.assertNotIn("analyze_zone", [step["name"] for step in trace])
