"""Evidence-bound Bedrock proposal adapter for TactiFrame."""

import json
from pathlib import Path
from typing import Any


SYSTEM_PROMPT = (
    "You are TactiFrame's coach-review assistant. Use only the supplied candidate event, "
    "zone analysis, and video frames. Do not claim possession, passes, turnovers, player "
    "identities, or calibrated pitch locations. Write one concise proposal asking a coach what "
    "to review, then list the evidence event ID and supplied limitations. Never approve a plan."
)


def _extract_frames(clip_path: Path) -> list[bytes]:
    import cv2

    source = cv2.VideoCapture(str(clip_path))
    if not source.isOpened():
        raise RuntimeError(f"Could not open evidence clip: {clip_path}")
    try:
        count = int(source.get(cv2.CAP_PROP_FRAME_COUNT))
        if count < 1:
            raise RuntimeError(f"Evidence clip has no frames: {clip_path}")
        frames = []
        for index in sorted({0, count // 2, count - 1}):
            source.set(cv2.CAP_PROP_POS_FRAMES, index)
            ok, frame = source.read()
            if not ok:
                continue
            encoded, image = cv2.imencode(".jpg", frame)
            if encoded:
                frames.append(image.tobytes())
        if not frames:
            raise RuntimeError(f"Could not extract evidence frames: {clip_path}")
        return frames
    finally:
        source.release()


class BedrockCoachProposal:
    def __init__(self, model_id: str, region: str, profile: str = "", client: Any = None):
        self.model_id = model_id
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
        self._client = session.client("bedrock-runtime")
        return self._client

    def propose(self, event: dict, zone_analysis: dict, clip_path: Path,
                frame_bytes: list[bytes] | None = None) -> dict:
        """Request coach-review wording grounded in selected OpenCV evidence."""
        try:
            frames = frame_bytes if frame_bytes is not None else _extract_frames(clip_path)
            evidence = {
                "event": event,
                "zoneAnalysis": zone_analysis,
                "evidenceClip": {"path": clip_path.name, "framesProvided": len(frames)},
            }
            content: list[dict] = [
                {"text": "Create a coach-review proposal from this evidence only:\n" +
                          json.dumps(evidence, separators=(",", ":"))}
            ]
            content.extend({"image": {"format": "jpeg", "source": {"bytes": frame}}} for frame in frames)
            response = self._client_or_create().converse(
                modelId=self.model_id,
                system=[{"text": SYSTEM_PROMPT}],
                messages=[{"role": "user", "content": content}],
                inferenceConfig={"maxTokens": 250, "temperature": 0.2},
            )
            text = "".join(
                block.get("text", "") for block in response["output"]["message"]["content"]
            )
            if not text.strip():
                raise RuntimeError("Bedrock returned no proposal text")
            return {
                "status": "success", "modelId": self.model_id,
                "eventId": event["id"], "frameCount": len(frames),
                "proposal": text.strip(), "usage": response.get("usage", {}),
                "stopReason": response.get("stopReason"),
            }
        except Exception as error:
            return {
                "status": "failed", "modelId": self.model_id,
                "eventId": event.get("id"),
                "error": f"{type(error).__name__}: {error}",
            }
