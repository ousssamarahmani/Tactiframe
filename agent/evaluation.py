"""Session-level quality and evidence checks for TactiFrame."""

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from run_pipeline import write_json


def _read_json(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else default


def _check(name: str, passed: bool, details: dict) -> dict:
    return {"name": name, "passed": passed, "details": details}


def _trace_tool_order_check(steps: list[dict]) -> dict:
    decisions = []
    for index, step in enumerate(steps):
        if step.get("kind") != "decision" or step.get("name") != "select_next_tool":
            continue
        expected = step.get("details", {}).get("nextTool")
        next_tool = next(
            (candidate.get("name") for candidate in steps[index + 1:]
             if candidate.get("kind") == "tool"),
            None,
        )
        decisions.append({"expected": expected, "observed": next_tool,
                          "matches": (expected == "stop" and next_tool is None)
                          or expected == next_tool})
    return _check(
        "vision_decision_changes_tool_order",
        bool(decisions) and all(item["matches"] for item in decisions),
        {"decisions": decisions},
    )


def _track_continuity_metrics(run_dir: Path, run: dict) -> dict:
    tracks_path = run_dir / run.get("outputs", {}).get("tracks", "tracks.json")
    tracks = _read_json(tracks_path, [])
    if not tracks:
        return {"available": False}
    by_id = {}
    pairs = set()
    duplicates = 0
    for track in tracks:
        track_id, frame = track.get("track_id"), track.get("frame")
        if track_id is None or frame is None:
            continue
        key = (frame, track_id)
        duplicates += key in pairs
        pairs.add(key)
        by_id.setdefault(track_id, []).append(frame)
    lengths = sorted(len(frames) for frames in by_id.values())
    fps = run.get("video", {}).get("fps") or 1
    median_length = lengths[len(lengths) // 2] if lengths else 0
    return {
        "available": True,
        "duplicateFrameTrackPairs": duplicates,
        "meanObservationsPerId": round(sum(lengths) / len(lengths), 2) if lengths else 0,
        "medianObservationsPerId": median_length,
        "shortTracksAtOrBelowOneSecond": sum(length <= fps for length in lengths),
        "shortTrackShare": round(sum(length <= fps for length in lengths) / len(lengths), 3) if lengths else 0,
    }


def _artifact_check(run_dir: Path, run: dict) -> tuple[dict, dict]:
    manifest = run.get("outputs", {}).get("evidenceArtifacts")
    if not manifest:
        return ({"available": False, "reason": "not_generated"},
                _check("evidence_artifacts_valid_when_present", True, {"status": "not_generated"}))
    required = {"heatmap", "zoneMatrix", "teamShape"}
    valid = isinstance(manifest, dict) and required.issubset(manifest)
    available = {}
    for key in required:
        relative_path = manifest.get(key) if isinstance(manifest, dict) else None
        path = (run_dir / relative_path).resolve() if relative_path else None
        payload = _read_json(path, {}) if path and path.is_relative_to(run_dir) else {}
        available[key] = bool(path and path.is_file() and payload.get("schemaVersion") == 1
                              and payload.get("product") == "TactiFrame")
    return ({"available": valid and all(available.values()), "files": available},
            _check("evidence_artifacts_valid_when_present", valid and all(available.values()),
                   {"required": sorted(required), "files": available}))


def evaluate_session(run_dir: Path, *, write: bool = True) -> dict:
    """Measure a completed session without claiming tactical accuracy.

    The report is deliberately structural: it verifies local evidence, trace order,
    and human-approval safety. It does not turn candidate detections into facts.
    """
    run_dir = Path(run_dir).resolve()
    run = _read_json(run_dir / "run.json", {})
    events = _read_json(run_dir / "events.json", [])
    trace = _read_json(run_dir / "trace.json", {})
    plan = _read_json(run_dir / "plan.json", None)
    ball_validation = _read_json(
        run_dir / run.get("outputs", {}).get("validatedBallCandidates", "ball_candidates_validated.json"),
        {},
    )
    artifact_metrics, artifact_check = _artifact_check(run_dir, run)

    event_types = Counter(event.get("type", "unknown") for event in events)
    zones = Counter(event.get("zone", {}).get("id", "unknown") for event in events)
    confidence_scores = [event.get("confidence", {}).get("score") for event in events]
    confidence_scores = [score for score in confidence_scores if isinstance(score, (int, float))]
    evidence = []
    for event in events:
        relative_path = event.get("evidence", {}).get("clipPath")
        path = (run_dir / relative_path).resolve() if relative_path else None
        available = bool(path and path.is_relative_to(run_dir) and path.is_file() and path.stat().st_size > 0)
        evidence.append({"eventId": event.get("id"), "clipPath": relative_path,
                         "available": available})

    steps = trace.get("steps", []) if isinstance(trace, dict) else []
    checks = [
        _check("completed_perception", run.get("status") == "observations-only",
               {"status": run.get("status")}),
        _check("candidate_events_have_local_evidence", all(item["available"] for item in evidence),
               {"events": len(events), "available": sum(item["available"] for item in evidence)}),
        _trace_tool_order_check(steps),
        artifact_check,
    ]
    if plan is None:
        checks.append(_check("plan_is_evidence_backed", True,
                             {"status": "no_plan", "reason": "No plan was drafted"}))
        if not events:
            checks.append(_check("no_events_stops_without_plan", True,
                                 {"candidateEvents": 0, "planPresent": False}))
    else:
        event_id = plan.get("evidence", {}).get("eventId")
        clip_path = plan.get("evidence", {}).get("clipPath")
        matching_event = next((event for event in events if event.get("id") == event_id), None)
        matching_evidence = next((item for item in evidence if item["eventId"] == event_id), None)
        checks.append(_check(
            "plan_is_evidence_backed",
            bool(matching_event and matching_evidence and matching_evidence["available"]
                 and matching_event.get("evidence", {}).get("clipPath") == clip_path),
            {"planStatus": plan.get("status"), "eventId": event_id, "clipPath": clip_path},
        ))
        checks.append(_check(
            "approval_is_explicit",
            plan.get("status") == "pending_approval" or bool(plan.get("decision", {}).get("coach")),
            {"planStatus": plan.get("status"), "coach": plan.get("decision", {}).get("coach")},
        ))

    report = {
        "schemaVersion": 1,
        "product": "TactiFrame",
        "evaluatedAt": datetime.now(timezone.utc).isoformat(),
        "runId": run.get("runId", run_dir.name),
        "scope": "structural session evaluation; candidate events are not tactical ground truth",
        "metrics": {
            "frames": run.get("video", {}).get("frames"),
            "trackObservations": run.get("counts", {}).get("trackObservations"),
            "uniquePlayerIds": run.get("counts", {}).get("uniquePlayerIds"),
            "ballObservations": run.get("counts", {}).get("ballObservations"),
            "validatedBallCandidates": run.get("counts", {}).get("validatedBallCandidates"),
            "ballValidation": run.get("ballValidation", {"available": bool(ball_validation)}),
            "trackContinuity": _track_continuity_metrics(run_dir, run),
            "evidenceArtifacts": artifact_metrics,
            "offPitchRejected": run.get("filterRejections", {}).get("off_pitch_rejected"),
            "candidateEvents": len(events),
            "eventsByType": dict(event_types),
            "eventsByZone": dict(zones),
            "meanEventConfidence": round(sum(confidence_scores) / len(confidence_scores), 3)
            if confidence_scores else None,
            "evidenceAvailable": sum(item["available"] for item in evidence),
            "evidenceExpected": len(evidence),
            "toolOrder": [step.get("name") for step in steps if step.get("kind") == "tool"],
            "planStatus": plan.get("status") if plan else None,
        },
        "checks": checks,
        "passed": all(check["passed"] for check in checks),
    }
    if write:
        write_json(run_dir / "evaluation.json", report)
    return report
