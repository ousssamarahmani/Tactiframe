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
| TactiFrame Agentic Vision | Video Analyst, Vision Agent, Tactical Analyst, evidence-bound chat, trace, and coach approval | Tool loop, trace, proposal, and approval exist; specialist-agent split and chat are planned |
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
