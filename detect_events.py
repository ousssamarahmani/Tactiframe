"""Build candidate events, image-relative zones, and evidence clips from a run."""

import argparse
import json
from pathlib import Path

import cv2

from cv.event_detector import detect_events
from run_pipeline import write_json


def export_clip(source: cv2.VideoCapture, destination: Path, start: int,
                end: int, fps: float, width: int, height: int) -> int:
    writer = cv2.VideoWriter(str(destination), cv2.VideoWriter_fourcc(*"mp4v"),
                             fps, (width, height))
    if not writer.isOpened():
        raise RuntimeError(f"Could not create clip: {destination}")
    source.set(cv2.CAP_PROP_POS_FRAMES, start)
    written = 0
    try:
        for _ in range(start, end + 1):
            ok, frame = source.read()
            if not ok:
                break
            writer.write(frame)
            written += 1
    finally:
        writer.release()
    if written != end - start + 1:
        destination.unlink(missing_ok=True)
        raise RuntimeError(f"Clip ended early: {destination} ({written} frames)")
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    run_dir = args.run_dir
    metadata = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    tracks = json.loads((run_dir / "tracks_with_teams.json").read_text(encoding="utf-8"))
    video = Path(metadata["video"]["path"])
    source = cv2.VideoCapture(str(video))
    if not source.isOpened():
        raise RuntimeError(f"Could not open source video: {video}")
    try:
        fps = source.get(cv2.CAP_PROP_FPS)
        width = int(source.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(source.get(cv2.CAP_PROP_FRAME_HEIGHT))
        frame_count = int(source.get(cv2.CAP_PROP_FRAME_COUNT))
        if fps <= 0 or width <= 0 or height <= 0 or frame_count <= 0:
            raise RuntimeError("Source video has invalid dimensions, FPS, or frame count")
        events = detect_events(tracks, fps, width, height)
        clip_dir = run_dir / "clips"
        clip_dir.mkdir(exist_ok=True)
        for event in events:
            # Include two seconds of context on each side when available.
            start = max(0, event["startFrame"] - round(2 * fps))
            end = min(frame_count - 1, event["endFrame"] + round(2 * fps))
            clip_path = run_dir / event["evidence"]["clipPath"]
            event["evidence"].update({
                "startFrame": start,
                "endFrame": end,
                "startSeconds": round(start / fps, 3),
                "endSeconds": round(end / fps, 3),
                "eventStartSeconds": event["startSeconds"],
                "eventEndSeconds": event["endSeconds"],
                "frames": export_clip(source, clip_path, start, end, fps, width, height),
            })
        write_json(run_dir / "events.json", events)
        metadata["outputs"]["events"] = "events.json"
        metadata["outputs"]["clips"] = "clips/"
        metadata["quality"]["events"] = "candidate-unverified"
        metadata["quality"]["zoneCoordinates"] = "image_relative_3x3"
        metadata["counts"]["candidateEvents"] = len(events)
        write_json(run_dir / "run.json", metadata)
        print(f"TactiFrame candidate events: {len(events)}; clips: {clip_dir}")
    finally:
        source.release()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
