"""Evidence-driven local agent loop for the TactiFrame demo."""

from collections import Counter
from pathlib import Path

from agent.tools import ToolLayer


def _bedrock_proposal(tools: ToolLayer, event: dict, clip: dict, zone: dict) -> dict | None:
    """Use Bedrock only after vision has selected concrete event evidence."""
    from config import AWS_ENABLED, AWS_PROFILE, AWS_REGION, BEDROCK_MODEL_ID

    if not AWS_ENABLED:
        return None
    from agent.bedrock import BedrockCoachProposal

    result = BedrockCoachProposal(BEDROCK_MODEL_ID, AWS_REGION, AWS_PROFILE).propose(
        event, zone, Path(clip["clipPath"])
    )
    tools.note_external("bedrock_converse", result)
    return result


def _sync_s3(tools: ToolLayer) -> dict | None:
    """Upload final local artifacts without turning a cloud failure into a lost run."""
    from config import AWS_ENABLED, AWS_PROFILE, AWS_REGION, S3_BUCKET

    if not AWS_ENABLED:
        return None
    from aws.storage import SessionUploader

    tools.note_external("s3_sync", {"status": "started", "bucket": S3_BUCKET})
    uploader = SessionUploader(S3_BUCKET, AWS_REGION, AWS_PROFILE)
    result = uploader.sync_session(tools._require_run())
    tools.note_external("s3_sync", result)
    uploader.sync_trace(tools._require_run())
    return result


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
        try:
            clip = tools.get_clip(event["id"])
        except RuntimeError as error:
            tools.note_decision("Evidence clip unavailable", "stop", str(error))
            return {"run": summary, "selectedEvent": event["id"], "status": "evidence_unavailable"}
        zone = tools.analyze_zone(zone_id)
    else:
        tools.note_decision("Sustained image-zone density", "analyze_zone",
                            f"Vision found {counts['zone_density']} density and {counts['zone_contest']} contest candidates")
        zone = tools.analyze_zone(zone_id)
        try:
            clip = tools.get_clip(event["id"])
        except RuntimeError as error:
            tools.note_decision("Evidence clip unavailable", "stop", str(error))
            return {"run": summary, "selectedEvent": event["id"], "status": "evidence_unavailable"}
    bedrock = _bedrock_proposal(tools, event, clip, zone)
    plan = tools.draft_plan(
        event["id"], clip, zone,
        proposal=bedrock.get("proposal") if bedrock and bedrock["status"] == "success" else None,
        proposal_source="bedrock" if bedrock and bedrock["status"] == "success" else "local-template",
    )
    approval = tools.request_approval()
    s3 = _sync_s3(tools)
    return {"run": summary, "selectedEvent": event["id"],
            "plan": plan, "approval": approval, "aws": {"bedrock": bedrock, "s3": s3}}
