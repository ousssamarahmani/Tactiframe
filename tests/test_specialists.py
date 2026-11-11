import json
import os
import tempfile
import unittest
from pathlib import Path

import config
from agent.specialists import run_specialist_simulation
from agent.tools import ToolLayer


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

    def make_run(self, name: str, kinds: list[str], *, calibration: str = "manual-image-polygon") -> Path:
        run_dir = Path(self.temp_dir.name) / name
        (run_dir / "clips").mkdir(parents=True)
        (run_dir / "artifacts").mkdir()
        for name in ("heatmap", "zone_matrix", "team_shape"):
            (run_dir / "artifacts" / f"{name}.json").write_text(json.dumps({"schemaVersion": 1, "product": "TactiFrame"}))
        (run_dir / "run.json").write_text(json.dumps({
            "runId": name, "status": "observations-only", "counts": {"trackObservations": 100, "uniquePlayerIds": 18},
            "environment": {"opencv": "5.0.0"}, "quality": {"pitchCalibration": calibration},
            "outputs": {"evidenceArtifacts": {"heatmap": "artifacts/heatmap.json", "zoneMatrix": "artifacts/zone_matrix.json", "teamShape": "artifacts/team_shape.json"}},
        }))
        events = []
        for index, kind in enumerate(kinds, 1):
            event_id = f"evt-{index:04d}"
            (run_dir / "clips" / f"{event_id}.mp4").write_bytes(b"clip")
            events.append({"id": event_id, "type": kind, "status": "candidate", "zone": {"id": "r1c1"}, "evidence": {"clipPath": f"clips/{event_id}.mp4"}})
        (run_dir / "events.json").write_text(json.dumps(events))
        return run_dir

    def next_tool(self, run_dir: Path) -> str:
        run_specialist_simulation(ToolLayer(), run_dir=run_dir)
        trace = json.loads((run_dir / "trace.json").read_text())["steps"]
        decision = next(step for step in trace if step["kind"] == "decision")
        return decision["details"]["nextTool"]

    def test_density_evidence_routes_to_zone_analysis(self):
        self.assertEqual(self.next_tool(self.make_run("density", ["zone_density", "zone_density", "zone_contest"])), "analyze_zone")

    def test_contest_evidence_routes_to_clip(self):
        self.assertEqual(self.next_tool(self.make_run("contest", ["zone_contest", "zone_contest", "zone_density"])), "get_clip")

    def test_video_quality_concern_overrides_tactical_order(self):
        self.assertEqual(self.next_tool(self.make_run("uncalibrated", ["zone_density", "zone_density"], calibration="unavailable")), "get_clip")

    def test_no_events_stops_without_a_plan(self):
        run_dir = self.make_run("empty", [])
        result = run_specialist_simulation(ToolLayer(), run_dir=run_dir)
        self.assertEqual(result["status"], "no_evidence")
        self.assertFalse((run_dir / "plan.json").exists())
