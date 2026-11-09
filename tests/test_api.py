import json
import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException
from pydantic import ValidationError

from api.main import ApprovalRequest, ChatRequest, create_app


class ApiTests(unittest.TestCase):
    def setUp(self):
        temp_root = Path(__file__).resolve().parents[1] / ".tmp"
        temp_root.mkdir(exist_ok=True)
        self.temp_dir = tempfile.TemporaryDirectory(dir=temp_root)
        self.root = Path(self.temp_dir.name)
        self.run_dir = self.root / "demo-session"
        self.run_dir.mkdir()
        (self.run_dir / "run.json").write_text(json.dumps({
            "runId": "run-123", "status": "observations-only",
            "counts": {"trackObservations": 4},
            "environment": {"opencv": "5.0.0"},
            "quality": {"pitchCalibration": "manual-image-polygon"},
        }))
        (self.run_dir / "events.json").write_text(json.dumps([
            {"id": "evt-0001", "status": "candidate", "type": "zone_density",
             "zone": {"id": "r1c1"}, "evidence": {"clipPath": "clips/evt-0001.mp4"}},
        ]))
        (self.run_dir / "trace.json").write_text(json.dumps({
            "runId": "run-123", "steps": [{"name": "draft_plan"}],
        }))
        (self.run_dir / "plan.json").write_text(json.dumps({
            "id": "plan-123", "status": "pending_approval",
        }))
        (self.run_dir / "tracked.mp4").write_bytes(b"video")
        (self.run_dir / "clips").mkdir()
        (self.run_dir / "clips" / "evt-0001.mp4").write_bytes(b"clip")
        artifact_dir = self.run_dir / "artifacts"
        artifact_dir.mkdir()
        for name in ("heatmap", "zone_matrix", "team_shape"):
            (artifact_dir / f"{name}.json").write_text(json.dumps({
                "schemaVersion": 1, "product": "TactiFrame", "kind": name,
            }))
        (artifact_dir / "zone_matrix.json").write_text(json.dumps({
            "schemaVersion": 1, "product": "TactiFrame", "kind": "candidate_zone_occupancy_matrix",
            "groups": {"all": {"counts": [[0, 0, 0], [0, 4, 0], [0, 0, 0]]}},
        }))
        run = json.loads((self.run_dir / "run.json").read_text())
        run["outputs"] = {"annotatedVideo": "tracked.mp4", "evidenceArtifacts": {
            "heatmap": "artifacts/heatmap.json", "zoneMatrix": "artifacts/zone_matrix.json",
            "teamShape": "artifacts/team_shape.json",
        }}
        (self.run_dir / "run.json").write_text(json.dumps(run))
        self.app = create_app(self.root)

    def tearDown(self):
        self.temp_dir.cleanup()

    def endpoint(self, path: str):
        return next(route.endpoint for route in self.app.routes if getattr(route, "path", None) == path)

    def test_session_artifacts_and_run_id_lookup(self):
        self.assertEqual(self.endpoint("/health")()["status"], "ok")
        session = self.endpoint("/sessions/{session_id}")("run-123")
        self.assertEqual(session["sessionId"], "demo-session")
        self.assertEqual(self.endpoint("/sessions/{session_id}/events")("demo-session")["events"][0]["id"], "evt-0001")
        self.assertEqual(self.endpoint("/sessions/{session_id}/trace")("demo-session")["runId"], "run-123")
        self.assertEqual(self.endpoint("/sessions/{session_id}/plan")("demo-session")["status"], "pending_approval")
        artifacts = self.endpoint("/sessions/{session_id}/artifacts")("demo-session")
        self.assertEqual(artifacts["artifacts"]["heatmap"]["product"], "TactiFrame")
        self.assertEqual(self.endpoint("/sessions/{session_id}/video")("demo-session").media_type, "video/mp4")
        self.assertEqual(self.endpoint("/sessions/{session_id}/clips/{event_id}")(
            "demo-session", "evt-0001").media_type, "video/mp4")
        self.assertEqual(self.endpoint("/review/{session_id}")("demo-session").media_type, "text/html")

    def test_chat_is_evidence_bound_and_never_drafts_a_plan(self):
        result = self.endpoint("/sessions/{session_id}/chat")(
            "demo-session", ChatRequest(question="Show candidate evidence in r1c1"),
        )
        self.assertEqual(result["status"], "evidence_backed_candidate")
        self.assertEqual(result["evidence"]["events"], ["evt-0001"])
        self.assertEqual(result["evidence"]["clips"][0]["url"], "/sessions/demo-session/clips/evt-0001")
        self.assertIn("candidate", result["answer"].lower())
        self.assertEqual(json.loads((self.run_dir / "plan.json").read_text())["status"], "pending_approval")
        trace = json.loads((self.run_dir / "trace.json").read_text())["steps"]
        self.assertIn("analyze_zone", [step["name"] for step in trace])

    def test_approval_requires_validated_explicit_decision(self):
        with self.assertRaises(ValidationError):
            ApprovalRequest(decision="approved")

        approval = self.endpoint("/sessions/{session_id}/approval")(
            "demo-session", ApprovalRequest(decision="approved", coach="Coach Rivera"),
        )
        self.assertEqual(approval["approval"]["status"], "approved")
        self.assertEqual(approval["plan"]["decision"]["coach"], "Coach Rivera")

        with self.assertRaises(HTTPException) as repeated:
            self.endpoint("/sessions/{session_id}/approval")(
                "demo-session", ApprovalRequest(decision="rejected", coach="Coach Rivera"),
            )
        self.assertEqual(repeated.exception.status_code, 409)

    def test_unknown_or_unsafe_session_is_not_read(self):
        with self.assertRaises(HTTPException) as unknown:
            self.endpoint("/sessions/{session_id}")("unknown")
        self.assertEqual(unknown.exception.status_code, 404)
        with self.assertRaises(HTTPException) as unsafe:
            self.endpoint("/sessions/{session_id}/events")("..")
        self.assertEqual(unsafe.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
