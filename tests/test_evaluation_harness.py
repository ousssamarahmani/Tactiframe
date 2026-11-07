import json
import os
import tempfile
import unittest
from pathlib import Path

import config
from agent.evaluation import evaluate_session
from agent.orchestrator import run_agent
from agent.tools import ToolLayer


class EvaluationHarnessTests(unittest.TestCase):
    def setUp(self):
        self.previous_aws_enabled = os.environ.get("AWS_ENABLED")
        self.previous_config_aws_enabled = config.AWS_ENABLED
        os.environ["AWS_ENABLED"] = "false"
        config.AWS_ENABLED = False
        self.temp_root = Path(__file__).resolve().parents[1] / ".tmp"
        self.temp_root.mkdir(exist_ok=True)
        self.temp_dir = tempfile.TemporaryDirectory(dir=self.temp_root)

    def tearDown(self):
        self.temp_dir.cleanup()
        if self.previous_aws_enabled is None:
            os.environ.pop("AWS_ENABLED", None)
        else:
            os.environ["AWS_ENABLED"] = self.previous_aws_enabled
        config.AWS_ENABLED = self.previous_config_aws_enabled

    def make_run(self, name: str, kinds: list[str], *, include_clips: bool = True) -> Path:
        run_dir = Path(self.temp_dir.name) / name
        (run_dir / "clips").mkdir(parents=True)
        (run_dir / "run.json").write_text(json.dumps({
            "runId": name, "status": "observations-only",
            "video": {"frames": 150},
            "counts": {"trackObservations": 400, "uniquePlayerIds": 22, "ballObservations": 16},
            "filterRejections": {"off_pitch_rejected": 12},
            "environment": {"opencv": "5.0.0"},
            "quality": {"pitchCalibration": "manual-image-polygon"},
        }))
        events = []
        for index, kind in enumerate(kinds, 1):
            event_id = f"evt-{index:04d}"
            if include_clips:
                (run_dir / "clips" / f"{event_id}.mp4").write_bytes(b"clip")
            events.append({
                "id": event_id, "type": kind, "status": "candidate",
                "zone": {"id": "r1c1", "coordinateSystem": "image_relative_3x3"},
                "confidence": {"score": 0.8},
                "evidence": {"clipPath": f"clips/{event_id}.mp4"},
            })
        (run_dir / "events.json").write_text(json.dumps(events))
        return run_dir

    def run_and_evaluate(self, run_dir: Path) -> dict:
        run_agent(ToolLayer(), run_dir=run_dir)
        report = evaluate_session(run_dir)
        self.assertEqual(report, json.loads((run_dir / "evaluation.json").read_text()))
        return report

    def test_density_first_records_zone_analysis_first(self):
        report = self.run_and_evaluate(self.make_run(
            "density", ["zone_density", "zone_density", "zone_contest"]
        ))
        self.assertTrue(report["passed"])
        self.assertEqual(report["metrics"]["toolOrder"][2], "analyze_zone")

    def test_contest_first_records_clip_first(self):
        report = self.run_and_evaluate(self.make_run(
            "contest", ["zone_contest", "zone_contest", "zone_density"]
        ))
        self.assertTrue(report["passed"])
        self.assertEqual(report["metrics"]["toolOrder"][2], "get_clip")

    def test_no_events_stops_without_a_plan(self):
        run_dir = self.make_run("no-events", [])
        report = self.run_and_evaluate(run_dir)
        self.assertTrue(report["passed"])
        self.assertFalse((run_dir / "plan.json").exists())
        self.assertIsNone(report["metrics"]["planStatus"])

    def test_missing_clip_stops_without_an_unsupported_plan(self):
        run_dir = self.make_run("missing-clip", ["zone_contest"], include_clips=False)
        result = run_agent(ToolLayer(), run_dir=run_dir)
        report = evaluate_session(run_dir)
        self.assertEqual(result["status"], "evidence_unavailable")
        self.assertFalse((run_dir / "plan.json").exists())
        self.assertFalse(report["passed"])
        self.assertFalse(next(check for check in report["checks"]
                              if check["name"] == "candidate_events_have_local_evidence")["passed"])


if __name__ == "__main__":
    unittest.main()
