# TactiFrame — Evaluation Guide

## Evaluation Criteria

| Criterion | How TactiFrame addresses it |
|---|---|
| Real computer vision | OpenCV 5 + YOLO detects players and ball; ByteTrack assigns persistent IDs; Zone_Analyzer maps positions to pitch zones |
| Agentic behaviour | Agent_Orchestrator runs a multi-step Bedrock Converse loop: hypothesis → tool call → evidence evaluation → refinement (up to 10 iterations) |
| AWS integration | S3 for video + clip storage; Amazon Bedrock for reasoning; optional AgentCore routing |
| Evidence-backed output | Every tactical plan references at least one detected event; evidence clips are linked in the trace |
| Human-in-the-loop | Approval_Gate requires explicit coach sign-off before any plan is delivered |
| Reproducibility | No live AWS credentials required for tests; synthetic video fixture; moto for S3; mock.patch for Bedrock |

---

## Known Limitations

- **Heuristic event detection** — Event_Detector uses geometry and motion heuristics rather than a trained classifier. False positives are expected on unusual footage.
- **Single-camera input** — No multi-feed synchronisation. One video clip per session.
- **Short clips only** — Tested on clips up to ~5 minutes. Long-form (90-minute) processing is not optimised.
- **YOLO confidence threshold** — Fixed at 0.5. Dense scenes with occlusions may produce missed detections.
- **AgentCore optional** — AgentCore routing is tested against the mock only; a live AgentCore runtime is required for full end-to-end validation.

---

## Reproducing the Demo

### 1. Environment Setup

```bash
# Clone the repository
git clone https://github.com/<your-org>/tactiframe.git
cd tactiframe

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy the environment template and fill in your values
cp .env.example .env
# Edit .env: set S3_BUCKET, BEDROCK_MODEL_ID, AWS_REGION
```

### 2. Download Model Weights

TactiFrame uses a YOLO model. Weights are not committed to the repository (see `.gitignore`).

```bash
# Download YOLOv8n weights (example — use the model appropriate for your setup)
mkdir -p models
wget -O models/yolo.pt https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt
```

Set `YOLO_WEIGHTS_PATH=models/yolo.pt` in `.env` (or `config.py`).

### 3. Run the Perception Pipeline

```bash
python run_pipeline.py --video /path/to/clip.mp4
```

**Expected output:**
```
[TactiFrame] Processing video: /path/to/clip.mp4
[TactiFrame] Session ID: 3f2a1b9c-...
[TactiFrame] Events detected: 7
  - pass     @ 4.12s
  - press    @ 8.75s
  - shot     @ 14.33s
  - cross    @ 19.01s
  - pass     @ 22.50s
  - set_piece @ 28.90s
  - pass     @ 35.14s
[TactiFrame] Done. Session data: data/sessions/3f2a1b9c-...
```

### 4. Run the Full Agent Loop

```bash
python run_agent.py --video /path/to/clip.mp4
```

**Expected output:**
```
[TactiFrame] Starting agent loop...
[TactiFrame] Session: 3f2a1b9c-...
[TactiFrame] Iteration 1: run_perception
[TactiFrame] Iteration 2: list_events (7 events found)
[TactiFrame] Iteration 3: analyze_zone (zone Z05 — dominant: team_a)
[TactiFrame] Iteration 4: draft_plan
[TactiFrame] Plan pending approval...
[TactiFrame] (Awaiting coach decision — use POST /approve/<session_id> or press Enter to auto-approve in demo mode)
[TactiFrame] Plan APPROVED.

=== Tactical Plan ===
Opponent team_b is overloading the left flank (zone Z02) in the first 15 seconds.
Recommend shifting the defensive block right and pressing higher in Z05.
Evidence: events [evt-001 (press@8.75s), evt-003 (shot@14.33s)]
```

### 5. Run All Tests (no AWS credentials required)

```bash
pytest tests/ -v
```

**Expected output:**
```
tests/test_agent_trace.py::test_tool_calls_contain_required_tools PASSED
tests/test_agent_trace.py::test_draft_plan_event_ids_subset_of_list_events PASSED
tests/test_agent_trace.py::test_draft_plan_without_list_events_returns_error PASSED
tests/test_cv_properties.py::test_detection_confidence_threshold PASSED
...
XX passed in X.XXs
```

### 6. Start the API Server

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

Then call the API:

```bash
# Submit a video for analysis
curl -X POST http://localhost:8000/analyse \
  -H "Content-Type: application/json" \
  -d '{"video_path": "/path/to/clip.mp4"}'

# Retrieve events
curl http://localhost:8000/events/<session_id>

# Approve a plan
curl -X POST http://localhost:8000/approve/<session_id> \
  -H "Content-Type: application/json" \
  -d '{"decision": "approved", "reason": ""}'
```
