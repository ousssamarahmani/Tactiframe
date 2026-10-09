# Requirements Document

## Introduction

TactiFrame is an Agentic Vision system for football (soccer) opposition analysis targeting the OpenCV AI Competition 2026 (Agentic Vision track with AWS). The system converts match video footage into evidence-backed tactical intelligence by following a four-phase pipeline: SEE (OpenCV 5 perception) → UNDERSTAND (structured events) → DECIDE (agent tools with a reasoning loop) → ACT / COACH APPROVAL. TactiFrame is designed as a GitHub-ready hackathon entry with a clean, reproducible repository structure, real video analysis, and AWS-backed deployment.

The system is NOT a full multi-camera production analytics suite, NOT a chatbot-only Q&A on frozen frames, and NVIDIA VSS / Cosmos are stretch goals pursued only after P0 is complete.

---

## Glossary

- **TactiFrame**: The product name used in all user-facing content; the system built for this hackathon entry.
- **Perception_Engine**: The OpenCV 5–based computer vision module in `cv/` that ingests video and produces detections, tracks, zone assignments, events, and evidence clips.
- **Event_Detector**: The component in `cv/event_detector.py` that converts frame-level tracks into discrete football events (pass, shot, press, etc.).
- **Zone_Analyzer**: The component in `cv/zones.py` that maps player positions to pitch zones and computes zone-level statistics.
- **Tool_Layer**: The single implementation in `agent/tools.py` that exposes `run_perception`, `list_events`, `get_clip`, `analyze_zone`, `draft_plan`, and `request_approval`.
- **Agent_Orchestrator**: The reasoning loop in `agent/orchestrator.py` that calls Tool_Layer functions via Amazon Bedrock (AgentCore) to form hypotheses, gather evidence, and produce tactical plans.
- **Trace_Logger**: The component in `agent/trace.py` that records each reasoning step, tool call, and evidence reference so judges can verify that vision outputs changed agent decisions.
- **MCP_Server**: The Model Context Protocol server in `mcp/server.py` that wraps the same Tool_Layer functions, providing a second adapter with no duplicated logic.
- **Approval_Gate**: The mandatory human-in-the-loop step enforced by `request_approval` that blocks any tactical plan from being delivered without explicit coach sign-off.
- **Coach**: The human user (football analyst or head coach) who reviews and approves or rejects tactical plans produced by the Agent_Orchestrator.
- **Evidence_Clip**: A short video segment extracted from the source footage that supports a specific detected event or tactical finding.
- **S3_Store**: The AWS S3 bucket used to store uploaded match videos, evidence clips, and serialized event data.
- **API**: The FastAPI application in `api/main.py` that exposes HTTP endpoints for triggering the pipeline and querying results.
- **Pitch_Zone**: One of the defined regions on the football pitch (e.g., left flank, central midfield block, penalty area) used by the Zone_Analyzer.
- **ByteTrack**: The multi-object tracking algorithm used to assign persistent IDs to players across frames.
- **YOLO**: The object detection model used to detect players and the ball in individual frames.
- **Bedrock**: Amazon Bedrock, the AWS-managed LLM service used to power the Agent_Orchestrator's reasoning.
- **AgentCore**: Amazon Bedrock AgentCore, the managed agent execution environment (used where available).

---

## Requirements

### Requirement 1: OpenCV 5 Perception Pipeline

**User Story:** As a football analyst, I want TactiFrame to analyse a match video clip using real computer vision, so that I receive structured, evidence-backed perception outputs rather than placeholder data.

#### Acceptance Criteria

1. WHEN a valid match video file is provided, THE Perception_Engine SHALL detect all visible players and the ball in each frame using YOLO with a minimum confidence threshold of 0.5.
2. WHEN detections are produced, THE Perception_Engine SHALL assign persistent player IDs across frames using ByteTrack.
3. WHEN player tracks are available, THE Perception_Engine SHALL assign each player track to a Pitch_Zone at each frame using the Zone_Analyzer.
4. WHEN player tracks and Pitch_Zone assignments are available, THE Event_Detector SHALL identify discrete football events (pass, shot, cross, press, set piece) with a timestamp expressed as elapsed seconds from video start rounded to two decimal places, and the player IDs involved.
5. WHEN an event at timestamp `t` is identified, THE Perception_Engine SHALL extract a short Evidence_Clip from the source video spanning from `max(0, t−2s)` to `min(video_duration, t+2s)`.
6. WHEN the pipeline completes processing a video, THE Perception_Engine SHALL write all detections, tracks, zone assignments, events, and Evidence_Clip file paths to a session-scoped structured JSON output file, ensuring separate sessions do not overwrite each other.
7. IF the provided video file does not exist or cannot be decoded, THEN THE Perception_Engine SHALL raise an error whose message indicates the file path and the failure reason, and halt processing.
8. IF YOLO model weights are not found at the configured path, THEN THE Perception_Engine SHALL raise an error whose message indicates the expected model weight path, and halt processing.

---

### Requirement 2: Zone Analysis

**User Story:** As a football analyst, I want to query the zone-level activity of specific teams or time windows, so that I can identify tactical patterns like overloads, wide play prevalence, and defensive shape.

#### Acceptance Criteria

1. THE Zone_Analyzer SHALL divide the pitch into a configurable grid of between 6 and 64 Pitch_Zones, where the grid dimensions are set at configuration time before any video is processed.
2. WHEN player tracks are provided, THE Zone_Analyzer SHALL compute, for each Pitch_Zone, the count of player occupancy frames per team per time window, where a time window is a contiguous frame interval of between 1 second and the full match duration.
3. WHEN `analyze_zone` is called with a zone identifier, THE Tool_Layer SHALL return zone statistics including occupancy counts per team, the dominant team (defined as the team with the highest occupancy frame count in the requested window), and the timestamps of the top 3 frames with the highest single-team occupancy count.
4. IF an unrecognised zone identifier is provided to `analyze_zone`, THEN THE Tool_Layer SHALL return a structured error response that identifies the invalid zone and lists all valid zone identifiers, without modifying any existing zone data.

---

### Requirement 3: Tool Layer Contract

**User Story:** As an engineer integrating TactiFrame with an agent framework or MCP client, I want a single, stable tool contract, so that I do not need to duplicate business logic across adapters.

#### Acceptance Criteria

1. THE Tool_Layer SHALL implement exactly the following six tools in `agent/tools.py`: `run_perception`, `list_events`, `get_clip`, `analyze_zone`, `draft_plan`, `request_approval`.
2. WHEN `run_perception` is called with a video file path, THE Tool_Layer SHALL invoke the Perception_Engine and return a session ID referencing the stored outputs. IF the video file path does not exist or the Perception_Engine fails, THE Tool_Layer SHALL return a structured error response containing an `error` field with the failure reason.
3. WHEN `list_events` is called with a valid session ID, THE Tool_Layer SHALL return all events detected in that session, each with a type, timestamp, player IDs, and Evidence_Clip path. IF the session ID does not exist, THE Tool_Layer SHALL return a structured error response containing an `error` field identifying the unknown session.
4. WHEN `get_clip` is called with a valid event ID, THE Tool_Layer SHALL return the local file path and the S3_Store URL of the corresponding Evidence_Clip. IF the event ID does not exist, THE Tool_Layer SHALL return a structured error response containing an `error` field identifying the unknown event.
5. WHEN `analyze_zone` is called with a valid session ID and zone identifier, THE Tool_Layer SHALL return zone statistics as defined in Requirement 2, Criterion 3.
6. WHEN `draft_plan` is called and `list_events` has NOT been called for the current session, THE Tool_Layer SHALL refuse the request and return a structured error response containing an `error` field stating that evidence review is required before drafting.
7. WHEN `draft_plan` is called and `list_events` HAS been called for the current session, THE Tool_Layer SHALL invoke the Agent_Orchestrator to produce a tactical plan referencing at least one detected event as evidence.
8. WHEN `request_approval` is called, THE Tool_Layer SHALL present the drafted plan to the Coach and block until an explicit approval or rejection response is received, such that `plan_presented_to_coach` and `blocked_until_response` hold in all execution paths including timeout. IF no response is received within a configurable timeout, THE Tool_Layer SHALL return a structured error response containing an `error` field indicating the timeout.
9. IF `request_approval` receives a rejection, THEN THE Tool_Layer SHALL return the rejection reason to the Agent_Orchestrator for plan revision. IF no reason is provided with the rejection, THE Tool_Layer SHALL return an empty string as the rejection reason.
10. THE Tool_Layer SHALL expose all six tools through the MCP_Server in `mcp/server.py` by importing and wrapping them, with no duplicated business logic.

---

### Requirement 4: Agentic Investigation Loop

**User Story:** As a judge evaluating the Agentic Vision track, I want to see that the agent autonomously forms hypotheses, searches for evidence, and refines its analysis based on vision outputs, so that I can confirm TactiFrame qualifies as an agentic system rather than a static pipeline.

#### Acceptance Criteria

1. WHEN a tactical analysis request is received, THE Agent_Orchestrator SHALL execute a multi-step reasoning loop comprising hypothesis formation, tool invocation, evidence evaluation, and plan refinement, terminating no later than after 10 reasoning iterations.
2. WHEN the Agent_Orchestrator invokes a tool, THE Trace_Logger SHALL record the step number, tool name, input arguments, and output summary.
3. WHEN a tool output causes the Agent_Orchestrator to update its current hypothesis, THE Trace_Logger SHALL record the prior hypothesis text, the event ID or tool output that triggered the change, and the updated hypothesis text.
4. THE Agent_Orchestrator SHALL call `list_events` before calling `draft_plan` in every session, enforcing the evidence-first constraint.
5. WHEN `draft_plan` returns a tactical plan, THE Agent_Orchestrator SHALL call `request_approval` and wait for the Coach's decision before terminating the session.
6. WHEN a session ends, THE Trace_Logger SHALL serialise the full reasoning trace to a JSON file referencing all tool calls, evidence clips, and plan versions.
7. IF Bedrock returns an error during any reasoning step, THEN THE Agent_Orchestrator SHALL log the error in the trace and retry the step once before returning a failure response to the caller.
8. WHEN the Agent_Orchestrator reaches the maximum iteration limit of 10 without producing a final plan, THE Agent_Orchestrator SHALL log a termination reason in the trace and return a structured error response to the caller. IF the Agent_Orchestrator produces a final plan on the 10th (final) iteration, THEN THE Agent_Orchestrator SHALL treat this as success, proceed with the approval flow, and SHALL NOT return a structured error response.

---

### Requirement 5: AWS Integration

**User Story:** As a judge evaluating AWS usage, I want TactiFrame to use AWS for a meaningful component of the system, so that I can confirm the entry meets the AWS track requirement.

#### Acceptance Criteria

1. WHEN a match video is submitted for analysis, THE API SHALL upload the video file to S3_Store under a prefix containing the session identifier, such that no two concurrent sessions share the same prefix.
2. WHEN Evidence_Clips are extracted, THE Perception_Engine SHALL upload each Evidence_Clip to S3_Store and record the resulting S3 URL in the event record.
3. WHEN a tactical analysis request is received, THE Agent_Orchestrator SHALL invoke reasoning through Amazon Bedrock using a configured foundation model and SHALL receive a response from Bedrock before returning results to the caller.
4. WHERE Amazon Bedrock AgentCore is available, THE Agent_Orchestrator SHALL route tool calls through AgentCore rather than executing them directly.
5. THE API SHALL be deployable to AWS App Runner or as a Lambda container image using only the configuration in `aws/`, such that the deployment produces a running service endpoint.
6. IF an S3 upload fails, THEN THE Perception_Engine SHALL log the error, retain the local Evidence_Clip file, and record a null S3 URL in the event record.
7. IF Bedrock invocation fails during a reasoning step, THEN THE Agent_Orchestrator SHALL return an error response to the caller without returning partial or undefined results.

---

### Requirement 6: MCP Server

**User Story:** As an MCP client developer, I want TactiFrame to expose its tools via a Model Context Protocol server, so that I can integrate TactiFrame's capabilities into any MCP-compatible agent without writing custom adapters.

#### Acceptance Criteria

1. WHEN `mcp/server.py` is executed, THE MCP_Server SHALL start, bind to a configured host and port, and accept incoming MCP client connections over stdio or HTTP/SSE transport.
2. WHEN an MCP client requests the tool list, THE MCP_Server SHALL advertise the same six tool names as the Tool_Layer with input and output schemas that are byte-for-byte identical to those in `agent/tools.py`.
3. WHEN an MCP client calls any of the six tools, THE MCP_Server SHALL delegate execution to the corresponding function in `agent/tools.py` and return the result to the client unchanged.
4. WHEN an MCP client calls any of the six tools and the Tool_Layer returns a structured error response, THE MCP_Server SHALL return that error response to the client without modification.
5. THE MCP_Server SHALL enforce the `draft_plan` gate defined in Requirement 3, Criterion 6, because the gate is implemented in `agent/tools.py` and delegation preserves it automatically.

---

### Requirement 7: FastAPI HTTP Interface

**User Story:** As an operator deploying TactiFrame on AWS, I want an HTTP API to trigger the pipeline and retrieve results, so that I can integrate TactiFrame with external dashboards or CI evaluation scripts.

#### Acceptance Criteria

1. THE API SHALL expose a `POST /analyse` endpoint that accepts a video file path (up to 1024 characters) or S3 URI and returns a session ID.
2. THE API SHALL expose a `GET /events/{session_id}` endpoint that returns all events for a session.
3. THE API SHALL expose a `GET /clip/{event_id}` endpoint that returns the Evidence_Clip file path and S3 URL.
4. THE API SHALL expose a `POST /approve/{session_id}` endpoint whose request body explicitly specifies either an approval or a rejection decision, and optionally a reason string, for the pending plan.
5. WHEN a request is received, THE API SHALL respond within 30 seconds for `GET /events/{session_id}`, `GET /clip/{event_id}`, and `POST /approve/{session_id}`. THE `POST /analyse` endpoint SHALL return a session ID within 5 seconds and continue processing asynchronously.
6. IF a requested session ID does not exist, THEN THE API SHALL return HTTP 404 with an error message indicating the session was not found.
7. IF a request body fails schema validation, THEN THE API SHALL return HTTP 422 with field-level error details.
8. IF a requested event ID does not exist on `GET /clip/{event_id}`, THEN THE API SHALL return HTTP 404 with an error message indicating the event was not found.
9. IF the input to `POST /analyse` is a file path that does not exist or is not accessible, THEN THE API SHALL return HTTP 400 with an error message indicating the invalid input, and SHALL NOT create a session.
10. IF `POST /approve/{session_id}` is called and no pending plan exists for that session, THEN THE API SHALL return HTTP 409 with an error message indicating there is no pending plan awaiting approval.

---

### Requirement 8: Approval Gate

**User Story:** As a football coach, I want every tactical plan to require my explicit approval before it is delivered, so that no automated recommendation reaches my staff without my review.

#### Acceptance Criteria

1. WHEN a tactical plan is ready, THE Approval_Gate SHALL set the plan status to `pending_approval` and SHALL return a response indicating the plan is pending approval to any caller that requests it before an explicit Coach decision is recorded.
2. WHEN a session has a plan with status `pending_approval`, THE API SHALL return the plan content and the status `pending_approval` in the session response.
3. WHEN the Coach records an approval decision, THE Approval_Gate SHALL set the plan status to `approved` and make the plan content accessible to callers.
4. WHEN the Coach records a rejection decision with a reason, THE Approval_Gate SHALL set the plan status to `revision_required` and pass the reason text to the Agent_Orchestrator for plan revision.
5. THE Trace_Logger SHALL record the approval decision value (`approved` or `revision_required`), the Coach-provided reason string (or an empty string if none was provided for approvals or rejections without a reason), and the UTC timestamp of the decision in the session trace.
6. IF an approval or rejection request is made for a session that does not exist or whose plan is not in `pending_approval` status, THEN THE Approval_Gate SHALL return a structured error response indicating the session was not found or the plan is not awaiting approval.

---

### Requirement 9: Repository Hygiene and Documentation

**User Story:** As a hackathon judge reviewing the GitHub repository, I want a clean, professional repo structure with accurate documentation, so that I can evaluate the project quickly and fairly.

#### Acceptance Criteria

1. THE repository SHALL contain a `README.md` with: a one-liner description of TactiFrame, a Mermaid architecture diagram, a quickstart section, a demo flow section, a "How this meets Agentic Vision" section with a trace example, and an explicit non-goals section.
2. THE repository SHALL contain a `requirements.txt` with pinned versions for all direct runtime dependencies including OpenCV 5, YOLO, ByteTrack, FastAPI, Boto3, and the MCP SDK.
3. THE repository SHALL contain a `.gitignore` that excludes `data/`, `models/`, `.env`, `__pycache__`, and AWS credential files.
4. THE repository SHALL contain an `MIT LICENSE` file.
5. THE repository SHALL contain `docs/HACKATHON.md` describing the competition context, priority order (P0/P1/P2), and explicit non-goals.
6. THE repository SHALL contain `docs/ARCHITECTURE.md` with a written description of all components and their interactions.
7. THE repository SHALL contain `docs/EVAL.md` describing evaluation criteria, known limitations, and instructions for reproducing the demo that include environment setup steps, the exact commands to run, and the expected observable output.
8. THE repository SHALL NOT contain match video files, raw binary model weight files (`.pt`, `.onnx`, `.pth`, `.weights`) committed directly to the git tree, or AWS credential files. Git LFS pointers or external storage references to model weight files are acceptable and do not constitute a violation of this criterion.
9. THE repository SHALL use the product name TactiFrame in all user-facing content (README, `docs/` files, and UI-rendered strings) and SHALL NOT reference TactiScout as the product name.
10. THE repository SHALL NOT contain any references to Google Cloud services.

---

### Requirement 10: Test Coverage for Agent Trace

**User Story:** As a developer maintaining TactiFrame, I want automated tests for the agent trace, so that I can verify the reasoning loop produces a valid, evidence-linked trace on every run.

#### Acceptance Criteria

1. WHEN the full agent loop completes on a synthetic video of no more than 30 frames, THE test suite in `tests/test_agent_trace.py` SHALL assert that the output trace JSON contains a `tool_calls` array with at least one entry whose `tool_name` field equals each of `run_perception`, `list_events`, and `draft_plan`.
2. WHEN the agent loop completes, THE test SHALL assert that every entry in `tool_calls` whose `tool_name` is `draft_plan` contains an `event_ids` field that references at least one `event_id` value present in a prior `list_events` `tool_calls` entry.
3. IF `draft_plan` is called without a prior `list_events` call in the same session, THEN THE test SHALL assert that the Tool_Layer returns a response containing an `error` field and that the Agent_Orchestrator's invoke method is called zero times.
4. THE test suite SHALL be executable with `pytest tests/` and SHALL NOT require live AWS credentials or real match video files to pass.

---

### Requirement 11: Entry-Point Scripts

**User Story:** As a developer evaluating TactiFrame locally, I want simple command-line entry points for the pipeline and the agent, so that I can reproduce the demo without reading through all module internals.

#### Acceptance Criteria

1. WHEN `run_pipeline.py` is executed with a valid video file path argument, THE script SHALL invoke the Perception_Engine, print a summary to stdout that includes at minimum the total event count, each event type detected, and the timestamp of each event, and exit with code 0.
2. WHEN `run_agent.py` is executed with a valid video file path argument, THE script SHALL invoke the full agent loop including the Approval_Gate, print the final approved plan text or the rejection reason to stdout, and exit with code 0.
3. WHEN `run_pipeline.py` is executed without required arguments, THE script SHALL print usage instructions that identify the required argument name and its expected value type, and exit with a non-zero code.
4. WHEN `run_agent.py` is executed without required arguments, THE script SHALL print usage instructions that identify the required argument name and its expected value type, and exit with a non-zero code.
5. IF `run_pipeline.py` or `run_agent.py` is executed with a video file path that does not exist or cannot be read, THEN THE script SHALL print an error message indicating the invalid path, exit with a non-zero code, and SHALL NOT invoke the Perception_Engine or Agent_Orchestrator.
