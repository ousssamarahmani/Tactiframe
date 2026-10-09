# Implementation Plan: TactiFrame — Hackathon Repository

## Overview

Implement TactiFrame as a GitHub-ready hackathon repository for the OpenCV AI Competition 2026
(Agentic Vision track with AWS). The implementation follows a strict priority order:

- **P0 (must ship):** cv/ perception pipeline, agent/ layer, api/, AWS S3/Bedrock, tests/, repo hygiene
- **P1 (should ship):** mcp/server.py, UI polish
- **P2 / stretch:** NVIDIA VSS / Cosmos integration — only after P0 is complete

The base for `cv/` is forked from [TactiScout-CV](https://github.com/Marouan-balha/TactiScout-CV).
Existing modules (detector, tracker, team_classifier, ball_interpolation) are imported as-is; only
`cv/pipeline.py` is extended, and two new modules (`cv/zones.py`, `cv/event_detector.py`) are added.

---

## Tasks

<!-- ═══════════════════════════════════════════════════════════════
     P0 — BLOCK 1: Repository skeleton & base fork
     ═══════════════════════════════════════════════════════════════ -->

- [ ] 1. Set up repository skeleton and fork TactiScout-CV base
  - Clone / fork https://github.com/Marouan-balha/TactiScout-CV and copy the four existing
    modules (`cv/detector.py`, `cv/tracker.py`, `cv/team_classifier.py`,
    `cv/ball_interpolation.py`) into `cv/` — do NOT modify their logic.
  - Create the full directory tree:
    `cv/`, `agent/`, `api/`, `mcp/`, `tests/`, `docs/`, `aws/`,
    `data/sessions/` (gitkeep), `models/` (gitkeep).
  - Add `cv/__init__.py`, `agent/__init__.py`, `api/__init__.py`, `mcp/__init__.py`,
    `tests/__init__.py` with empty bodies.
  - Create `config.py` at the project root exporting all tuneable constants:
    `YOLO_CONF_THRESHOLD = 0.5`, `ZONE_ROWS`, `ZONE_COLS`, `APPROVAL_TIMEOUT_SECONDS`,
    `BEDROCK_MODEL_ID`, `S3_BUCKET`, `AGENTCORE_ENABLED`, `AGENTCORE_RUNTIME_ID`,
    `MCP_TRANSPORT`.
  - _Requirements: 9.1–9.10, 1.1, 2.1_

<!-- ═══════════════════════════════════════════════════════════════
     P0 — BLOCK 2: Repo hygiene documents
     ═══════════════════════════════════════════════════════════════ -->

- [ ] 2. Add repository hygiene files
  - [ ] 2.1 Write `requirements.txt` with pinned versions for all direct runtime dependencies:
    `opencv-python>=5.0.0`, `ultralytics` (YOLO), `supervision` (ByteTrack wrapper),
    `fastapi`, `uvicorn`, `boto3`, `mcp[cli]`, `hypothesis`, `pytest`, `moto[s3]`,
    `pydantic>=2`, and any transitive pins identified during setup.
    - _Requirements: 9.2_

  - [ ] 2.2 Write `.gitignore` excluding `data/`, `models/`, `.env`, `__pycache__/`,
    `*.pt`, `*.onnx`, `*.pth`, `*.weights`, `*.mp4` inside `data/`, `*.egg-info/`,
    `.aws/credentials`, and standard Python / IDE ignores.
    - _Requirements: 9.3, 9.8_

  - [ ] 2.3 Write `LICENSE` — MIT licence with current year and author name.
    - _Requirements: 9.4_

  - [ ] 2.4 Write `docs/HACKATHON.md` — competition context, P0/P1/P2 priority table,
    and an explicit non-goals section (no production multi-camera, no chatbot-only Q&A,
    NVIDIA VSS is stretch).
    - _Requirements: 9.5_

  - [ ] 2.5 Write `docs/ARCHITECTURE.md` — written descriptions of all components
    (`cv/`, `agent/`, `api/`, `mcp/`, `aws/`, session store), data flows, and the
    Mermaid diagram reproduced from the design document.
    - _Requirements: 9.6_

  - [ ] 2.6 Write `docs/EVAL.md` — evaluation criteria, known limitations, and a
    reproducible demo section with exact environment-setup steps, exact commands to run,
    and the expected observable output for each command.
    - _Requirements: 9.7_

  - [ ] 2.7 Write `README.md` with: one-liner, Mermaid architecture diagram, quickstart
    section, demo flow section, "How this meets Agentic Vision" section with a trace
    example, and an explicit non-goals section. Use the product name TactiFrame
    throughout — no TactiScout references.
    - _Requirements: 9.1, 9.9, 9.10_

<!-- ═══════════════════════════════════════════════════════════════
     P0 — BLOCK 3: cv/ perception pipeline
     ═══════════════════════════════════════════════════════════════ -->

- [ ] 3. Implement cv/zones.py — Zone_Analyzer
  - [ ] 3.1 Create `cv/zones.py` with `ZoneAnalyzer` class and `ZoneStats` dataclass.
    - Constructor accepts `rows: int`, `cols: int`, `pitch_width_px: int`,
      `pitch_height_px: int`; validate that `rows * cols` is between 6 and 64 inclusive.
    - `assign_zone(x, y) -> str` maps pixel coordinates to a zone ID string (e.g., `"Z03"`).
    - `compute_occupancy(tracks, time_window) -> dict[str, dict[str, int]]` returns
      `{zone_id: {team_id: frame_count}}` for the given time window.
    - `zone_stats(zone_id, occupancy) -> ZoneStats` returns occupancy counts, dominant team
      (highest frame count, ties broken by lexicographic team ID), and top-3 timestamps.
    - `list_valid_zones() -> list[str]` returns all valid zone IDs for error messages.
    - _Requirements: 1.3, 2.1, 2.2, 2.3, 2.4_

  - [ ]* 3.2 Write property test for Zone_Analyzer — Property 2: Zone assignment completeness
    - **Property 2: Zone assignment completeness**
    - For any `(x, y)` within pitch dimensions, `assign_zone` returns exactly one ID
      that appears in `list_valid_zones()`.
    - **Validates: Requirements 1.3, 2.1**

  - [ ]* 3.3 Write property test for Zone_Analyzer — Property 6: Zone occupancy conservation
    - **Property 6: Zone occupancy conservation**
    - For any set of player tracks and any time window, the sum of all occupancy frame
      counts across all zones equals the total `(player_track, frame)` pairs in the window.
    - **Validates: Requirements 2.2**

  - [ ]* 3.4 Write property test for Zone_Analyzer — Property 7: Dominant team correctness
    - **Property 7: Dominant team correctness**
    - For any `ZoneStats`, `dominant_team` is the team with the highest value in
      `occupancy_counts`; ties broken deterministically (lexicographic).
    - **Validates: Requirements 2.3**

- [ ] 4. Implement cv/event_detector.py — Event_Detector
  - [ ] 4.1 Create `cv/event_detector.py` with `Event` dataclass and `EventDetector` class.
    - `Event` fields: `event_id` (UUID str), `event_type`
      (`"pass"|"shot"|"cross"|"press"|"set_piece"`), `timestamp` (float, rounded to 2 dp),
      `player_ids` (list[str]), `zone_id` (str), `clip_local_path` (str),
      `clip_s3_url` (str | None).
    - `detect_events(tracks: list[TrackFrame]) -> list[Event]` applies heuristics for all
      five event types and returns events sorted ascending by `timestamp`.
    - All timestamps stored via `round(raw_ts, 2)`.
    - _Requirements: 1.4, 1.5_

  - [ ]* 4.2 Write property test for Event_Detector — Property 5: Event timestamp precision
    - **Property 5: Event timestamp precision**
    - For any raw timestamp, the stored value satisfies `round(ts, 2) == stored_ts`.
    - **Validates: Requirements 1.4**

- [ ] 5. Extend cv/pipeline.py — Perception_Engine
  - [ ] 5.1 Add `compute_clip_bounds(t: float, d: float) -> tuple[float, float]` as a
    pure module-level function: returns `(max(0.0, t-2.0), min(d, t+2.0))`.
    - _Requirements: 1.5_

  - [ ]* 5.2 Write property test for pipeline — Property 3: Evidence clip boundary clamping
    - **Property 3: Evidence clip boundary clamping**
    - For any `t >= 0` and `d > 0`, `compute_clip_bounds` satisfies the clamping formula.
    - **Validates: Requirements 1.5**

  - [ ] 5.3 Extend `run_pipeline(video_path, session_id, config) -> SessionResult` to:
    - Raise `FileNotFoundError` if `video_path` does not exist.
    - Raise `ModelNotFoundError` if YOLO weights are not found.
    - Call `ZoneAnalyzer` after tracking to assign zone IDs to each track frame.
    - Call `EventDetector.detect_events()` on the completed tracks.
    - Extract evidence clips with `cv2.VideoCapture` seek + `cv2.VideoWriter` write,
      using `compute_clip_bounds` for time boundaries.
    - Upload each clip to S3 (log error + set `clip_s3_url=None` on failure).
    - Write session output to `data/sessions/{session_id}/events.json` and
      `data/sessions/{session_id}/metadata.json`.
    - Ensure separate sessions never share a path (UUID-based `session_id`).
    - _Requirements: 1.1–1.8, 5.2, 5.6_

  - [ ]* 5.4 Write property test for pipeline — Property 1: Detection confidence threshold
    - **Property 1: Detection confidence threshold**
    - For any list of raw detections with arbitrary confidence scores, the filtered
      result contains only items with `confidence >= 0.5`.
    - **Validates: Requirements 1.1**

  - [ ]* 5.5 Write property test for pipeline — Property 4: Session path uniqueness
    - **Property 4: Session path uniqueness**
    - For any N distinct session IDs, all `data/sessions/{id}/` paths are distinct.
    - **Validates: Requirements 1.6, 5.1**

- [ ] 6. Checkpoint — cv/ layer complete
  - Ensure all tests pass (`pytest tests/test_cv_properties.py -v`).
  - Verify that `cv/zones.py` and `cv/event_detector.py` import cleanly alongside the
    four unmodified TactiScout-CV modules.
  - Ask the user if any adjustments are needed before proceeding to the agent layer.

<!-- ═══════════════════════════════════════════════════════════════
     P0 — BLOCK 4: agent/ layer
     ═══════════════════════════════════════════════════════════════ -->

- [ ] 7. Implement agent/trace.py — Trace_Logger
  - [ ] 7.1 Create `agent/trace.py` with `TraceLogger` class.
    - `record_tool_call(step, tool_name, input_args, output_summary,
      hypothesis_before, hypothesis_after)` appends to `tool_calls` list.
    - `record_approval(decision, reason, timestamp)` sets `trace["approval"]`.
    - `record_termination(reason)` appends a termination entry.
    - `save(session_id)` serialises the full trace to
      `data/sessions/{session_id}/trace.json`, including `session_id`,
      `started_at`, `ended_at`, `tool_calls`, `plan_versions`, `approval`.
    - _Requirements: 4.2, 4.3, 4.6, 8.5_

  - [ ]* 7.2 Write property test for Trace_Logger — Property 9: Trace tool-call completeness
    - **Property 9: Trace tool-call completeness**
    - For any sequence of N tool calls, `trace["tool_calls"]` has exactly N entries,
      each with `step`, `tool_name`, `input`, `output_summary` fields.
    - **Validates: Requirements 4.2, 4.6, 10.1**

- [ ] 8. Implement agent/tools.py — Tool_Layer (single source of truth)
  - [ ] 8.1 Create `agent/tools.py` skeleton with all six function signatures and
    the session-file helpers (`_load_metadata`, `_save_metadata`, `_load_events`,
    `_find_event_by_id`).
    - _Requirements: 3.1_

  - [ ] 8.2 Implement `run_perception(video_path) -> dict`.
    - Validates that `video_path` exists; returns `{"error": ...}` if not.
    - Generates a UUID session ID, creates `data/sessions/{id}/` directory.
    - Uploads the video file to S3 under `sessions/{id}/video.*`.
    - Calls `run_pipeline(video_path, session_id, config)`.
    - Returns `{"session_id": session_id}` on success or `{"error": ...}` on failure.
    - _Requirements: 3.2, 5.1_

  - [ ] 8.3 Implement `list_events(session_id, event_type=None, zone=None) -> dict`.
    - Returns `{"error": "Unknown session: <id>"}` if session not found.
    - Reads `events.json`, applies optional filters.
    - Sets `metadata["events_reviewed"] = True` and saves `metadata.json`.
    - Returns `{"events": [...]}`.
    - _Requirements: 3.3_

  - [ ] 8.4 Implement `get_clip(event_id) -> dict`.
    - Searches all sessions for the event; returns `{"error": "Unknown event: <id>"}` if not found.
    - Returns `{"local_path": str, "s3_url": str | None}`.
    - _Requirements: 3.4_

  - [ ] 8.5 Implement `analyze_zone(session_id, zone_id) -> dict`.
    - Returns `{"error": "Unknown session: <id>"}` if session not found.
    - Returns `{"error": "Invalid zone: <id>. Valid zones: [...]"}` if zone unknown.
    - Returns full `ZoneStats` dict otherwise.
    - _Requirements: 3.5, 2.3, 2.4_

  - [ ] 8.6 Implement `draft_plan(session_id, question) -> dict`.
    - Hard gate: reads `metadata["events_reviewed"]`; returns
      `{"error": "list_events must be called before draft_plan"}` if `False`.
    - If gate passes, calls `AgentOrchestrator().invoke(session_id, question)`.
    - Returns `{"plan": str, "event_ids": list[str]}` or `{"error": str}`.
    - _Requirements: 3.6, 3.7, 4.4_

  - [ ] 8.7 Implement `request_approval(session_id, plan) -> dict`.
    - Writes `plan.json` with `status="pending_approval"`.
    - Polls `plan.json` for a coach decision up to `APPROVAL_TIMEOUT_SECONDS`.
    - Returns `{"decision": ..., "reason": ...}` or `{"error": "Approval timeout after <N>s"}`.
    - _Requirements: 3.8, 3.9, 8.1–8.4_

  - [ ]* 8.8 Write property test for Tool_Layer — Property 8: Evidence-first gate
    - **Property 8: Evidence-first gate**
    - For any session where `list_events` has not been called, `draft_plan` returns
      a dict with an `error` key and `AgentOrchestrator.invoke` is never called.
    - **Validates: Requirements 3.6, 4.4, 10.3**

  - [ ]* 8.9 Write property test for Tool_Layer — Property 12: Rejection reason round-trip
    - **Property 12: Rejection reason round-trip**
    - For any rejection reason string (including empty string), the reason returned by
      `request_approval` equals the reason submitted by the coach exactly.
    - **Validates: Requirements 3.9, 8.4**

- [ ] 9. Implement agent/orchestrator.py — Agent_Orchestrator
  - [ ] 9.1 Create `agent/prompts.py` with the system prompt string for Bedrock
    (instructs the model to use TactiFrame's six tools to form hypotheses and draft a
    tactical plan, referencing detected events as evidence).
    - _Requirements: 4.1_

  - [ ] 9.2 Create `agent/orchestrator.py` with `AgentOrchestrator` class.
    - `MAX_ITERATIONS = 10` class constant.
    - `invoke(session_id, question) -> dict` runs the Bedrock Converse loop:
      builds `messages` list, calls `bedrock_runtime.converse()` with `toolConfig`
      generated from `agent/tools.py` signatures, dispatches `tool_use` blocks to
      Tool_Layer functions, feeds `toolResult` messages back, repeats until
      `stopReason == "end_turn"` or iteration limit reached.
    - On `ThrottlingException` or transient errors: single retry after 2 s sleep;
      log retry in trace; return `{"error": ...}` if retry also fails.
    - AgentCore opt-in: if `AGENTCORE_ENABLED=true` and client available, route
      through `agentcore_client.invoke_agent_runtime(...)`.
    - On max iterations: call `trace_logger.record_termination("max_iterations_reached")`
      and return `{"error": "Max iterations reached without producing a plan"}`.
    - _Requirements: 4.1, 4.4, 4.5, 4.7, 4.8, 5.3, 5.4, 5.7_

  - [ ]* 9.3 Write property test for Agent_Orchestrator — Property 10: Reasoning loop bound
    - **Property 10: Reasoning loop iteration bound**
    - For any sequence of tool results from a mocked Bedrock that always returns
      `stopReason="tool_use"`, the loop terminates after exactly 10 iterations.
    - **Validates: Requirements 4.1, 4.8**

- [ ] 10. Checkpoint — agent/ layer complete
  - Ensure all tests pass (`pytest tests/test_tools_properties.py tests/test_orchestrator.py -v`).
  - Verify that `agent/tools.py` imports cleanly and `draft_plan` gate works end-to-end
    with a mock session.
  - Ask the user if any adjustments are needed before proceeding.

<!-- ═══════════════════════════════════════════════════════════════
     P0 — BLOCK 5: Required trace tests (Requirement 10)
     ═══════════════════════════════════════════════════════════════ -->

- [ ] 11. Implement tests/test_agent_trace.py — required by Requirement 10
  - [ ] 11.1 Create `tests/conftest.py` with shared fixtures:
    - `synthetic_video` — generates a 30-frame blank MP4 with `cv2.VideoWriter`.
    - `mock_bedrock` — `unittest.mock.patch` for `boto3.client("bedrock-runtime")` that
      returns a valid `converse` response sequence driving `run_perception → list_events
      → draft_plan`.
    - `mock_s3` — `moto` `mock_aws` decorator creating the configured S3 bucket.
    - _Requirements: 10.4_

  - [ ] 11.2 Implement `tests/test_agent_trace.py` with the four assertions from Req 10:
    1. Full loop on synthetic video: `tool_calls` contains ≥1 entry for each of
       `run_perception`, `list_events`, `draft_plan`.
    2. Every `draft_plan` `tool_calls` entry has `event_ids` that are a non-empty subset
       of `event_id` values from prior `list_events` entries.
    3. Calling `draft_plan` without prior `list_events` returns `{"error": ...}` and
       `AgentOrchestrator.invoke` is called 0 times.
    4. All assertions pass with `pytest tests/` and no live AWS credentials.
    - _Requirements: 10.1, 10.2, 10.3, 10.4_

  - [ ]* 11.3 Write property test — Property 14: Draft plan evidence linkage
    - **Property 14: Draft plan evidence linkage**
    - For any complete agent session trace, every `draft_plan` `tool_calls` entry has
      `event_ids` that are a non-empty subset of `event_id` values from prior
      `list_events` entries in the same trace.
    - **Validates: Requirements 3.7, 4.4, 10.2**

<!-- ═══════════════════════════════════════════════════════════════
     P0 — BLOCK 6: API + Approval Gate
     ═══════════════════════════════════════════════════════════════ -->

- [ ] 12. Implement api/schemas.py and api/main.py — FastAPI application
  - [ ] 12.1 Create `api/schemas.py` with all Pydantic v2 models from the design:
    `AnalyseRequest`, `AnalyseResponse`, `EventRecord`, `ClipResponse`,
    `ApprovalRequest`, `ApprovalResponse`, `SessionMetadata`, `PlanRecord`, `ZoneStats`.
    - _Requirements: 7.1–7.10_

  - [ ] 12.2 Implement `api/main.py` with the FastAPI app and all five endpoints:
    - `POST /analyse` — validates `video_path` (≤1024 chars, must exist or be S3 URI),
      calls `run_perception` in `BackgroundTasks`, returns `{"session_id": ...}` within
      5 s. Returns HTTP 400 if path invalid.
    - `GET /events/{session_id}` — calls `list_events`; returns HTTP 404 if session missing.
    - `GET /clip/{event_id}` — calls `get_clip`; returns HTTP 404 if event missing.
    - `POST /approve/{session_id}` — validates `ApprovalRequest` body; writes decision
      to `plan.json`; returns HTTP 409 if no pending plan; HTTP 404 if session missing.
    - `GET /session/{session_id}` — returns `SessionMetadata` + plan status.
    - Maps tool-layer `{"error": ...}` responses to the correct HTTP status codes per the
      error taxonomy in the design document.
    - _Requirements: 7.1–7.10, 8.1–8.6_

  - [ ]* 12.3 Write example-based FastAPI tests in `tests/test_api.py`
    - Cover happy paths for all five endpoints and all error paths listed in Req 7.
    - Use `TestClient` from `fastapi.testclient` with mocked Tool_Layer functions.
    - _Requirements: 7.1–7.10_

  - [ ]* 12.4 Write property test — Property 11: Approval status transition
    - **Property 11: Approval status transition**
    - For any drafted plan, status is `pending_approval` after `draft_plan` and
      transitions to exactly `approved` or `revision_required` — never stays
      `pending_approval` after a decision.
    - **Validates: Requirements 8.1, 8.3, 8.4**

- [ ] 13. Implement entry-point scripts
  - [ ] 13.1 Create `run_pipeline.py`:
    - Parses `sys.argv` for a required `--video` argument; prints usage + exits non-zero
      if missing.
    - Validates the path exists; prints error + exits non-zero if not.
    - Calls `run_pipeline`, prints summary (total event count, each event type, each
      timestamp), exits 0.
    - _Requirements: 11.1, 11.3, 11.5_

  - [ ] 13.2 Create `run_agent.py`:
    - Parses `sys.argv` for a required `--video` argument; prints usage + exits non-zero
      if missing.
    - Validates path; prints error + exits non-zero if not.
    - Calls the full agent loop (including Approval_Gate), prints final approved plan or
      rejection reason, exits 0.
    - _Requirements: 11.2, 11.4, 11.5_

- [ ] 14. Checkpoint — P0 complete
  - Run the full test suite: `pytest tests/ -v`.
  - Ensure all P0 items build and import cleanly with no live AWS credentials.
  - Ask the user if any adjustments are needed before moving to P1.

<!-- ═══════════════════════════════════════════════════════════════
     P0 — BLOCK 7: AWS deployment configuration
     ═══════════════════════════════════════════════════════════════ -->

- [ ] 15. Add AWS deployment configuration
  - [ ] 15.1 Create `aws/apprunner.yaml` — App Runner service definition pointing to the
    FastAPI container image, with environment variable stubs for `S3_BUCKET`,
    `BEDROCK_MODEL_ID`, `AWS_REGION`, and `APPROVAL_TIMEOUT_SECONDS`.
    - _Requirements: 5.5_

  - [ ] 15.2 Create `Dockerfile` — multi-stage build: installs Python deps from
    `requirements.txt`, copies source, exposes port 8000, sets `CMD ["uvicorn",
    "api.main:app", "--host", "0.0.0.0", "--port", "8000"]`.
    - _Requirements: 5.5_

  - [ ] 15.3 Create `aws/lambda_container/` variant with a Lambda handler shim
    (`aws/lambda_handler.py`) using `mangum` to wrap the FastAPI app for Lambda
    container image deployment.
    - _Requirements: 5.5_

<!-- ═══════════════════════════════════════════════════════════════
     P1 — BLOCK 8: MCP Server
     ═══════════════════════════════════════════════════════════════ -->

- [ ] 16. Implement mcp/server.py — MCP_Server (P1)
  - [ ] 16.1 Create `mcp/server.py` using `FastMCP` from the `mcp` Python SDK.
    - Import all six functions from `agent/tools` directly.
    - Register each with `@mcp.tool()` decorator wrapping the import — no logic copied.
    - Support `stdio` and `streamable-http` transports via `MCP_TRANSPORT` env var.
    - On startup bind to configured host and port.
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 3.10_

  - [ ]* 16.2 Write property test — Property 13: MCP delegation identity
    - **Property 13: MCP delegation identity**
    - For any of the six tools and any valid input arguments, the result from calling
      through `MCP_Server` is structurally identical (same keys and values) to calling
      the function directly in `agent/tools.py`.
    - **Validates: Requirements 6.2, 6.3**

  - [ ]* 16.3 Write example-based tests for MCP server in `tests/test_mcp.py`
    - Verify tool list advertisement matches Tool_Layer schema exactly (byte-for-byte).
    - Verify error responses from Tool_Layer are passed through unchanged.
    - _Requirements: 6.2, 6.4_

- [ ] 17. Checkpoint — P1 complete
  - Run the full test suite: `pytest tests/ -v`.
  - Verify the MCP server starts on `stdio` transport without errors.
  - Ask the user if any adjustments are needed before considering P2 stretch work.

<!-- ═══════════════════════════════════════════════════════════════
     P2 — BLOCK 9: NVIDIA VSS / Cosmos (stretch — after P0 complete)
     ═══════════════════════════════════════════════════════════════ -->

- [ ] 18. Stretch: NVIDIA VSS / Cosmos integration (P2 — only after P0 verified complete)
  - [ ] 18.1 Create `cv/vss_adapter.py` — thin wrapper around the NVIDIA Video Search and
    Summarisation API; implement `query_vss(video_path, prompt) -> dict` that calls the
    VSS endpoint and returns a structured response compatible with `Event` schema.
    - _Requirements: none (stretch goal, not required for base score)_

  - [ ] 18.2 Add a `--use-vss` flag to `run_pipeline.py` that routes perception through
    `vss_adapter.py` instead of the local YOLO + ByteTrack stack when set.
    - _Requirements: none (stretch goal)_

  - [ ]* 18.3 Write smoke tests for VSS adapter in `tests/test_vss.py` using mocked
    NVIDIA API responses, skipped if `NVIDIA_API_KEY` env var is not set.
    - _Requirements: none (stretch goal)_

- [ ] 19. Final checkpoint — all tasks complete
  - Run the full test suite: `pytest tests/ -v --tb=short`.
  - Confirm repo contains no model weight files, no match video files, no AWS
    credential files, and no Google Cloud references.
  - Confirm all user-facing strings use the product name TactiFrame.
  - Ask the user for a final review before tagging a release commit.

---

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP.
- P0 tasks (1–15) must be complete before P1 (16–17) is started.
- P2 task (18) is a stretch goal and must only be started after P0 is verified.
- The four TactiScout-CV modules (`detector.py`, `tracker.py`, `team_classifier.py`,
  `ball_interpolation.py`) are copied as-is — do NOT modify their internal logic.
- All property-based tests use Hypothesis with `@settings(max_examples=100)`.
- No live AWS credentials are required to run the test suite (use `moto` for S3, `mock.patch` for Bedrock).
- Each property test includes a comment: `# Feature: tactiframe-hackathon-repo, Property N: <title>`
- The `draft_plan` evidence-first gate is implemented once in `agent/tools.py` and inherited by
  both the MCP server and the FastAPI adapter automatically.

---

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["2.1", "2.2", "2.3", "2.4", "2.5", "2.6", "2.7"] },
    { "id": 1, "tasks": ["3.1", "4.1", "5.1"] },
    { "id": 2, "tasks": ["3.2", "3.3", "3.4", "4.2", "5.2", "5.4", "5.5", "7.1"] },
    { "id": 3, "tasks": ["5.3", "7.2"] },
    { "id": 4, "tasks": ["8.1", "9.1"] },
    { "id": 5, "tasks": ["8.2", "8.3", "8.4", "8.5", "8.6", "8.7"] },
    { "id": 6, "tasks": ["8.8", "8.9", "9.2", "11.1", "12.1"] },
    { "id": 7, "tasks": ["9.3", "11.2", "12.2"] },
    { "id": 8, "tasks": ["11.3", "12.3", "12.4", "13.1", "13.2"] },
    { "id": 9, "tasks": ["15.1", "15.2", "15.3"] },
    { "id": 10, "tasks": ["16.1"] },
    { "id": 11, "tasks": ["16.2", "16.3"] },
    { "id": 12, "tasks": ["18.1"] },
    { "id": 13, "tasks": ["18.2"] },
    { "id": 14, "tasks": ["18.3"] }
  ]
}
```
