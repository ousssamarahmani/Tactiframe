"""Best-effort private S3 upload for TactiFrame session artifacts."""

import json
from pathlib import Path
from typing import Any


def s3_uri(bucket: str, key: str) -> str:
    return f"s3://{bucket}/{key}"


def _content_type(path: Path) -> str:
    return "video/mp4" if path.suffix.lower() == ".mp4" else "application/json"


class SessionUploader:
    """Upload evidence without making local analysis dependent on AWS success."""

    def __init__(self, bucket: str, region: str, profile: str = "", client: Any = None):
        self.bucket = bucket
        self.region = region
        self.profile = profile
        self._client = client

    def _client_or_create(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            import boto3
        except ImportError as error:
            raise RuntimeError("boto3 is not installed; install requirements.txt before enabling AWS") from error
        session = boto3.Session(profile_name=self.profile or None, region_name=self.region)
        self._client = session.client("s3")
        return self._client

    def _upload(self, path: Path, key: str) -> dict:
        try:
            self._client_or_create().upload_file(
                str(path), self.bucket, key,
                ExtraArgs={"ContentType": _content_type(path)},
            )
            return {"status": "uploaded", "key": key, "s3Uri": s3_uri(self.bucket, key)}
        except Exception as error:
            return {"status": "failed", "key": key, "s3Uri": None,
                    "error": f"{type(error).__name__}: {error}"}

    def sync_session(self, run_dir: Path) -> dict:
        """Upload clips first, then enriched event, trace, and plan files."""
        run_dir = run_dir.resolve()
        metadata_path = run_dir / "run.json"
        events_path = run_dir / "events.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        events = json.loads(events_path.read_text(encoding="utf-8"))
        run_id = metadata["runId"]
        prefix = f"sessions/{run_id}"
        assets: dict[str, dict] = {}
        failures: list[dict] = []

        try:
            self._client_or_create()
        except Exception as error:
            message = f"{type(error).__name__}: {error}"
            for event in events:
                event["evidence"]["s3Uri"] = None
            events_path.write_text(json.dumps(events, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            result = {
                "bucket": self.bucket, "region": self.region, "prefix": prefix,
                "status": "unavailable", "assets": {},
                "failures": [{"asset": "aws-client", "error": message}],
            }
            metadata.setdefault("aws", {})["s3"] = result
            metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            return result

        for event in events:
            relative = Path(event["evidence"]["clipPath"])
            clip_path = (run_dir / relative).resolve()
            if not clip_path.is_relative_to(run_dir) or not clip_path.is_file():
                outcome = {"status": "failed", "s3Uri": None,
                           "error": "Evidence clip is missing or outside the session"}
            else:
                outcome = self._upload(clip_path, f"{prefix}/{relative.as_posix()}")
            event["evidence"]["s3Uri"] = outcome["s3Uri"]
            assets[f"clip:{event['id']}"] = outcome
            if outcome["status"] == "failed":
                failures.append({"asset": f"clip:{event['id']}", "error": outcome["error"]})

        events_path.write_text(json.dumps(events, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        for name in ("events.json", "trace.json", "plan.json"):
            path = run_dir / name
            if not path.is_file():
                outcome = {"status": "skipped", "s3Uri": None, "reason": "not-created"}
            else:
                outcome = self._upload(path, f"{prefix}/{name}")
            assets[name] = outcome
            if outcome["status"] == "failed":
                failures.append({"asset": name, "error": outcome["error"]})

        result = {
            "bucket": self.bucket, "region": self.region, "prefix": prefix,
            "status": "complete" if not failures else "partial",
            "assets": assets, "failures": failures,
        }
        metadata.setdefault("aws", {})["s3"] = result
        metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return result

    def sync_trace(self, run_dir: Path) -> dict:
        """Refresh the S3 trace after the S3 outcome is recorded locally."""
        metadata = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
        return self._upload(run_dir / "trace.json", f"sessions/{metadata['runId']}/trace.json")
