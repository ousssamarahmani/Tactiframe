# TactiFrame product vision and implementation backlog

## Product position

**TactiFrame is an Agentic Vision engine for football intelligence.** It is not a complete football-intelligence platform and it is not merely a computer-vision module. It turns football video into evidence, lets agents investigate that evidence, and keeps a coach in control of consequential recommendations.

```text
Football video / camera feeds
  → Commercial CV module
  → TactiFrame Vision Engine
  → TactiFrame Agentic Vision
  → Football solution agents and coach workflows
```

The Mazzulla reference is workflow inspiration only: prepare, observe, compare evidence, and adapt. It is not an endorsement, partnership, or product claim.

## Product layers

| Layer | Responsibility | Status |
|---|---|---|
| Commercial CV module | Detection, tracking, ball candidates, team labels, pitch calibration, and later multi-camera association | Single-camera baseline in progress; not commercially validated |
| TactiFrame Vision Engine | Converts CV outputs into session artifacts, zones, candidate events, clips, heatmaps, matrices, and quality metadata | Sessions, candidate events, clips, and quality reports exist; heatmaps and matrices are next |
| TactiFrame Agentic Vision | Video Analyst, Vision Agent, Tactical Analyst, evidence-bound chat, trace, and coach approval | Tool loop, trace, proposal, approval, evidence-bound chat, and deterministic local specialist simulation exist; model-driven and distributed agents are later |
| Football solution agents | Opposition Analyst, Performance Analyst, Match Room Agent, Match Analyst | Planned; they consume evidence and must not invent visual facts |

## Agent responsibilities

```text
Video Analyst Agent
  → validates footage, camera cuts, pitch calibration, evidence availability

Vision Agent
  → detects players/ball/team candidates, tracks movement, reports quality limits

Tactical Analyst Agent
  → investigates zones, shapes, density, pressure candidates, clips, heatmaps, matrices

Product-level agents
  → Opposition / Performance / Match Room / Match Analyst
  → consume evidence objects and produce role-specific, coach-reviewable findings
```

An agent must cite session IDs, event IDs, artifact IDs, and evidence clips for every video-derived tactical claim. When evidence is missing or unverified, it must say so and stop rather than fabricate an answer.

## Current task list — source of truth

This is the maintained checklist after the first local MVP foundation. The historical hackathon checklist is not the current implementation status.

### Completed foundation

- [x] Pitch-aware OpenCV 5 observation worker with football YOLO, ByteTrack, team candidates, ball candidates, run metadata, and annotated video.
- [x] Candidate events, image-relative zones, evidence clips, and explicit event-confidence/limitation fields.
- [x] Six-agent-tool contract, vision-dependent tool ordering, `trace.json`, and named coach approval gate.
- [x] Private S3 artifact sync and Bedrock evidence-bound coach-review proposal path, with local fallback.
- [x] FastAPI session, event, trace, plan, and approval endpoints plus scripted demo flow.
- [x] Session evaluation harness, ball-candidate validation, track diagnostics, and deterministic simulation tests.
- [x] Controlled A/B runner and comparator for one-setting tracking experiments.

### In progress — current CV gate

- [ ] Run the 5-second versus 8-second lost-track-buffer A/B session locally; inspect its annotated video and `tracking_ab_comparison.json` before accepting or rejecting the setting.

### Completed — Agentic Vision evidence artifacts v1

- [x] Generate overall and per-team candidate heatmaps from session tracks.
- [x] Generate 3×3 zone occupancy matrices with counts, normalized values, coordinate-system metadata, and limitations.
- [x] Generate candidate team-shape snapshots from track positions.
- [x] Store every artifact under the session with source counts, parameters, and a reproducible schema.
- [x] Add deterministic synthetic-track tests with known heatmap and matrix outputs.
- [x] Add evaluation-harness checks for artifact availability and schema validity.

These are JSON evidence artifacts for tool use and API delivery. They are candidate/unverified and image-relative; a visual workspace renderer and calibrated pitch views are later work.

### In progress — Agentic Vision chat and simulation

- [x] Add evidence-artifact, annotated-video, and selected-clip API endpoints by session ID.
- [x] Add API-only evidence-bound Agent Vision Chat: a question triggers tools and returns event IDs, artifact references, browser-safe clip URLs, limitations, and trace steps.
- [ ] Add the chat panel to the local Evidence Viewer after the API contract is tested on more sessions.
- [x] Simulate Video Analyst, Vision Agent, and Tactical Analyst roles in one local process before any distributed deployment.
- [x] Run the chat and specialist simulations against fixed/synthetic sessions before enabling model-driven specialist prompts.
- [x] Test no-evidence, missing-clip, density-first, contest-first, heatmap, and matrix question scenarios.
- [x] Enforce that chat cannot draft a plan or imply approval without the existing evidence and human gate.

### Later — production and advanced intelligence

- [ ] Async EC2 GPU worker, S3-backed jobs, authenticated FastAPI, monitoring, retention, and cost controls.
- [ ] Bedrock AgentCore deployment for the lead agent after specialist-agent contracts are stable.
- [ ] MCP wrapper for the stable evidence tools; A2A only after agents are independent services.
- [ ] Labeled evaluation for calibrated pitch coordinates, team identity, ball/possession/pass candidates, pressure, compactness, and shape analytics.
- [ ] Multi-camera synchronization and cross-camera association with labeled evaluation.
- [ ] Evidence graph/RAG, NVIDIA VSS/Cosmos evaluation, and private club pilots with written footage/data agreements.

## Implementation plan

### Milestone 1 — measured single-camera Agentic Vision

1. **Complete the controlled tracking A/B run.** Compare the 5-second and 8-second lost-track-buffer sessions with `evaluation.json`, `track_diagnostics.json`, and annotated-video review. Do not accept a setting without reviewing the same labeled player passages.
2. **Generate evidence artifacts.** Produce deterministic candidate heatmaps, zone occupancy matrices, team-shape snapshots, and artifact metadata from tracks. Every artifact must carry its coordinate system and limitations.
3. **Create an evidence API.** Serve events, clips, heatmaps, matrices, trace, plan, and quality data by session ID.
4. **Build evidence-bound Agent Vision Chat.** A coach question must invoke tools, return clip/event/artifact references, update the trace, and refuse unsupported claims.
5. **Simulate and test the agents.** Use deterministic sessions for missing evidence, no events, density-first, contest-first, and known heatmap/matrix expectations.

### Milestone 2 — deployable MVP

1. Run OpenCV and football model inference asynchronously on an EC2 GPU worker with private S3 session storage.
2. Keep FastAPI as the product boundary; add jobs, session status, authentication, structured logs, and retention controls.
3. Deploy the lead orchestration agent to Bedrock AgentCore only after the local specialist-agent contract is stable.
4. Add observability, evaluation datasets, cost limits, retry policies, and human-approval audit records.
5. Build a minimal evidence-review workspace only after the API and chat contract are tested.

### Milestone 3 — advanced Vision Engine

1. Add calibrated pitch coordinates, reliable team identity, ball validation, possession/pass candidates, pressure, compactness, and team-shape analytics.
2. Add multi-camera synchronization and cross-camera association as a dedicated CV problem with labeled evaluation; do not treat it as an extension of single-camera IDs.
3. Add a session evidence graph:

```text
session → camera → track → event → zone → clip → artifact → finding → plan → coach decision
```

4. Build retrieval over that graph for evidence-grounded memory across sessions.
5. Evaluate NVIDIA VSS/Cosmos only as an optional retrieval, embedding, or visual-verification layer on top of proven local evidence contracts.

## Protocol and deployment boundaries

- **MCP:** agent-to-tool contract. TactiFrame tools remain the source of truth.
- **A2A:** agent-to-agent communication only after Video Analyst, Vision Agent, and Tactical Analyst are independently deployable services. Do not introduce A2A to simulate multi-agent behavior inside one process.
- **AgentCore:** managed runtime for the lead agent, session orchestration, policy, and observability—not the GPU video worker.
- **EC2 GPU:** first production target for OpenCV, detector, tracker, and batch video processing.
- **SageMaker:** later option for managed training, model registry, and asynchronous inference; Studio is development tooling, not the production worker.
- **NVIDIA VSS/Cosmos:** later GPU platform evaluation; it must not replace the core OpenCV evidence path.

## Testing and simulation strategy

1. Unit tests for geometry, tracking invariants, ball validation, event schemas, artifact generation, and tool gates.
2. Synthetic sessions with expected agent tool order and expected heatmap/matrix values.
3. Fixed, rights-cleared clips for repeatable A/B CV evaluation.
4. Labeled continuous player passages and ball-visible frames before reporting identity or ball accuracy.
5. Human analyst review with a rubric: evidence relevance, false findings, missing findings, clip usefulness, and approval quality.

## Club-pilot path

Start with a narrow, private evaluation rather than a broad platform promise. A pilot should define the selected workflow, rights to the footage, retention period, approved users, success measures, and whether data may be used for model improvement. Potential pilots in Europe, Canada, or Tunisia should use synthetic or expressly cleared footage until those agreements exist.

## Explicit non-goals for the first MVP

- No unsupported chat-only tactical conclusions.
- No claim of universal all-league or all-camera accuracy.
- No automatic coach approval or autonomous tactical action.
- No multi-camera production claim before synchronization and identity evaluation exist.
- No NVIDIA, A2A, or RAG integration merely for architecture complexity.
