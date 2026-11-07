"""Write track_diagnostics.json for an existing TactiFrame session."""

import argparse
import json
from pathlib import Path

from cv.track_diagnostics import summarize_track_windows
from run_pipeline import write_json


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--window-seconds", type=int, default=30)
    args = parser.parse_args()
    if args.window_seconds < 1:
        parser.error("--window-seconds must be positive")
    run_dir = args.run_dir.resolve()
    run_path = run_dir / "run.json"
    run = json.loads(run_path.read_text(encoding="utf-8"))
    tracks_path = run_dir / run.get("outputs", {}).get("tracks", "tracks.json")
    tracks = json.loads(tracks_path.read_text(encoding="utf-8"))
    video = run.get("video", {})
    report = summarize_track_windows(
        tracks, total_frames=int(video["frames"]), fps=float(video["fps"]),
        window_seconds=args.window_seconds,
    )
    output_name = "track_diagnostics.json"
    write_json(run_dir / output_name, report)
    run.setdefault("outputs", {})["trackDiagnostics"] = output_name
    write_json(run_path, run)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
