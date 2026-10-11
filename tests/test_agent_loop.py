import json
import tempfile
import unittest
from pathlib import Path

from agent.orchestrator import run_agent
from agent.tools import ToolLayer


class AgentLoopTests(unittest.TestCase):
    def setUp(self):
        self.temp_root = Path(__file__).resolve().parents[1] / ".tmp"
        self.temp_root.mkdir(exist_ok=True)

    def make_run(self, root: Path, kinds: list[str]) -> Path:
        run_dir = root / "run"
        (run_dir / "clips").mkdir(parents=True)
        (run_dir / "run.json").write_text(json.dumps({
            "runId": "test-run", "status": "observations-only",
            "counts": {"trackObservations": 100},
            "environment": {"opencv": "5.0.0"},
            "quality": {"pitchCalibration": "manual-image-polygon"},
        }))
        events = []
        for index, kind in enumerate(kinds, 1):
            event_id = f"evt-{index:04d}"
            (run_dir / "clips" / f"{event_id}.mp4").write_bytes(b"clip")
            events.append({"id": event_id, "type": kind, "status": "candidate",
                           "zone": {"id": "r1c1", "coordinateSystem": "image_relative_3x3"},
                           "evidence": {"clipPath": f"clips/{event_id}.mp4"}})
        (run_dir / "events.json").write_text(json.dumps(events))
        return run_dir

    def test_draft_plan_gate_requires_list_events(self):
        with tempfile.TemporaryDirectory(dir=self.temp_root) as temp:
            run_dir = self.make_run(Path(temp), ["zone_density"])
            tools = ToolLayer()
            tools.run_perception(run_dir=run_dir)
            clip = tools.get_clip("evt-0001")
            zone = tools.analyze_zone("r1c1")
            with self.assertRaisesRegex(RuntimeError, "requires list_events"):
                tools.draft_plan("evt-0001", clip, zone)
            tools.list_events()
            plan = tools.draft_plan("evt-0001", clip, zone)
            self.assertEqual(plan["status"], "pending_approval")

    def test_vision_changes_next_tool_order_and_requests_coach(self):
        with tempfile.TemporaryDirectory(dir=self.temp_root) as temp:
            root = Path(temp)
            first = self.make_run(root / "density", ["zone_density", "zone_density", "zone_contest"])
            second = self.make_run(root / "contest", ["zone_contest", "zone_contest", "zone_density"])
            for run_dir, expected in ((first, "analyze_zone"), (second, "get_clip")):
                tools = ToolLayer()
                result = run_agent(tools, run_dir=run_dir)
                trace = json.loads((run_dir / "trace.json").read_text())["steps"]
                names = [step["name"] for step in trace if step["kind"] == "tool"]
                self.assertEqual(names[:2], ["run_perception", "list_events"])
                self.assertEqual(names[2], expected)
                self.assertEqual(trace[2]["details"]["nextTool"], expected)
                self.assertEqual(result["approval"]["status"], "pending_approval")
                self.assertEqual(json.loads((run_dir / "plan.json").read_text())["status"],
                                 "pending_approval")

    def test_approval_requires_explicit_coach_decision(self):
        with tempfile.TemporaryDirectory(dir=self.temp_root) as temp:
            run_dir = self.make_run(Path(temp), ["zone_density"])
            tools = ToolLayer()
            run_agent(tools, run_dir=run_dir)
            with self.assertRaises(ValueError):
                tools.request_approval(decision="approved")
            result = tools.request_approval(decision="rejected", coach="Test Coach")
            self.assertEqual(result["status"], "rejected")
            with self.assertRaises(RuntimeError):
                tools.request_approval(decision="approved", coach="Test Coach")


if __name__ == "__main__":
    unittest.main()
