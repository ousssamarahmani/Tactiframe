"""Local deterministic specialist-agent simulation for TactiFrame Agentic Vision.

The specialists do not claim tactical truth. They inspect bounded session evidence
and give the lead agent a next-tool recommendation that is recorded in trace.json.
"""

import json
from collections import Counter
from pathlib import Path

from agent.tools import ToolLayer


def _artifacts_available(run_dir: Path, run: dict) -> bool:
    manifest = run.get("outputs", {}).get("evidenceArtifacts")
    if not isinstance(manifest, dict):
        return False
    for name in ("heatmap", "zoneMatrix", "teamShape"):
        relative_path = manifest.get(name)
        if not isinstance(relative_path, str):
            return False
        path = (run_dir / relative_path).resolve()
        if not path.is_relative_to(run_dir.resolve()) or not path.is_file():
            return False
    return True


def video_analyst(run_dir: Path) -> dict:
    """Assess whether the source session is structurally usable for spatial review."""
    run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    calibration = run.get("quality", {}).get("pitchCalibration", "unavailable")
    artifacts = _artifacts_available(run_dir, run)
    usable = run.get("status") == "observations-only" and calibration != "unavailable"
    return {
        "role": "video_analyst",
        "status": "candidate_usable" if usable else "requires_clip_review",
        "pitchCalibration": calibration,
        "artifactsAvailable": artifacts,
        "recommendation": "continue_spatial_review" if usable else "get_clip",
        "limitations": ["Camera-space calibration and evidence remain candidate-only"],
    }


def vision_agent(run_dir: Path) -> dict:
    """Assess observation sufficiency without interpreting football tactics."""
    run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    counts = run.get("counts", {})
    ball_validation = run.get("ballValidation", {})
    observations = counts.get("trackObservations", 0)
    return {
        "role": "vision_agent",
        "status": "candidate_observations_available" if observations else "insufficient_observations",
        "trackObservations": observations,
        "uniquePlayerIds": counts.get("uniquePlayerIds"),
        "validatedBallCandidates": counts.get("validatedBallCandidates"),
        "ballStatus": ball_validation.get("status", "not_validated"),
        "recommendation": "continue_evidence_review" if observations else "get_clip",
        "limitations": ["Track identity and ball candidates are not verified"],
    }


def tactical_analyst(events: list[dict]) -> dict:
    """Choose an investigation order from candidate event mix, not a tactical conclusion."""
    counts = Counter(event.get("type", "unknown") for event in events)
    density, contest = counts["zone_density"], counts["zone_contest"]
    by_zone = Counter(event.get("zone", {}).get("id", "unknown") for event in events)
    selected_zone = by_zone.most_common(1)[0][0] if by_zone else "r1c1"
    next_tool = "analyze_zone" if density >= contest else "get_clip"
    return {
        "role": "tactical_analyst",
        "status": "candidate_patterns_available" if events else "no_candidate_patterns",
        "eventsByType": dict(counts),
        "selectedZone": selected_zone,
        "recommendation": next_tool if events else "stop",
        "limitations": ["Patterns are candidate observations, not verified tactical actions"],
    }


def run_specialist_simulation(tools: ToolLayer, *, run_dir: Path,
                              prior_trace: list[dict] | None = None) -> dict:
    """Run three evidence specialists and let their outputs change tool order."""
    summary = tools.run_perception(run_dir=run_dir)
    if prior_trace:
        tools.trace = [*prior_trace, *tools.trace]
    events = tools.list_events()
    if not events:
        tools.note_external("video_analyst", video_analyst(tools._require_run()))
        tools.note_external("vision_agent", vision_agent(tools._require_run()))
        tools.note_external("tactical_analyst", tactical_analyst(events))
        tools.note_decision("Specialists found no candidate evidence", "stop",
                            "No event supports further tactical investigation")
        return {"status": "no_evidence", "run": summary}

    video = video_analyst(tools._require_run())
    vision = vision_agent(tools._require_run())
    tactical = tactical_analyst(events)
    for result in (video, vision, tactical):
        tools.note_external(result["role"], result)

    if video["recommendation"] == "get_clip":
        next_tool, reason = "get_clip", "Video Analyst requires visual evidence review before spatial interpretation"
    elif vision["recommendation"] == "get_clip":
        next_tool, reason = "get_clip", "Vision Agent reports insufficient observations"
    else:
        next_tool, reason = tactical["recommendation"], "Tactical Analyst selected the order from candidate event mix"
    selected = next((event for event in events if event.get("zone", {}).get("id") == tactical["selectedZone"]), events[0])
    clip_path = selected.get("evidence", {}).get("clipPath")
    candidate_clip = (tools._require_run() / str(clip_path)).resolve()
    if not isinstance(clip_path, str) or not candidate_clip.is_relative_to(tools._require_run().resolve()) or not candidate_clip.is_file() or candidate_clip.stat().st_size == 0:
        tools.note_decision("Selected candidate lacks an evidence clip", "stop",
                            "Specialists cannot continue without the linked candidate clip")
        return {
            "status": "evidence_incomplete", "run": summary,
            "specialists": {"video": video, "vision": vision, "tactical": tactical},
            "selectedEvent": selected["id"],
        }
    tools.note_decision("Specialist evidence synthesis", next_tool, reason)
    if next_tool == "get_clip":
        first = tools.get_clip(selected["id"])
        second = tools.analyze_zone(selected["zone"]["id"])
    else:
        first = tools.analyze_zone(selected["zone"]["id"])
        second = tools.get_clip(selected["id"])
    return {
        "status": "specialist_evidence_reviewed", "run": summary,
        "specialists": {"video": video, "vision": vision, "tactical": tactical},
        "selectedEvent": selected["id"], "firstEvidence": first, "secondEvidence": second,
    }
