"""Deterministic evidence-bound chat service for one TactiFrame session."""

import json
import re
from pathlib import Path

from agent.tools import ToolLayer


def _read_artifacts(run_dir: Path) -> tuple[dict, dict]:
    run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    manifest = run.get("outputs", {}).get("evidenceArtifacts")
    if not isinstance(manifest, dict):
        return {}, {}
    artifacts, references = {}, {}
    for name in ("heatmap", "zoneMatrix", "teamShape"):
        relative_path = manifest.get(name)
        if not isinstance(relative_path, str):
            continue
        path = (run_dir / relative_path).resolve()
        if path.is_relative_to(run_dir.resolve()) and path.is_file():
            artifacts[name] = json.loads(path.read_text(encoding="utf-8"))
            references[name] = relative_path
    return artifacts, references


def _requested_team(question: str, groups: dict) -> str:
    lowered = question.lower().replace("-", "_")
    for team in groups:
        if team.lower() in lowered:
            return team
    return "all" if "all" in groups else next(iter(groups), "unknown")


def _zone_from_question(question: str, events: list[dict]) -> str:
    match = re.search(r"r[0-2]c[0-2]", question.lower())
    if match:
        return match.group(0)
    if events:
        return events[0]["zone"]["id"]
    return "r1c1"


def _zone_count(matrix: dict, team: str, zone_id: str) -> int | None:
    group = matrix.get("groups", {}).get(team)
    match = re.fullmatch(r"r([0-2])c([0-2])", zone_id)
    if not group or not match:
        return None
    row, column = (int(value) for value in match.groups())
    return group["counts"][row][column]


def answer_question(tools: ToolLayer, question: str, *, prior_trace: list[dict] | None = None) -> dict:
    """Answer with candidate evidence only; this function never drafts a plan."""
    summary = tools.run_perception(run_dir=tools._require_run())
    if prior_trace:
        tools.trace = [*prior_trace, *tools.trace]
    events = tools.list_events()
    if not events:
        tools.note_decision("No candidate visual event", "stop",
                            "A chat response cannot make a tactical claim without event evidence")
        return {"status": "no_evidence", "answer": "No candidate event evidence is available for this session.",
                "evidence": {"events": [], "clips": [], "artifacts": {}}, "run": summary}

    zone_id = _zone_from_question(question, events)
    tools.note_decision("Question requests spatial candidate evidence", "analyze_zone",
                        f"Selected {zone_id} from the question or first candidate event")
    zone = tools.analyze_zone(zone_id)
    selected = next((event for event in events if event["zone"]["id"] == zone_id), events[0])
    try:
        tools.get_clip(selected["id"])
    except RuntimeError:
        tools.note_decision("Selected candidate lacks an evidence clip", "stop",
                            "The chat must not describe a candidate without its linked clip")
        return {
            "status": "evidence_incomplete",
            "answer": "A candidate event exists, but its linked evidence clip is unavailable. "
                      "No tactical conclusion is provided.",
            "limitations": ["Evidence clip unavailable", "Candidate events and tracks are unverified"],
            "evidence": {"events": [selected["id"]], "clips": [], "artifacts": {}},
            "run": summary,
        }
    artifacts, artifact_refs = _read_artifacts(tools._require_run())
    tools.note_external("read_evidence_artifacts", {
        "available": sorted(artifact_refs), "selectedZone": zone_id,
    })
    matrix = artifacts.get("zoneMatrix", {})
    team = _requested_team(question, matrix.get("groups", {}))
    occupancy = _zone_count(matrix, team, zone_id)
    wording = (
        f"Candidate evidence for {team.replace('_', ' ')} in {zone_id}: "
        f"the zone tool found {zone['candidateEvents']} candidate events "
        f"({zone['byType']})."
    )
    if occupancy is not None:
        wording += f" The occupancy matrix records {occupancy} candidate track observations in that image-relative zone."
    wording += " Review the linked clip; this is not a verified tactical conclusion."
    return {
        "status": "evidence_backed_candidate",
        "answer": wording,
        "limitations": [
            "Candidate events and tracks are unverified",
            "Zones and artifacts use image-relative coordinates",
            "This chat endpoint cannot draft or approve a plan",
        ],
        "evidence": {
            "events": [selected["id"]],
            "clips": [{"eventId": selected["id"], "clipPath": selected["evidence"]["clipPath"]}],
            "zone": zone, "artifacts": artifact_refs,
        },
        "run": summary,
    }
