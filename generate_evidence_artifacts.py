"""Generate deterministic candidate heatmap, zone-matrix, and team-shape session artifacts."""

import argparse
import json
from pathlib import Path

import cv2

from cv.evidence_artifacts import build_evidence_artifacts
from run_pipeline import write_json


def _frame_size(run_dir: Path, metadata: dict) -> tuple[int, int]:
    source = Path(metadata.get("video", {}).get("path", ""))
    if not source.is_file():
        source = run_dir / metadata.get("outputs", {}).get("annotatedVideo", "tracked.mp4")
    capture = cv2.VideoCapture(str(source))
    try:
        width, height = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)), int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    finally:
        capture.release()
    if width < 1 or height < 1:
        raise ValueError("Could not determine a valid video frame size for artifacts")
    return width, height


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--heatmap-rows", type=int, default=12)
    parser.add_argument("--heatmap-cols", type=int, default=20)
    parser.add_argument("--shape-interval-seconds", type=int, default=5)
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    run_path = run_dir / "run.json"
    metadata = json.loads(run_path.read_text(encoding="utf-8"))
    tracks_path = run_dir / metadata.get("outputs", {}).get("tracksWithTeams", "tracks_with_teams.json")
    tracks = json.loads(tracks_path.read_text(encoding="utf-8"))
    width, height = _frame_size(run_dir, metadata)
    artifacts = build_evidence_artifacts(
        tracks, width=width, height=height, fps=float(metadata["video"]["fps"]),
        heatmap_rows=args.heatmap_rows, heatmap_cols=args.heatmap_cols,
        shape_interval_seconds=args.shape_interval_seconds,
    )
    artifact_dir = run_dir / "artifacts"
    artifact_dir.mkdir(exist_ok=True)
    paths = {"heatmap": "artifacts/heatmap.json", "zoneMatrix": "artifacts/zone_matrix.json",
             "teamShape": "artifacts/team_shape_snapshots.json"}
    for key, relative_path in paths.items():
        write_json(run_dir / relative_path, artifacts[key])
    metadata.setdefault("outputs", {})["evidenceArtifacts"] = paths
    metadata.setdefault("quality", {})["evidenceArtifacts"] = "candidate-unverified"
    write_json(run_path, metadata)
    print(json.dumps({"runId": metadata.get("runId"), "artifacts": paths}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
