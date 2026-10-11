"""Run the TactiFrame offline observation baseline on one football clip."""

import argparse
import hashlib
import json
import platform
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def write_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as output:
        json.dump(value, output, indent=2, sort_keys=True)
        output.write("\n")
    temporary.replace(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True, help="Football clip (respect its permitted use)")
    parser.add_argument("--model", type=Path, required=True, help="Football YOLO weights with ball=0, goalkeeper=1, player=2, referee=3")
    parser.add_argument("--output-dir", type=Path, default=None, help="New run directory; default: data/sessions/<run-id>")
    parser.add_argument("--ball-conf", type=float, default=0.15)
    parser.add_argument("--player-conf", type=float, default=0.30)
    parser.add_argument("--imgsz", type=int, default=960)
    parser.add_argument("--iou", type=float, default=0.5)
    parser.add_argument("--min-player-height", type=int, default=10)
    parser.add_argument("--no-pitch-mask", action="store_true", help="Disable the visible-green-turf filter")
    parser.add_argument("--field-polygons", type=Path, default=None,
                        help="Manual image-space polygon keyframes for this exact clip")
    parser.add_argument("--device", default=None, help="Inference device, for example cpu or cuda:0")
    parser.add_argument("--sample-frames", type=int, default=25)
    parser.add_argument("--calibration-frame", type=int, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.video.is_file():
        raise FileNotFoundError(f"Video does not exist: {args.video}")
    if not args.model.is_file():
        raise FileNotFoundError(f"Model does not exist: {args.model}")
    if not (0 < args.ball_conf <= 1 and 0 < args.player_conf <= 1 and 0 < args.iou <= 1):
        raise ValueError("--ball-conf, --player-conf, and --iou must be in (0, 1]")
    if args.imgsz < 32 or args.min_player_height < 1:
        raise ValueError("--imgsz must be >= 32 and --min-player-height must be positive")
    if args.sample_frames < 1:
        raise ValueError("--sample-frames must be positive")

    import cv2
    import torch
    import ultralytics
    from cv.team_classifier import TeamClassifier
    from cv.tracker import PlayerTracker

    cap = cv2.VideoCapture(str(args.video))
    if not cap.isOpened():
        raise ValueError(f"Video cannot be opened: {args.video}")
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = float(cap.get(cv2.CAP_PROP_FPS))
    frame_size = (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                  int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    cap.release()
    if frame_count < 1 or fps <= 0:
        raise ValueError("Video has no readable frames or valid FPS")

    started = datetime.now(timezone.utc)
    run_id = started.strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    output_dir = args.output_dir or Path("data/sessions") / run_id
    output_dir.mkdir(parents=True, exist_ok=False)
    started_clock = time.perf_counter()
    video_hash = sha256_file(args.video)
    model_hash = sha256_file(args.model)
    from cv.field_polygon import FieldPolygonTimeline
    field_polygon = (FieldPolygonTimeline.from_file(args.field_polygons,
                     video_checksum=video_hash, frame_size=frame_size)
                     if args.field_polygons else None)

    metadata = {
        "schemaVersion": 1,
        "product": "TactiFrame",
        "runId": run_id,
        "status": "running",
        "startedAt": started.isoformat(),
        "video": {"path": str(args.video.resolve()), "checksum": video_hash, "frames": frame_count, "fps": fps},
        "model": {"path": str(args.model.resolve()), "name": args.model.name, "checksum": model_hash},
        "parameters": {"confidence": min(args.ball_conf, args.player_conf), "ballConfidence": args.ball_conf,
                       "playerConfidence": args.player_conf, "imgsz": args.imgsz, "iou": args.iou,
                       "minPlayerHeight": args.min_player_height, "pitchMask": not args.no_pitch_mask,
                       "tracker": "supervision.ByteTrack", "device": args.device or "auto",
                       "sampleFrames": args.sample_frames},
        "environment": {"python": platform.python_version(), "opencv": cv2.__version__,
                        "ultralytics": ultralytics.__version__, "torch": torch.__version__},
        "outputs": {},
        "quality": {"pitchCalibration": "unavailable", "events": "unavailable", "evidenceEligibility": "candidate-only"},
    }
    if args.field_polygons:
        metadata["parameters"]["fieldPolygons"] = str(args.field_polygons.resolve())
        metadata["parameters"]["fieldPolygonChecksum"] = sha256_file(args.field_polygons)
        metadata["quality"]["pitchCalibration"] = "manual-image-polygon"
    write_json(output_dir / "run.json", metadata)

    try:
        tracker = PlayerTracker(model_path=str(args.model), conf=min(args.ball_conf, args.player_conf),
                                device=args.device, player_conf=args.player_conf,
                                ball_conf=args.ball_conf, imgsz=args.imgsz, iou=args.iou,
                                min_player_height=args.min_player_height,
                                use_pitch_mask=not args.no_pitch_mask,
                                field_polygon=field_polygon)
        checkpoint_args = (tracker.model.ckpt or {}).get("train_args", {})
        architecture = tracker.model.model.yaml.get("yaml_file") or checkpoint_args.get("model")
        metadata["model"]["architecture"] = Path(architecture).name if architecture else "unknown"
        metadata["model"]["classes"] = {str(key): value for key, value in tracker.model.names.items()}
        write_json(output_dir / "run.json", metadata)
        tracks, ball_observations = tracker.track_video(str(args.video), str(output_dir / "tracked.mp4"))
        if not (output_dir / "tracked.mp4").is_file() or (output_dir / "tracked.mp4").stat().st_size == 0:
            raise RuntimeError("Tracker did not produce an annotated video")
        write_json(output_dir / "tracks.json", tracks)
        write_json(output_dir / "ball_observations.json", ball_observations)

        classifier = TeamClassifier()
        cap = cv2.VideoCapture(str(args.video))
        if not cap.isOpened():
            raise RuntimeError("Video could not be reopened for team classification")
        try:
            calibration_frame = args.calibration_frame
            if calibration_frame is None:
                calibration_frame = frame_count // 2
            if not 0 <= calibration_frame < frame_count:
                raise ValueError("--calibration-frame is outside the video")
            cap.set(cv2.CAP_PROP_POS_FRAMES, calibration_frame)
            success, frame = cap.read()
            bboxes = [track["bbox"] for track in tracks if track["frame"] == calibration_frame and track["class_name"] == "player"]
            calibrated = bool(success and classifier.calibrate(frame, bboxes))

            sampled_teams: dict[int, list[str]] = {}
            sampled_tracks: dict[int, list[dict]] = defaultdict(list)
            for track in tracks:
                if track["frame"] % args.sample_frames or track["class_name"] != "player":
                    continue
                sampled_tracks[track["frame"]].append(track)
            for frame_number, frame_tracks in sorted(sampled_tracks.items()):
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
                success, frame = cap.read()
                if success:
                    for track in frame_tracks:
                        sampled_teams.setdefault(track["track_id"], []).append(classifier.classify(frame, track["bbox"]))
        finally:
            cap.release()

        final_teams = {track_id: Counter(votes).most_common(1)[0][0] for track_id, votes in sampled_teams.items() if votes}
        tracks_with_teams = [dict(track, team=final_teams.get(track["track_id"], "unknown")) for track in tracks]
        write_json(output_dir / "tracks_with_teams.json", tracks_with_teams)

        metadata["status"] = "observations-only"
        metadata["finishedAt"] = datetime.now(timezone.utc).isoformat()
        metadata["durationSeconds"] = round(time.perf_counter() - started_clock, 3)
        metadata["outputs"] = {
            "tracks": "tracks.json",
            "tracksWithTeams": "tracks_with_teams.json",
            "ballObservations": "ball_observations.json",
            "annotatedVideo": "tracked.mp4",
        }
        metadata["quality"]["teamCalibration"] = "available" if calibrated else "unavailable"
        metadata["quality"]["pitchCalibration"] = (
            "manual-image-polygon" if field_polygon is not None else
            "visible-green-mask" if not args.no_pitch_mask else "unavailable")
        metadata["filterRejections"] = dict(tracker.filter_counts)
        metadata["counts"] = {
            "trackObservations": len(tracks),
            "uniquePlayerIds": len({track["track_id"] for track in tracks}),
            "ballObservations": len(ball_observations),
            "teamAssignments": dict(Counter(final_teams.values())),
        }
        write_json(output_dir / "run.json", metadata)
        print(f"TactiFrame run: {output_dir}")
        print(json.dumps(metadata["counts"], indent=2))
        return 0
    except Exception as error:
        metadata["status"] = "failed"
        metadata["finishedAt"] = datetime.now(timezone.utc).isoformat()
        metadata["error"] = f"{type(error).__name__}: {error}"
        write_json(output_dir / "run.json", metadata)
        raise


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(2) from error
