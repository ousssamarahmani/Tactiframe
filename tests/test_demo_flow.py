import json
import tempfile
import unittest
from pathlib import Path

import config
from agent.orchestrator import run_agent
from agent.tools import ToolLayer
from api.main import ApprovalRequest, create_app


class DemoFlowTests(unittest.TestCase):
    def setUp(self):
        self.previous_aws_enabled = config.AWS_ENABLED
        config.AWS_ENABLED = False
        self.temp_root = Path(__file__).resolve().parents[1] / ".tmp"
        self.temp_root.mkdir(exist_ok=True)
        self.temp_dir = tempfile.TemporaryDirectory(dir=self.temp_root)
        self.root = Path(self.temp_dir.name)
        self.run_dir = self.root / "demo-session"
        (self.run_dir / "clips").mkdir(parents=True)
        (self.run_dir / "run.json").write_text(json.dumps({
            "runId": "demo-run", "status": "observations-only",
            "counts": {"trackObservations": 42},
            "environment": {"opencv": "5.0.0"},
            "quality": {"pitchCalibration": "manual-image-polygon"},
        }))
        (self.run_dir / "clips" / "evt-0001.mp4").write_bytes(b"clip")
        (self.run_dir / "events.json").write_text(json.dumps([{
            "id": "evt-0001", "type": "zone_density", "status": "candidate",
            "zone": {"id": "r1c1", "coordinateSystem": "image_relative_3x3"},
            "evidence": {"clipPath": "clips/evt-0001.mp4"},
        }]))
        self.app = create_app(self.root)

    def tearDown(self):
        config.AWS_ENABLED = self.previous_aws_enabled
        self.temp_dir.cleanup()

    def endpoint(self, path: str):
        return next(route.endpoint for route in self.app.routes if getattr(route, "path", None) == path)

    def test_agent_to_api_to_named_coach_decision(self):
        result = run_agent(ToolLayer(), run_dir=self.run_dir)
        self.assertEqual(result["approval"]["status"], "pending_approval")

        plan = self.endpoint("/sessions/{session_id}/plan")("demo-session")
        self.assertEqual(plan["status"], "pending_approval")
        self.assertEqual(plan["evidence"]["eventId"], "evt-0001")

        trace = self.endpoint("/sessions/{session_id}/trace")("demo-session")
        self.assertIn("list_events", [step["name"] for step in trace["steps"]])

        decision = self.endpoint("/sessions/{session_id}/approval")(
            "demo-session", ApprovalRequest(decision="approved", coach="Coach Rivera"),
        )
        self.assertEqual(decision["approval"]["status"], "approved")
        self.assertEqual(decision["plan"]["decision"]["coach"], "Coach Rivera")


if __name__ == "__main__":
    unittest.main()
