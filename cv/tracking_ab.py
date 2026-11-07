"""Compare two measured TactiFrame tracking sessions without choosing a winner automatically."""

import json
from pathlib import Path

from run_pipeline import write_json


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _mean_new_ids(run_dir: Path) -> float | None:
    path = run_dir / "track_diagnostics.json"
    if not path.is_file():
        return None
    windows = _load(path).get("windows", [])
    return round(sum(window.get("newTrackIds", 0) for window in windows) / len(windows), 2) if windows else None


def compare_tracking_runs(baseline_dir: Path, candidate_dir: Path, *, write: bool = True) -> dict:
    baseline_dir, candidate_dir = Path(baseline_dir).resolve(), Path(candidate_dir).resolve()
    baseline, candidate = (_load(path / "evaluation.json") for path in (baseline_dir, candidate_dir))
    keys = ("uniquePlayerIds", "trackObservations", "validatedBallCandidates", "candidateEvents")
    comparison = {}
    for key in keys:
        before, after = baseline["metrics"].get(key), candidate["metrics"].get(key)
        comparison[key] = {"baseline": before, "candidate": after,
                           "delta": after - before if isinstance(before, (int, float)) and isinstance(after, (int, float)) else None}
    for key in ("meanObservationsPerId", "medianObservationsPerId", "shortTrackShare"):
        before = baseline["metrics"].get("trackContinuity", {}).get(key)
        after = candidate["metrics"].get("trackContinuity", {}).get(key)
        comparison[key] = {"baseline": before, "candidate": after,
                           "delta": round(after - before, 3) if isinstance(before, (int, float)) and isinstance(after, (int, float)) else None}
    comparison["meanNewTrackIdsPerWindow"] = {
        "baseline": _mean_new_ids(baseline_dir), "candidate": _mean_new_ids(candidate_dir),
    }
    if all(isinstance(value, (int, float)) for value in comparison["meanNewTrackIdsPerWindow"].values()):
        comparison["meanNewTrackIdsPerWindow"]["delta"] = round(
            comparison["meanNewTrackIdsPerWindow"]["candidate"] - comparison["meanNewTrackIdsPerWindow"]["baseline"], 3)

    report = {
        "schemaVersion": 1,
        "product": "TactiFrame",
        "assessment": "descriptive A/B comparison; human review is required before selecting tracker settings",
        "baseline": {"runId": baseline.get("runId"), "path": str(baseline_dir)},
        "candidate": {"runId": candidate.get("runId"), "path": str(candidate_dir)},
        "metrics": comparison,
        "guardrails": [
            "Do not treat fewer IDs as proof of fewer ID switches.",
            "Reject a candidate with duplicate frame/track IDs or unavailable evidence clips.",
            "Review the same labeled player passages before accepting a setting.",
        ],
    }
    if write:
        write_json(candidate_dir / "tracking_ab_comparison.json", report)
    return report
