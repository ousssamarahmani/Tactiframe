"""Deterministic synthetic TactiFrame sessions shared by agent tests.

These fixtures contain no match footage.  They model only the session contract so
agent routes can be tested without cloud calls, a detector, or a model prompt.
"""

import json
from pathlib import Path


def make_session(root: Path, name: str, event_types: list[str], *,
                 calibration: str = "manual-image-polygon",
                 include_clip: bool = True) -> Path:
    """Create one complete, candidate-only session with predictable evidence."""
    run_dir = root / name
    (run_dir / "clips").mkdir(parents=True)
    (run_dir / "artifacts").mkdir()
    artifacts = run_dir / "artifacts"
    (artifacts / "heatmap.json").write_text(json.dumps({
        "schemaVersion": 1, "product": "TactiFrame", "kind": "candidate_heatmap",
    }), encoding="utf-8")
    (artifacts / "zone_matrix.json").write_text(json.dumps({
        "schemaVersion": 1, "product": "TactiFrame",
        "kind": "candidate_zone_occupancy_matrix",
        "groups": {"all": {"counts": [[0, 0, 0], [0, 12, 0], [0, 0, 0]]}},
    }), encoding="utf-8")
    (artifacts / "team_shape.json").write_text(json.dumps({
        "schemaVersion": 1, "product": "TactiFrame", "kind": "candidate_team_shape",
    }), encoding="utf-8")
    (run_dir / "run.json").write_text(json.dumps({
        "runId": name,
        "status": "observations-only",
        "counts": {"trackObservations": 100, "uniquePlayerIds": 18},
        "environment": {"opencv": "5.0.0"},
        "quality": {"pitchCalibration": calibration},
        "outputs": {"evidenceArtifacts": {
            "heatmap": "artifacts/heatmap.json",
            "zoneMatrix": "artifacts/zone_matrix.json",
            "teamShape": "artifacts/team_shape.json",
        }},
    }), encoding="utf-8")
    events = []
    for index, event_type in enumerate(event_types, 1):
        event_id = f"evt-{index:04d}"
        if include_clip:
            (run_dir / "clips" / f"{event_id}.mp4").write_bytes(b"candidate clip")
        events.append({
            "id": event_id,
            "type": event_type,
            "status": "candidate",
            "zone": {"id": "r1c1"},
            "evidence": {"clipPath": f"clips/{event_id}.mp4"},
        })
    (run_dir / "events.json").write_text(json.dumps(events), encoding="utf-8")
    return run_dir
