# TactiFrame local agent loop (P0 in progress)

`agent/tools.py` owns the six tools: `run_perception`, `list_events`, `get_clip`, `analyze_zone`, `draft_plan`, and `request_approval`. `draft_plan` refuses to run until `list_events` was called in the same agent session. The orchestrator in `agent/orchestrator.py` reads visual event counts and changes its next tool: contest-heavy evidence triggers `get_clip` first; density-heavy evidence triggers `analyze_zone` first. It then checks the other view of the selected evidence, drafts a provisional plan, and requests coach approval. Every tool call and choice is written to `trace.json`.

The local A/B test shows the change on real OpenCV 5 outputs from the same clip:

| Run | Visual candidates | Next tool after `list_events` | Approval |
|---|---|---|---|
| Baseline | 19 density, 19 contest | `get_clip` | Pending |
| Manual field polygon | 18 density, 17 contest | `analyze_zone` | Pending |

The polygon run's trace is under `data/sessions/match-20261011-local-150s-polygon/trace.json`. Its plan is `plan.json`; no coach decision was inserted automatically. The source footage and all local run outputs remain simulation and education material only.

Run on existing observations:

```powershell
.\.venv\Scripts\python run_agent.py --run-dir data\sessions\your-run-id
```

Or run OpenCV/YOLO perception, candidate event export, and the agent in one command:

```powershell
.\.venv\Scripts\python run_agent.py `
  --video data\input\your-clip.mp4 `
  --model models\your-football-weights.pt `
  --field-polygons data\input\your-field-polygons.json `
  --output-dir data\sessions\your-new-run-id
```

After a human reviews the referenced clip and plan, they can record a decision:

```powershell
.\.venv\Scripts\python approve_plan.py --run-dir data\sessions\your-run-id --decision approved --coach "Coach Name"
```

Use `--decision rejected` when appropriate. This is a local scripted approval path. The candidate events, team labels, and image-relative zones remain unverified; the plan asks the coach to review evidence before any tactical claim. AWS, FastAPI, and MCP are not yet wired, so this is **not the complete hackathon P0**.
