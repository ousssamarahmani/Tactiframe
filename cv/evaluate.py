"""
TactiFrame CV — Legacy baseline summary (not a validated accuracy evaluator)
Evaluates detection quality, tracking continuity, ball interpolation,
team classification purity, and homography calibration for a pipeline run.
This legacy script uses a sample manifest and marks several gates PASSED without
ground-truth annotations. Its output must not be used as evidence of detection,
tracking, calibration, or ball accuracy. Use video_review.py to prepare review
clips, then label ground truth before reporting accuracy metrics.

Usage:
    python cv/evaluate.py --run-dir data/sessions/<id> \
                          --manifest docs/sample_manifest.json \
                          --output-dir docs/baseline
"""

import sys
import os
import json
import math
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np

# Ensure cv/ is importable
import sys
from pathlib import Path
_CV_DIR = Path(__file__).resolve().parent
if str(_CV_DIR) not in sys.path:
    sys.path.insert(0, str(_CV_DIR))

from ball_interpolation import BallInterpolator


def evaluate_baseline(run_dir: Path, manifest_path: Path, output_dir: Path):
    print("=== TactiFrame CV Baseline Evaluator ===")
    print(f"Loading run output from: {run_dir}")
    print(f"Loading manifest from: {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # Load run outputs
    with open(run_dir / "tracks.json", "r", encoding="utf-8") as f:
        tracks = json.load(f)

    with open(run_dir / "ball_observations.json", "r", encoding="utf-8") as f:
        ball_obs = json.load(f)

    with open(run_dir / "tracks_with_teams.json", "r", encoding="utf-8") as f:
        tracks_with_teams = json.load(f)

    with open(run_dir / "run.json", "r", encoding="utf-8") as f:
        run_meta = json.load(f)

    total_video_frames = manifest["clips"][0]["endFrame"]
    fps = manifest["clips"][0]["fps"]

    # 1. Detection Quality Metrics
    player_confs = [d["confidence"] for d in tracks if "confidence" in d]
    ball_confs = [d["confidence"] for d in ball_obs if "confidence" in d]

    detection_stats = {
        "player": {
            "totalObservations": len(tracks),
            "meanConfidence": round(float(np.mean(player_confs)), 4) if player_confs else 0.0,
            "medianConfidence": round(float(np.median(player_confs)), 4) if player_confs else 0.0,
            "minConfidence": round(float(np.min(player_confs)), 4) if player_confs else 0.0,
            "maxConfidence": round(float(np.max(player_confs)), 4) if player_confs else 0.0,
        },
        "ball": {
            "totalObservations": len(ball_obs),
            "frameCoveragePercent": round(float(len(ball_obs) / total_video_frames * 100), 2),
            "meanConfidence": round(float(np.mean(ball_confs)), 4) if ball_confs else 0.0,
            "medianConfidence": round(float(np.median(ball_confs)), 4) if ball_confs else 0.0,
            "minConfidence": round(float(np.min(ball_confs)), 4) if ball_confs else 0.0,
            "maxConfidence": round(float(np.max(ball_confs)), 4) if ball_confs else 0.0,
            "missingFrames": total_video_frames - len(ball_obs)
        }
    }

    # 2. Tracking diagnostics (not identity accuracy)
    track_lengths = Counter(d["track_id"] for d in tracks)
    lens = list(track_lengths.values())

    tracking_stats = {
        "totalUniqueTracks": len(lens),
        "meanTrackDurationFrames": round(float(np.mean(lens)), 1) if lens else 0.0,
        "meanTrackDurationSeconds": round(float(np.mean(lens) / fps), 2) if lens else 0.0,
        "medianTrackDurationFrames": round(float(np.median(lens)), 1) if lens else 0.0,
        "maxTrackDurationFrames": int(np.max(lens)) if lens else 0,
        "maxTrackDurationSeconds": round(float(np.max(lens) / fps), 2) if lens else 0.0,
        "minTrackDurationFrames": int(np.min(lens)) if lens else 0,
        "longTracksOver500Frames": sum(1 for l in lens if l >= 500),
        "shortTracksUnder50Frames": sum(1 for l in lens if l < 50)
    }

    # 3. Hypothetical ball interpolation; input candidates may be false positives
    interpolator = BallInterpolator(max_gap_frames=50, max_speed_px_per_frame=80.0)
    interpolated_ball = interpolator.interpolate(ball_obs)
    interpolated_frames_count = sum(1 for d in interpolated_ball if d.get("interpolated", False))
    total_ball_frames = len(interpolated_ball)
    ball_coverage_after_interp = round(float(total_ball_frames / total_video_frames * 100), 2)

    ball_interp_stats = {
        "rawDetections": len(ball_obs),
        "rawCoveragePercent": detection_stats["ball"]["frameCoveragePercent"],
        "interpolatedFramesAdded": interpolated_frames_count,
        "totalFramesWithBall": total_ball_frames,
        "postInterpolationCoveragePercent": ball_coverage_after_interp,
        "maxAllowedGapFrames": interpolator.max_gap_frames,
        "maxAllowedSpeedPxPerFrame": interpolator.max_speed_px_per_frame,
        "status": "UNVERIFIED"
    }

    # 4. Team Assignment Stability
    team_counts = Counter(d.get("team", "unknown") for d in tracks_with_teams)
    by_track = defaultdict(list)
    for d in tracks_with_teams:
        by_track[d["track_id"]].append(d.get("team", "unknown"))

    pure_tracks_count = 0
    for tid, labels in by_track.items():
        counts = Counter(labels)
        if len(counts) == 1:
            pure_tracks_count += 1

    team_stats = {
        "distribution": {
            k: {
                "count": v,
                "percentage": round(float(v / len(tracks_with_teams) * 100), 2)
            }
            for k, v in team_counts.items()
        },
        "trackPurity": {
            "totalTracks": len(by_track),
            "pureConsistentTracks": pure_tracks_count,
            "trackPurityPercent": round(float(pure_tracks_count / len(by_track) * 100), 2) if by_track else 100.0
        }
    }

    # 5. Pitch Calibration & Homography Quality (Gate 4)
    calib_file = run_dir / "calibration.json"
    if not calib_file.exists():
        calib_file = manifest_path.parent / "calibration.json"

    calibration_stats = {
        "status": "unavailable",
        "reprojectionErrorMeters": None,
        "reprojectionErrorPixels": None,
        "landmarksUsed": 0,
        "reason": "No calibration file found"
    }

    if calib_file.exists():
        with open(calib_file, "r", encoding="utf-8") as f:
            calib_data = json.load(f)
            calibration_stats = {
                "status": calib_data.get("status", "unavailable"),
                "reprojectionErrorMeters": calib_data.get("reprojection_error_meters"),
                "reprojectionErrorPixels": calib_data.get("reprojection_error_pixels"),
                "landmarksUsed": calib_data.get("num_points_used", 0),
                "inliersCount": calib_data.get("inliers_count", 0),
                "reason": calib_data.get("reason")
            }

    # 6. Hardware Runtime & Throughput
    duration_sec = run_meta.get("durationSeconds", 0.0)
    effective_fps = round(float(total_video_frames / duration_sec), 2) if duration_sec > 0 else 0.0

    runtime_stats = {
        "totalDurationSeconds": duration_sec,
        "totalVideoFrames": total_video_frames,
        "throughputFps": effective_fps,
        "python": run_meta.get("python", "3.11.9"),
        "operatingSystem": run_meta.get("operatingSystem", "Windows"),
        "hardwareProfile": manifest.get("environment", {}).get("hardware", "Intel CPU")
    }

    report = {
        "session_id": manifest.get("sessionId", "unknown"),
        "schemaVersion": 1,
        "clipId": manifest["clips"][0]["clipId"],
        "modelId": manifest["models"][0]["modelId"],
        "modelWeights": manifest["models"][0]["weights"],
        "modelChecksum": manifest["models"][0]["weightsChecksum"],
        "videoChecksum": manifest["clips"][0]["sourceChecksum"],
        "detection": detection_stats,
        "tracking": tracking_stats,
        "ballInterpolation": ball_interp_stats,
        "teamClassification": team_stats,
        "calibration": calibration_stats,
        "runtime": runtime_stats,
        "detectionStatus": "UNVERIFIED",
        "calibrationStatus": "PASSED" if calibration_stats["status"] == "valid" else calibration_stats["status"].upper(),
        "ballInterpolationStatus": "UNVERIFIED"
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    report_json_path = output_dir / "baseline_report.json"
    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # Render Markdown Report
    report_md_path = output_dir / "BASELINE_REPORT.md"
    md_content = f"""# TactiFrame CV Baseline Report

**Session**: `{report['session_id']}`  
**Clip**: `{report['clipId']}` (`{total_video_frames}` frames @ {fps} FPS)  
**Model**: `{report['modelId']}` (`{report['modelWeights']}`)  
**Model Checksum**: `{report['modelChecksum']}`  
**Video Checksum**: `{report['videoChecksum']}`  
**Status**: Detection UNVERIFIED · Calibration: {calibration_stats['status'].upper()} · Ball Interpolation UNVERIFIED

---

## 1. Detection Performance

| Target Class | Observations | Coverage | Mean Conf | Median Conf | Min / Max Conf |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Players & Keepers** | `{detection_stats['player']['totalObservations']:,}` | Full clip | `{detection_stats['player']['meanConfidence'] * 100:.1f}%` | `{detection_stats['player']['medianConfidence'] * 100:.1f}%` | `{detection_stats['player']['minConfidence'] * 100:.1f}%` / `{detection_stats['player']['maxConfidence'] * 100:.1f}%` |
| **Ball (Raw)** | `{detection_stats['ball']['totalObservations']:,}` | `{detection_stats['ball']['frameCoveragePercent']}%` | `{detection_stats['ball']['meanConfidence'] * 100:.1f}%` | `{detection_stats['ball']['medianConfidence'] * 100:.1f}%` | `{detection_stats['ball']['minConfidence'] * 100:.1f}%` / `{detection_stats['ball']['maxConfidence'] * 100:.1f}%` |

---

## 2. Tracking Continuity (ByteTrack)

* **Unique Player Tracks**: `{tracking_stats['totalUniqueTracks']}` active track IDs
* **Mean Track Duration**: `{tracking_stats['meanTrackDurationFrames']} frames` (`{tracking_stats['meanTrackDurationSeconds']}s`)
* **Median Track Duration**: `{tracking_stats['medianTrackDurationFrames']} frames`
* **Longest Continuous Track**: `{tracking_stats['maxTrackDurationFrames']} frames` (`{tracking_stats['maxTrackDurationSeconds']}s` ~ {tracking_stats['maxTrackDurationSeconds']/60:.1f} mins)
* **Persistent Tracks (≥ 500 frames / 20s)**: `{tracking_stats['longTracksOver500Frames']}` tracks ({tracking_stats['longTracksOver500Frames'] / tracking_stats['totalUniqueTracks'] * 100:.1f}%)

---

## 3. Ball Interpolation

| Metric | Raw Detections | After Interpolation | Delta |
| :--- | :--- | :--- | :--- |
| **Ball Frames** | `{ball_interp_stats['rawDetections']:,}` | `{ball_interp_stats['totalFramesWithBall']:,}` | `+{ball_interp_stats['interpolatedFramesAdded']:,} frames` |
| **Coverage** | `{ball_interp_stats['rawCoveragePercent']}%` | `{ball_interp_stats['postInterpolationCoveragePercent']}%` | `+{ball_interp_stats['postInterpolationCoveragePercent'] - ball_interp_stats['rawCoveragePercent']:.2f}%` |

* **Max Gap Interpolated**: `{ball_interp_stats['maxAllowedGapFrames']} frames` (2.0s @ 25fps)
* **Max Speed Ceiling**: `{ball_interp_stats['maxAllowedSpeedPxPerFrame']} px/frame`
* Interpolated points tagged `interpolated: true` with confidence ≤ 0.3; real detections unchanged.

---

## 4. Pitch Homography Calibration

* **Status**: `{calibration_stats['status'].upper()}`
* **Reprojection Error (RMSE)**: **`{calibration_stats['reprojectionErrorMeters']} meters`** ({calibration_stats['reprojectionErrorPixels']} px)
* **Valid threshold**: `< 1.8m` · **Degraded threshold**: `< 3.5m`
* **Inliers used**: `{calibration_stats['inliersCount']} / {calibration_stats['landmarksUsed']} landmarks`

---

## 5. Team Classification

* **Team Distribution**:
  * `team_a`: `{team_stats['distribution'].get('team_a', {}).get('count', 0):,}` ({team_stats['distribution'].get('team_a', {}).get('percentage', 0)}%)
  * `team_b`: `{team_stats['distribution'].get('team_b', {}).get('count', 0):,}` ({team_stats['distribution'].get('team_b', {}).get('percentage', 0)}%)
  * `referee`: `{team_stats['distribution'].get('referee', {}).get('count', 0):,}` ({team_stats['distribution'].get('referee', {}).get('percentage', 0)}%)
* **Within-ID label consistency**: `{team_stats['trackPurity']['trackPurityPercent']}%` ({team_stats['trackPurity']['pureConsistentTracks']} / {team_stats['trackPurity']['totalTracks']} IDs). This is not verified team identity accuracy.

---

## 6. Runtime

* **Frames processed**: `{runtime_stats['totalVideoFrames']:,}`
* **Total runtime**: `{runtime_stats['totalDurationSeconds']}s` ({runtime_stats['totalDurationSeconds']/60:.1f} mins)
* **Throughput**: `{runtime_stats['throughputFps']} FPS`

---

## 7. Summary

- [ ] Detection accuracy: requires labeled video frames
- [ ] Identity continuity: requires reviewed player identities; this script only counts IDs
- [ ] Ball interpolation accuracy: requires validated ball detections and scene-cut checks
- [ ] Homography calibration: {calibration_stats['status'].upper()} ({calibration_stats['reprojectionErrorMeters']}m RMSE)
- [ ] Team classification accuracy: requires labeled team identities
"""

    with open(report_md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"Report generated successfully:")
    print(f"  JSON: {report_json_path}")
    print(f"  Markdown: {report_md_path}")
    return report

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="TactiFrame CV Baseline Evaluator")
    parser.add_argument("--run-dir", required=True, help="Path to session output dir (tracks.json, run.json, etc.)")
    parser.add_argument("--manifest", required=True, help="Path to manifest.json")
    parser.add_argument("--output-dir", default="docs/baseline", help="Where to write baseline_report.json + BASELINE_REPORT.md")
    args = parser.parse_args()
    evaluate_baseline(Path(args.run_dir), Path(args.manifest), Path(args.output_dir))
