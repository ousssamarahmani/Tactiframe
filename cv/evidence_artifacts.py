"""Deterministic candidate evidence artifacts derived from tracked positions."""

from collections import defaultdict


def _grid(points: list[dict], width: int, height: int, rows: int, cols: int) -> dict:
    counts = [[0 for _ in range(cols)] for _ in range(rows)]
    for point in points:
        column = min(cols - 1, max(0, int(float(point["x"]) / width * cols)))
        row = min(rows - 1, max(0, int(float(point["y"]) / height * rows)))
        counts[row][column] += 1
    total = sum(sum(row) for row in counts)
    normalized = [[round(value / total, 6) if total else 0.0 for value in row] for row in counts]
    return {"counts": counts, "normalized": normalized, "observations": total}


def _groups(tracks: list[dict]) -> dict[str, list[dict]]:
    groups = defaultdict(list)
    for track in tracks:
        if track.get("class_name", "player") not in {"player", "goalkeeper"}:
            continue
        if "x" not in track or "y" not in track:
            continue
        groups["all"].append(track)
        groups[track.get("team", "unknown")].append(track)
    return dict(groups)


def build_evidence_artifacts(
    tracks: list[dict], *, width: int, height: int, fps: float,
    heatmap_rows: int = 12, heatmap_cols: int = 20, shape_interval_seconds: int = 5,
) -> dict:
    """Build occupancy and shape artifacts without asserting football facts."""
    if width <= 0 or height <= 0 or fps <= 0:
        raise ValueError("width, height, and fps must be positive")
    if heatmap_rows < 1 or heatmap_cols < 1 or shape_interval_seconds < 1:
        raise ValueError("artifact grid sizes and sample interval must be positive")
    groups = _groups(tracks)
    source = {
        "trackObservations": sum(len(points) for name, points in groups.items() if name == "all"),
        "frameSize": {"width": width, "height": height},
        "fps": fps,
        "limitations": [
            "Candidate positions from unverified tracks and team labels",
            "Image-relative coordinates, not calibrated pitch coordinates",
            "Occupancy does not establish possession, pressure, or formation",
        ],
    }
    heatmap = {
        "schemaVersion": 1,
        "product": "TactiFrame",
        "kind": "candidate_occupancy_heatmap",
        "coordinateSystem": f"image_relative_{heatmap_cols}x{heatmap_rows}",
        "source": source,
        "groups": {name: _grid(points, width, height, heatmap_rows, heatmap_cols)
                   for name, points in groups.items()},
    }
    matrix = {
        "schemaVersion": 1,
        "product": "TactiFrame",
        "kind": "candidate_zone_occupancy_matrix",
        "coordinateSystem": "image_relative_3x3",
        "source": source,
        "groups": {name: _grid(points, width, height, 3, 3) for name, points in groups.items()},
    }

    frames = defaultdict(lambda: defaultdict(list))
    for track in tracks:
        if track.get("class_name", "player") in {"player", "goalkeeper"} and "frame" in track:
            frames[track["frame"]][track.get("team", "unknown")].append(track)
    interval_frames = max(1, round(fps * shape_interval_seconds))
    snapshots = []
    for frame in sorted(frames):
        if frame % interval_frames:
            continue
        groups_at_frame = {}
        for team, points in frames[frame].items():
            if not points:
                continue
            xs = [float(point["x"]) / width for point in points]
            ys = [float(point["y"]) / height for point in points]
            groups_at_frame[team] = {
                "observations": len(points),
                "centroid": {"x": round(sum(xs) / len(xs), 6), "y": round(sum(ys) / len(ys), 6)},
                "extent": {"minX": round(min(xs), 6), "maxX": round(max(xs), 6),
                           "minY": round(min(ys), 6), "maxY": round(max(ys), 6)},
            }
        snapshots.append({"frame": frame, "seconds": round(frame / fps, 3), "groups": groups_at_frame})
    shape = {
        "schemaVersion": 1,
        "product": "TactiFrame",
        "kind": "candidate_team_shape_snapshots",
        "coordinateSystem": "normalized_image_coordinates",
        "source": source,
        "sampleIntervalSeconds": shape_interval_seconds,
        "snapshots": snapshots,
    }
    return {"heatmap": heatmap, "zoneMatrix": matrix, "teamShape": shape}
