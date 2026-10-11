"""Single local tool layer for TactiFrame's six agent actions.

The tools expose candidate visual evidence; they do not certify tactical facts.
"""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from run_pipeline import write_json


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ToolLayer:
    def __init__(self, repo_root: Path | None = None):
        self.repo_root = Path(repo_root or Path(__file__).resolve().parents[1]).resolve()
        self.run_dir: Path | None = None
        self.run_id: str | None = None
        self.events: list[dict] = []
        self.events_listed = False
        self.trace: list[dict] = []

    def _record(self, kind: str, name: str, details: dict) -> None:
        self.trace.append({"at": _now(), "kind": kind, "name": name, "details": details})
        if self.run_dir is not None:
            write_json(self.run_dir / "trace.json", {
                "schemaVersion": 1, "product": "TactiFrame",
                "runId": self.run_id or self.run_dir.name, "steps": self.trace,
            })

    def note_decision(self, hypothesis: str, next_tool: str, reason: str) -> None:
        self._record("decision", "select_next_tool", {
            "hypothesis": hypothesis, "nextTool": next_tool, "reason": reason,
        })

    def _require_run(self) -> Path:
        if self.run_dir is None:
            raise RuntimeError("Call run_perception before using session tools")
        return self.run_dir

    def run_perception(self, *, run_dir: Path | None = None, video: Path | None = None,
                       model: Path | None = None, field_polygons: Path | None = None,
                       output_dir: Path | None = None) -> dict:
        """Use a completed run, or execute OpenCV/YOLO observation and events."""
        if run_dir is None:
            if video is None or model is None:
                raise ValueError("Provide run_dir or both video and model")
            command = [sys.executable, str(self.repo_root / "run_pipeline.py"),
                       "--video", str(video), "--model", str(model)]
            if field_polygons is not None:
                command += ["--field-polygons", str(field_polygons)]
            if output_dir is not None:
                output_dir = (self.repo_root / output_dir).resolve() if not output_dir.is_absolute() else output_dir
                command += ["--output-dir", str(output_dir)]
            subprocess.run(command, cwd=self.repo_root, check=True)
            run_dir = output_dir
            if run_dir is None:
                raise ValueError("output_dir is required when launching perception")
        self.run_dir = (self.repo_root / run_dir).resolve() if not run_dir.is_absolute() else run_dir.resolve()
        metadata = json.loads((self.run_dir / "run.json").read_text(encoding="utf-8"))
        if metadata.get("status") != "observations-only":
            raise RuntimeError("Perception run is not complete")
        if not str(metadata.get("environment", {}).get("opencv", "")).startswith("5."):
            raise RuntimeError("This agent run requires OpenCV 5 observations")
        if not (self.run_dir / "events.json").is_file():
            subprocess.run([sys.executable, str(self.repo_root / "detect_events.py"),
                            "--run-dir", str(self.run_dir)], cwd=self.repo_root, check=True)
        self.events = json.loads((self.run_dir / "events.json").read_text(encoding="utf-8"))
        self.run_id = metadata["runId"]
        self.events_listed = False
        self.trace = []
        summary = {"runId": metadata["runId"], "candidateEvents": len(self.events),
                   "trackObservations": metadata["counts"]["trackObservations"],
                   "opencv": metadata["environment"]["opencv"],
                   "calibration": metadata["quality"]["pitchCalibration"]}
        self._record("tool", "run_perception", summary)
        return summary

    def list_events(self) -> list[dict]:
        self._require_run()
        self.events_listed = True
        by_type = {}
        for event in self.events:
            by_type[event["type"]] = by_type.get(event["type"], 0) + 1
        self._record("tool", "list_events", {"count": len(self.events), "byType": by_type})
        return self.events

    def get_clip(self, event_id: str) -> dict:
        run_dir = self._require_run()
        event = next((e for e in self.events if e["id"] == event_id), None)
        if event is None:
            raise ValueError(f"Unknown event: {event_id}")
        path = (run_dir / event["evidence"]["clipPath"]).resolve()
        if not path.is_relative_to(run_dir) or not path.is_file() or path.stat().st_size == 0:
            raise RuntimeError(f"Evidence clip is unavailable: {event_id}")
        result = {"eventId": event_id, "clipPath": str(path),
                  "zone": event["zone"], "status": event["status"]}
        self._record("tool", "get_clip", {"eventId": event_id,
                                         "clipPath": event["evidence"]["clipPath"]})
        return result

    def analyze_zone(self, zone_id: str) -> dict:
        self._require_run()
        selected = [e for e in self.events if e["zone"]["id"] == zone_id]
        by_type = {}
        for event in selected:
            by_type[event["type"]] = by_type.get(event["type"], 0) + 1
        result = {"zone": {"id": zone_id, "coordinateSystem": "image_relative_3x3"},
                  "candidateEvents": len(selected), "byType": by_type,
                  "eventIds": [e["id"] for e in selected]}
        self._record("tool", "analyze_zone", result)
        return result

    def draft_plan(self, event_id: str, clip: dict, zone_analysis: dict) -> dict:
        run_dir = self._require_run()
        if not self.events_listed:
            raise RuntimeError("draft_plan requires list_events in this agent run")
        event = next((e for e in self.events if e["id"] == event_id), None)
        if event is None or clip.get("eventId") != event_id:
            raise ValueError("Plan evidence must reference a listed event and its clip")
        if zone_analysis.get("zone", {}).get("id") != event["zone"]["id"]:
            raise ValueError("Zone analysis must match the selected event")
        plan = {"schemaVersion": 1, "id": f"plan-{uuid4().hex[:8]}",
                "status": "pending_approval", "createdAt": _now(),
                "proposal": ("Coach: review this visual grouping and decide whether to "
                             "investigate opponent spacing in the highlighted image zone."),
                "evidence": {"eventId": event_id,
                             "eventType": event["type"],
                             "clipPath": event["evidence"]["clipPath"],
                             "zone": event["zone"]},
                "limitations": ["Candidate event, not manually verified",
                                "Image-relative zone, not calibrated pitch coordinates",
                                "Ball and track identities are unverified"]}
        write_json(run_dir / "plan.json", plan)
        self._record("tool", "draft_plan", {"planId": plan["id"], "eventId": event_id})
        return plan

    def request_approval(self, *, decision: str | None = None,
                         coach: str | None = None) -> dict:
        run_dir = self._require_run()
        plan_path = run_dir / "plan.json"
        if not plan_path.is_file():
            raise RuntimeError("A draft plan is required before approval")
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        if decision is None:
            result = {"planId": plan["id"], "status": plan["status"],
                      "message": "Coach review required" if plan["status"] == "pending_approval"
                      else "Coach decision already recorded"}
        else:
            if decision not in {"approved", "rejected"} or not coach:
                raise ValueError("Human approval needs approved/rejected and a coach name")
            if plan["status"] != "pending_approval":
                raise RuntimeError("This plan already has a coach decision")
            plan["status"] = decision
            plan["decision"] = {"coach": coach, "at": _now()}
            write_json(plan_path, plan)
            result = {"planId": plan["id"], "status": decision, "coach": coach}
        self._record("tool", "request_approval", result)
        return result
