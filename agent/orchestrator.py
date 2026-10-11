"""Evidence-driven local agent loop for the TactiFrame demo."""

from collections import Counter

from agent.tools import ToolLayer


def run_agent(tools: ToolLayer, **perception_input) -> dict:
    summary = tools.run_perception(**perception_input)
    events = tools.list_events()
    if not events:
        tools.note_decision("No candidate visual event", "stop",
                            "Perception yielded no event to support a plan")
        return {"run": summary, "status": "no_evidence"}

    counts = Counter(event["type"] for event in events)
    contest_first = counts["zone_contest"] >= counts["zone_density"] and counts["zone_contest"] > 0
    chosen_type = "zone_contest" if contest_first else "zone_density"
    event = next((e for e in events if e["type"] == chosen_type), events[0])
    zone_id = event["zone"]["id"]
    if contest_first:
        tools.note_decision("Two-team visual contest", "get_clip",
                            f"Vision found {counts['zone_contest']} contest and {counts['zone_density']} density candidates")
        clip = tools.get_clip(event["id"])
        zone = tools.analyze_zone(zone_id)
    else:
        tools.note_decision("Sustained image-zone density", "analyze_zone",
                            f"Vision found {counts['zone_density']} density and {counts['zone_contest']} contest candidates")
        zone = tools.analyze_zone(zone_id)
        clip = tools.get_clip(event["id"])
    plan = tools.draft_plan(event["id"], clip, zone)
    approval = tools.request_approval()
    return {"run": summary, "selectedEvent": event["id"],
            "plan": plan, "approval": approval}
