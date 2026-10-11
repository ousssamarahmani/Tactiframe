# TactiFrame — Hackathon Context

## Competition

**Event:** OpenCV AI Competition 2026
**Track:** Agentic Vision (with AWS)
**Entry:** TactiFrame — Agentic Vision System for Football Opposition Analysis
**Deadline:** 26 October 2026 · Submit buffer: 24–25 Oct

---

## Priority Order

| Priority | Scope | Status |
|---|---|---|
| **P0** | cv/ perception pipeline, agent/ layer, api/, AWS S3/Bedrock integration, tests/, repo hygiene | Must ship |
| **P1** | mcp/server.py, UI polish | Should ship |
| **P2** | NVIDIA VSS / Cosmos integration | Stretch — only after P0 verified complete |

---

## Task List

### Phase A — Perception (P0)

- [ ] **Stabilize observation quality on one 3–5 min clip**
  `run_pipeline.py` now completes a full-duration technical run on a 4-minute-15-second match segment and writes the run folder. That clip and its visual derivatives are restricted to local simulation and education, so obtain a separately cleared clip for public submission. The first run used BoT-SORT; the current worker applies filters before ByteTrack. Before relying on observations for event logic, improve ID continuity and ball coverage. Confirm the selected checkpoint's use terms. The run uses a 5 fps working copy; its measured limitations are in `docs/EVAL.md`.

- [ ] **Zones (ROI or light homography) on every event**
  Every detected event in `events.json` must carry a `zone_id` field populated by `ZoneAnalyzer`. If a full homography is too slow for the clip length, use a fixed ROI grid. Verify that no event is written without a zone assignment.

- [ ] **Event detector (≥2 types, e.g. turnover, press density) → `events.json`**
  `cv/event_detector.py` must detect and classify at least two distinct event types (e.g. `press` and `turnover`, or `shot` and `cross`) using geometric / motion heuristics on the track data. All detected events are serialised to `data/sessions/{id}/events.json` with the frozen schema (see next task).

- [ ] **Evidence clip export per event → `clips/event_XXX.mp4`**
  For every event in `events.json`, extract a short video segment (`max(0, t-2s)` → `min(duration, t+2s)`) using `cv2.VideoCapture` + `cv2.VideoWriter`. Save to `data/sessions/{id}/clips/event_{event_id}.mp4` and record the local path in the event record. Upload to S3 and record `clip_s3_url` (set to `null` on upload failure — do not block the pipeline).

- [ ] **Freeze event JSON schema + sample in docs**
  Lock the `Event` schema (fields: `event_id`, `event_type`, `timestamp`, `player_ids`, `zone_id`, `clip_local_path`, `clip_s3_url`). Add `docs/EVENT_SCHEMA.md` with the field definitions, allowed `event_type` values, and a concrete sample `events.json` with at least 3 events. This file is the contract between `cv/` and `agent/`.

---

### Phase B — Agent + MCP (P0 / P1)

- [ ] **`agent/tools.py`: run_perception, list_events, get_clip, analyze_zone, draft_plan, request_approval**
  Implement all six Tool_Layer functions as the single source of truth. Each returns a plain `dict` — success responses never contain an `error` key; failure responses always do. No business logic lives outside this file — both the FastAPI adapter and MCP server are thin wrappers.

- [ ] **Hard gate: refuse `draft_plan` unless `list_events` was called**
  In `draft_plan`, read `metadata["events_reviewed"]` from the session file. If `False`, return `{"error": "list_events must be called before draft_plan"}` immediately — do not call the orchestrator. This gate must be enforced in `agent/tools.py` only, so both adapters inherit it automatically.

- [ ] **Orchestrator (Bedrock / AgentCore) multi-step loop**
  `agent/orchestrator.py` runs a Bedrock Converse loop capped at 10 iterations. On each `tool_use` response, dispatch to the Tool_Layer function, feed the result back as a `toolResult` message, and continue. On `ThrottlingException` or transient error, retry once after 2 s. If `AGENTCORE_ENABLED=true`, route through `agentcore_client.invoke_agent_runtime()` instead. On reaching 10 iterations without a plan, log termination and return `{"error": "Max iterations reached without producing a plan"}`.

- [ ] **Vision branching: zone density / event mix changes next tool sequence**
  The agent must demonstrably change which tool it calls next based on what the vision data shows. Concretely: if `list_events` returns a high density of press events in a zone, the orchestrator's next call should be `analyze_zone` on that zone rather than jumping straight to `draft_plan`. This branching must appear in `trace.json` as a hypothesis change between steps. It is the core agentic criterion judges will look for.

- [ ] **`request_approval` → status `pending_approval`**
  `request_approval` writes `plan.json` with `status: "pending_approval"` and polls for a coach decision up to `APPROVAL_TIMEOUT_SECONDS`. On approval, return `{"decision": "approved", "reason": ""}`. On rejection with reason, return `{"decision": "revision_required", "reason": "<text>"}`. On timeout, return `{"error": "Approval timeout after <N>s"}`. The plan must never be auto-delivered — the poll must genuinely block.

- [ ] **`trace.json` per run (judge-facing)**
  `agent/trace.py` serialises the full reasoning trace after every run to `data/sessions/{id}/trace.json`. Required fields per tool call: `step`, `tool_name`, `input`, `output_summary`, `hypothesis_before`, `hypothesis_after`. The `hypothesis_before` → `hypothesis_after` delta is the machine-verifiable proof that vision outputs changed agent decisions. Judges will open this file directly.

- [ ] **MCP server wraps the same six tools**
  `mcp/server.py` uses `FastMCP` to register all six tools by importing them directly from `agent/tools`. No logic is copied. Supports `stdio` (default) and `streamable-http` transports via `MCP_TRANSPORT` env var. Running `python mcp/server.py` must start without errors.

- [ ] **`tests/test_agent_trace.py` asserts vision-influenced tool order**
  Beyond checking that `tool_calls` contains the required tool names, the test must assert that the *order* of tool calls reflects the vision output. Specifically: when `list_events` returns press-heavy data, `analyze_zone` must appear in `tool_calls` before `draft_plan`. This is the test-level proof of agentic behaviour — not just that tools were called, but that vision changed the sequence.

---

### Phase C — AWS + Demo (P0)

- [ ] **S3 for video, events, clips, traces**
  Every session asset is uploaded to `S3_BUCKET` under `sessions/{session_id}/`: the source video, each evidence clip, `events.json`, and `trace.json`. Record S3 URLs in the session metadata. On upload failure: log the error, keep the local file, set the S3 URL to `null` — never block the pipeline.

- [ ] **FastAPI: `/analyse`, `/events/{id}`, `/clip/{id}`, `/approve/{id}`, `/session/{id}`**
  All five endpoints implemented in `api/main.py`. `POST /analyse` returns `session_id` within 5 s and continues processing in `BackgroundTasks`. All `GET` endpoints respond within 30 s. HTTP error codes follow the taxonomy in the design doc (400, 404, 409, 422). Pydantic v2 models in `api/schemas.py`.

- [ ] **Deploy API (App Runner or Lambda container)**
  The FastAPI app must be deployable to AWS using only the config in `aws/`. Either: push the Docker image to ECR and deploy via `aws/apprunner.yaml`, or use `aws/lambda_handler.py` (Mangum shim) for Lambda container image. The deployment must produce a live HTTPS endpoint. Document the exact deploy commands in `docs/EVAL.md`.

- [ ] **Minimal UI or scripted demo path**
  Judges must be able to trigger the full pipeline without reading source code. Either: a minimal web UI served from the FastAPI app, or a single shell script `demo.sh` that calls `run_agent.py` with a sample clip, approves the plan via `curl`, and prints the final plan to stdout. The demo path must be documented in `docs/EVAL.md` step by step.

- [ ] **Eval on 2 clips (success + limitation) → `docs/EVAL.md`**
  Run the full pipeline on two distinct clips: one where detection + event detection works well (the "success" demo), and one where it struggles (e.g. low contrast, crowded scene). Document both runs in `docs/EVAL.md` with: event counts, zone assignments, agent hypothesis changes, final plan text, and an honest assessment of what failed and why. Judges value honesty over claimed perfection.

- [ ] **Demo video ≤5 min + architecture diagram**
  Record a screen capture (OBS or similar) of the full pipeline running on the success clip: terminal output of `run_agent.py`, the final approved plan, and `trace.json` opened in an editor. Include a 30-second walkthrough of the Mermaid architecture diagram. Keep the total under 5 minutes. Upload to YouTube (unlisted) or include as a file link in `docs/EVAL.md` and the Devpost submission.

- [ ] **Submit buffer: 24–25 Oct (deadline 26 Oct)**
  All P0 + P1 tasks must be complete and pushed to `master` by end of day 24 Oct. 25 Oct is reserved for Devpost submission form, final README check, demo video upload, and verifying the live API endpoint. Do not start new features after 24 Oct.

---

### Phase D — Stretch (P2, only if A–C green)

- [ ] **NVIDIA VSS: search / retrieve similar sequences**
  Implement `cv/vss_adapter.py` with `query_vss(video_path, prompt) -> dict`. Call the NVIDIA Video Search and Summarisation API to search for clips similar to a detected event. Return results in a schema compatible with the `Event` dataclass so they can be fed back into the agent loop.

- [ ] **Cosmos: confirm/reject on retrieved clips**
  Add a `confirm_with_cosmos(clip_path, hypothesis) -> dict` function to `cv/vss_adapter.py`. Use the NVIDIA Cosmos model to confirm or reject a tactical hypothesis against a retrieved clip. Return `{"confirmed": bool, "reasoning": str}`.

- [ ] **Log VSS/Cosmos steps in the same agent trace**
  Extend `Trace_Logger` to record VSS query steps and Cosmos confirmation steps with the same `step`, `tool_name`, `input`, `output_summary`, `hypothesis_before`, `hypothesis_after` schema. Judges should see a single `trace.json` that shows the full reasoning chain including NVIDIA steps.

- [ ] **Optional VSS evidence step in the agent**
  If P0 works and time remains, let the agent query VSS for similar sequences after OpenCV/YOLO has produced an event or hypothesis. Cosmos may then confirm or reject the retrieved evidence. Keep local OpenCV perception as the primary path and record these optional calls in the same trace.

---

## Definition of Done

Before submitting, every item below must be verifiable by a judge cloning the repo:

- [ ] OpenCV 5 does **real video analysis** — not decorative, not mocked frames
- [ ] AWS hosts storage and/or the API/agent actually used in the demo
- [ ] **Agent loop**: perception → evidence gathering → decision → action or approval
- [ ] **Trace proves vision changed the next step** — `hypothesis_before` ≠ `hypothesis_after` in at least 2 consecutive steps, and the tool called after the change is different from what it would have been without the vision data
- [ ] MCP server exposes the same six core tools (or documented equivalent)
- [ ] Demo path documented + demo video ≤5 min uploaded + known limitations written up
- [ ] Repo runs with `pip install -r requirements.txt` + `.env` config — no weights or videos committed
- [ ] `pytest tests/` passes with no live AWS credentials

---

## Explicit Non-Goals

The following are explicitly **out of scope**:

1. **Multi-camera production analytics** — single clip per session, no camera sync
2. **Chatbot-only Q&A on frozen frames** — real CV on real video only
3. **Real-time streaming** — pre-recorded footage only
4. **Full 90-minute match processing** — short analysis clips only
5. **Player biometric identification** — bounding box + team colour only
6. **Automated production deployment** — `aws/` config is for reference; production ops are the operator's responsibility
