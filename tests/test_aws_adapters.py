import json
import tempfile
import unittest
from pathlib import Path

from agent.bedrock import BedrockCoachProposal
from aws.storage import SessionUploader


class FakeS3:
    def __init__(self, fail_name: str | None = None):
        self.fail_name = fail_name
        self.calls = []

    def upload_file(self, filename, bucket, key, ExtraArgs):
        self.calls.append((filename, bucket, key, ExtraArgs))
        if self.fail_name and filename.endswith(self.fail_name):
            raise RuntimeError("simulated upload failure")


class FakeBedrock:
    def __init__(self):
        self.request = None

    def converse(self, **kwargs):
        self.request = kwargs
        return {
            "output": {"message": {"content": [{"text": "Coach: inspect the grouped players."}]}},
            "usage": {"inputTokens": 12, "outputTokens": 7},
            "stopReason": "end_turn",
        }


class AwsAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp_root = Path(__file__).resolve().parents[1] / ".tmp"
        self.temp_root.mkdir(exist_ok=True)

    def make_session(self, root: Path) -> Path:
        run_dir = root / "run"
        (run_dir / "clips").mkdir(parents=True)
        (run_dir / "clips" / "evt-0001.mp4").write_bytes(b"clip")
        (run_dir / "run.json").write_text(json.dumps({"runId": "run-123"}))
        (run_dir / "events.json").write_text(json.dumps([{
            "id": "evt-0001", "evidence": {"clipPath": "clips/evt-0001.mp4"},
        }]))
        (run_dir / "trace.json").write_text("{}")
        (run_dir / "plan.json").write_text("{}")
        return run_dir

    def test_s3_sync_writes_clip_uri_and_metadata(self):
        with tempfile.TemporaryDirectory(dir=self.temp_root) as temp:
            run_dir = self.make_session(Path(temp))
            client = FakeS3()
            result = SessionUploader("bucket", "eu-north-1", client=client).sync_session(run_dir)
            event = json.loads((run_dir / "events.json").read_text())[0]
            metadata = json.loads((run_dir / "run.json").read_text())
            self.assertEqual(result["status"], "complete")
            self.assertEqual(event["evidence"]["s3Uri"],
                             "s3://bucket/sessions/run-123/clips/evt-0001.mp4")
            self.assertEqual(metadata["aws"]["s3"]["bucket"], "bucket")
            self.assertEqual(len(client.calls), 4)

    def test_s3_failure_keeps_local_artifacts(self):
        with tempfile.TemporaryDirectory(dir=self.temp_root) as temp:
            run_dir = self.make_session(Path(temp))
            result = SessionUploader("bucket", "eu-north-1", client=FakeS3("evt-0001.mp4")).sync_session(run_dir)
            event = json.loads((run_dir / "events.json").read_text())[0]
            self.assertEqual(result["status"], "partial")
            self.assertIsNone(event["evidence"]["s3Uri"])
            self.assertTrue((run_dir / "clips" / "evt-0001.mp4").is_file())

    def test_bedrock_receives_selected_event_and_frames(self):
        client = FakeBedrock()
        result = BedrockCoachProposal("model-id", "eu-north-1", client=client).propose(
            {"id": "evt-0002", "type": "zone_density", "limitations": ["candidate"]},
            {"zone": {"id": "r1c1"}}, Path("unused.mp4"),
            frame_bytes=[b"frame-a", b"frame-b", b"frame-c"],
        )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["eventId"], "evt-0002")
        self.assertEqual(result["frameCount"], 3)
        content = client.request["messages"][0]["content"]
        self.assertEqual(len([block for block in content if "image" in block]), 3)
        self.assertIn("evt-0002", content[0]["text"])


if __name__ == "__main__":
    unittest.main()
