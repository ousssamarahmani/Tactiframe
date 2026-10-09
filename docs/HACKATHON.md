# TactiFrame — Hackathon Context

## Competition

**Event:** OpenCV AI Competition 2026
**Track:** Agentic Vision (with AWS)
**Entry:** TactiFrame — Agentic Vision System for Football Opposition Analysis

---

## Priority Order

| Priority | Scope | Status |
|---|---|---|
| **P0** | cv/ perception pipeline, agent/ layer, api/, AWS S3/Bedrock integration, tests/, repo hygiene | Must ship |
| **P1** | mcp/server.py, UI polish | Should ship |
| **P2** | NVIDIA VSS / Cosmos integration | Stretch — only after P0 verified complete |

### P0 — Must Ship

- `cv/` perception pipeline: YOLO detection, ByteTrack tracking, Zone_Analyzer, Event_Detector, evidence clip extraction
- `agent/` layer: Tool_Layer (6 tools), Agent_Orchestrator (Bedrock Converse loop), Trace_Logger, Approval_Gate
- `api/` FastAPI HTTP interface: all 5 endpoints, coach approval flow
- AWS integration: S3 for video + clip storage, Amazon Bedrock for reasoning
- `tests/` suite: property-based tests (Hypothesis), example-based tests, no live AWS credentials required
- Repository hygiene: README, LICENSE, .gitignore, docs/, requirements.txt

### P1 — Should Ship

- `mcp/server.py`: MCP_Server wrapping all six Tool_Layer functions over stdio or HTTP/SSE transport
- UI polish: improved README formatting, demo GIFs

### P2 — Stretch (only after P0 complete)

- NVIDIA VSS / Cosmos integration via `cv/vss_adapter.py`
- `--use-vss` flag on `run_pipeline.py`

---

## Explicit Non-Goals

The following are explicitly **out of scope** for this hackathon entry:

1. **Multi-camera production analytics** — TactiFrame processes a single video clip per session. No camera synchronisation, no broadcast-grade multi-feed ingestion.
2. **Chatbot-only Q&A on frozen frames** — TactiFrame is an agentic pipeline, not a chatbot. It runs real computer vision on real video and produces evidence-backed tactical plans.
3. **Real-time streaming** — The pipeline processes pre-recorded footage. Live video ingest is not in scope.
4. **Full match (90+ minute) processing** — Demo clips are short segments. Long-form processing is not optimised or tested.
5. **Player identification by face or biometric** — Players are tracked by bounding box and team colour classification only.
6. **Automated deployment to production** — AWS configuration files are provided for reference; production deployment is the operator's responsibility.
