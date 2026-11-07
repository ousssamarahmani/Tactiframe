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
