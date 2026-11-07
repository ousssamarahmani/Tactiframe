"""Conservative, auditable quality checks for raw football-ball candidates."""

from collections import Counter
from math import hypot


def validate_ball_candidates(
    candidates: list[dict], *, min_confidence: float = 0.20,
    static_radius_px: float = 6.0, static_min_observations: int = 5,
    max_static_frame_gap: int = 2, jump_distance_px: float = 95.0,
) -> tuple[list[dict], dict]:
    """Return quality-filtered candidates without interpolation or inference.

    A candidate must clear the configured confidence floor and must not be part
    of a sustained, fixed-image-position run (commonly a pitch marking). Large
    jumps are retained but counted as diagnostics: they can be a genuine pass,
    a camera change, or a false positive and therefore need human review.
    """
    ordered = sorted(candidates, key=lambda item: item["frame"])
    rejected = Counter()
    confidence_ok = []
    for item in ordered:
        if item.get("confidence", 0.0) < min_confidence:
            rejected["low_confidence"] += 1
        else:
            confidence_ok.append(dict(item))

    static_frames = set()
    start = 0
    while start < len(confidence_ok):
        anchor = confidence_ok[start]
        end = start + 1
        while end < len(confidence_ok):
            candidate = confidence_ok[end]
            if candidate["frame"] - confidence_ok[end - 1]["frame"] > max_static_frame_gap:
                break
            if hypot(candidate["x"] - anchor["x"], candidate["y"] - anchor["y"]) > static_radius_px:
                break
            end += 1
        if end - start >= static_min_observations:
            static_frames.update(item["frame"] for item in confidence_ok[start:end])
        start = end if end > start else start + 1

    validated = []
    previous = None
    jumps = 0
    for item in confidence_ok:
        if item["frame"] in static_frames:
            rejected["static_position"] += 1
            continue
        record = dict(item, validation="confidence-and-static-filter-v1")
        if previous is not None:
            frame_gap = record["frame"] - previous["frame"]
            if frame_gap > 0 and hypot(record["x"] - previous["x"], record["y"] - previous["y"]) / frame_gap > jump_distance_px:
                record["trajectoryWarning"] = "large_jump"
                jumps += 1
        validated.append(record)
        previous = record

    summary = {
        "method": "confidence-and-static-filter-v1",
        "parameters": {
            "minConfidence": min_confidence,
            "staticRadiusPx": static_radius_px,
            "staticMinObservations": static_min_observations,
            "maxStaticFrameGap": max_static_frame_gap,
            "jumpDistancePxPerFrame": jump_distance_px,
        },
        "rawCandidates": len(ordered),
        "validatedCandidates": len(validated),
        "rejected": dict(rejected),
        "trajectoryWarnings": {"large_jump": jumps},
        "status": "candidate-unverified",
    }
    return validated, summary
