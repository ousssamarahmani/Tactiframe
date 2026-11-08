"""HTTP review API for completed local TactiFrame sessions.

The API is intentionally thin: OpenCV and the agent write session artifacts, and
this module exposes those artifacts plus the existing explicit coach-approval
gate. It does not run perception or generate plans on a GET request.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from agent.tools import ToolLayer
from config import SESSION_DIR


class ApprovalRequest(BaseModel):
    """The human decision required to finalize a draft plan."""

    decision: str = Field(pattern="^(approved|rejected)$")
    coach: str = Field(min_length=1, max_length=120)


def _read_json(path: Path, artifact: str):
    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session artifact not found: {artifact}",
        )
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Invalid session artifact: {artifact}",
        ) from error


def _safe_identifier(value: str) -> str:
    if not value or value in {".", ".."} or Path(value).name != value:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return value


def _safe_session_file(run_dir: Path, relative_path: str, artifact: str) -> Path:
    path = (run_dir / relative_path).resolve()
    if not path.is_relative_to(run_dir.resolve()) or not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Session artifact not found: {artifact}")
    return path


def _resolve_session(session_root: Path, session_id: str) -> Path:
    """Resolve a folder name or runId without allowing path traversal."""

    session_id = _safe_identifier(session_id)
    direct = session_root / session_id
    if direct.is_dir() and (direct / "run.json").is_file():
        return direct

    if session_root.is_dir():
        for candidate in session_root.iterdir():
            if not candidate.is_dir():
                continue
            metadata_path = candidate / "run.json"
            if metadata_path.is_file():
                metadata = _read_json(metadata_path, "run.json")
                if metadata.get("runId") == session_id:
                    return candidate
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")


def _approval_tools(run_dir: Path) -> ToolLayer:
    """Restore enough session state for ToolLayer.request_approval()."""

    tools = ToolLayer()
    tools.run_dir = run_dir.resolve()
    trace_path = run_dir / "trace.json"
    if trace_path.is_file():
        trace = _read_json(trace_path, "trace.json")
        tools.run_id = trace.get("runId")
        tools.trace = trace.get("steps", [])
    else:
        tools.run_id = _read_json(run_dir / "run.json", "run.json").get("runId")
    return tools


def create_app(session_root: Path | str | None = None) -> FastAPI:
    """Create the API with an optional session root for tests or deployment."""

    root = Path(session_root or SESSION_DIR).resolve()
    app = FastAPI(title="TactiFrame API", version="0.1.0")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "product": "TactiFrame"}

    @app.get("/sessions/{session_id}")
    def get_session(session_id: str) -> dict:
        run_dir = _resolve_session(root, session_id)
        return {"sessionId": run_dir.name, "run": _read_json(run_dir / "run.json", "run.json")}

    @app.get("/sessions/{session_id}/events")
    def get_events(session_id: str) -> dict:
        run_dir = _resolve_session(root, session_id)
        return {"sessionId": run_dir.name, "events": _read_json(run_dir / "events.json", "events.json")}

    @app.get("/sessions/{session_id}/trace")
    def get_trace(session_id: str) -> dict:
        run_dir = _resolve_session(root, session_id)
        return _read_json(run_dir / "trace.json", "trace.json")

    @app.get("/sessions/{session_id}/plan")
    def get_plan(session_id: str) -> dict:
        run_dir = _resolve_session(root, session_id)
        return _read_json(run_dir / "plan.json", "plan.json")

    @app.get("/sessions/{session_id}/artifacts")
    def get_artifacts(session_id: str) -> dict:
        run_dir = _resolve_session(root, session_id)
        run = _read_json(run_dir / "run.json", "run.json")
        manifest = run.get("outputs", {}).get("evidenceArtifacts")
        if not isinstance(manifest, dict):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Session evidence artifacts have not been generated")
        artifacts = {}
        for name in ("heatmap", "zoneMatrix", "teamShape"):
            relative_path = manifest.get(name)
            if not isinstance(relative_path, str):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                    detail=f"Session artifact not found: {name}")
            artifacts[name] = _read_json(_safe_session_file(run_dir, relative_path, name), name)
        return {"sessionId": run_dir.name, "artifacts": artifacts}

    @app.get("/sessions/{session_id}/video")
    def get_video(session_id: str):
        run_dir = _resolve_session(root, session_id)
        run = _read_json(run_dir / "run.json", "run.json")
        relative_path = run.get("outputs", {}).get("annotatedVideo", "tracked.mp4")
        if not isinstance(relative_path, str):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Session annotated video is not available")
        return FileResponse(_safe_session_file(run_dir, relative_path, "annotated video"), media_type="video/mp4")

    @app.get("/review/{session_id}")
    def review_page(session_id: str):
        _resolve_session(root, session_id)
        page = Path(__file__).with_name("static") / "evidence_viewer.html"
        if not page.is_file():
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail="Evidence viewer is not installed")
        return FileResponse(page, media_type="text/html")

    @app.post("/sessions/{session_id}/approval")
    def record_approval(session_id: str, request: ApprovalRequest) -> dict:
        run_dir = _resolve_session(root, session_id)
        try:
            result = _approval_tools(run_dir).request_approval(
                decision=request.decision,
                coach=request.coach.strip(),
            )
        except (RuntimeError, ValueError) as error:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
        return {"sessionId": run_dir.name, "approval": result,
                "plan": _read_json(run_dir / "plan.json", "plan.json")}

    return app


app = create_app()
