"""Export fixed local review windows and descriptive observation diagnostics.

These counts are not accuracy scores. A person must label visible players and
ball positions in the review clips before precision, recall, or ID switches can
be measured.
"""

import argparse
import json
from collections import Counter
from pathlib import Path

import cv2


def export_review(run_dir: Path, starts: list[int], seconds: int) -> dict:
    metadata = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    tracks = json.loads((run_dir / "tracks.json").read_text(encoding="utf-8"))
    balls = json.loads((run_dir / "ball_observations.json").read_text(encoding="utf-8"))
    source = run_dir / "tracked.mp4"
    cap = cv2.VideoCapture(str(source))
    if not cap.isOpened():
        raise ValueError(f"Cannot open annotated video: {source}")
    fps = float(cap.get(cv2.CAP_PROP_FPS))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if fps <= 0 or total < 1 or width < 1 or height < 1:
        raise ValueError("Annotated video metadata is invalid")

    output = run_dir / "review"
    output.mkdir(exist_ok=True)
    windows = []
    try:
        for start_second in starts:
            first = round(start_second * fps)
            last = min(total, round((start_second + seconds) * fps))
            if first < 0 or first >= total or last <= first:
                raise ValueError(f"Review window starts outside video: {start_second}s")
            path = output / f"review-{start_second:03d}-{round(last / fps):03d}s.mp4"
            writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
            if not writer.isOpened():
                raise ValueError(f"Cannot create review clip: {path}")
            cap.set(cv2.CAP_PROP_POS_FRAMES, first)
            written = 0
            try:
                for _ in range(first, last):
                    ok, frame = cap.read()
                    if not ok:
                        raise ValueError(f"Video ended early while writing {path}")
                    writer.write(frame)
                    written += 1
            finally:
                writer.release()

            window_tracks = [item for item in tracks if first <= item["frame"] < last]
            window_balls = [item for item in balls if first <= item["frame"] < last]
            per_frame = Counter(item["frame"] for item in window_tracks)
            frame_ids = Counter((item["frame"], item["track_id"]) for item in window_tracks)
            windows.append({
                "startSecond": start_second,
                "endSecond": round(last / fps, 3),
                "frames": written,
                "clip": str(path.relative_to(run_dir)),
                "trackObservations": len(window_tracks),
                "distinctTrackIds": len({item["track_id"] for item in window_tracks}),
                "duplicateFrameIdPairs": sum(count > 1 for count in frame_ids.values()),
                "medianTrackedPlayersPerFrame": sorted(per_frame.get(i, 0) for i in range(first, last))[(last - first) // 2],
                "ballCandidateFrames": len({item["frame"] for item in window_balls}),
            })
    finally:
        cap.release()

    report = {
        "sourceRun": metadata.get("runId"),
        "inputChecksum": metadata.get("video", {}).get("checksum"),
        "use": "local simulation and education only",
        "assessment": "descriptive diagnostics; no ground truth or accuracy claim",
        "windows": windows,
    }
    (output / "diagnostics.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--starts", nargs="+", type=int, default=[0, 110, 220])
    parser.add_argument("--seconds", type=int, default=30)
    args = parser.parse_args()
    if args.seconds < 1:
        parser.error("--seconds must be positive")
    print(json.dumps(export_review(args.run_dir, args.starts, args.seconds), indent=2))
