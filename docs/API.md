# TactiFrame local review API

The FastAPI service exposes completed local session artifacts and the same coach
approval gate used by `approve_plan.py`. It does not run perception, generate a
plan on a read request, or bypass human approval.

## Start the service

```powershell
.\.venv\Scripts\uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Use either a session folder name or the `runId` from `run.json` as
`{session_id}`.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Service status |
| `GET` | `/sessions/{session_id}` | Run metadata |
| `GET` | `/sessions/{session_id}/events` | Candidate events |
| `GET` | `/sessions/{session_id}/trace` | Agent and cloud trace |
| `GET` | `/sessions/{session_id}/plan` | Current draft/decision |
| `GET` | `/sessions/{session_id}/artifacts` | Candidate heatmap, zone matrix, and team-shape JSON |
| `GET` | `/sessions/{session_id}/video` | Annotated session video |
| `GET` | `/sessions/{session_id}/clips/{event_id}` | One evidence clip selected from `events.json` |
| `GET` | `/review/{session_id}` | Local visual evidence viewer |
| `POST` | `/sessions/{session_id}/chat` | Evidence-bound candidate answer; cannot draft or approve a plan |
| `POST` | `/sessions/{session_id}/simulate-agents` | Local Video Analyst, Vision Agent, and Tactical Analyst simulation; cannot draft or approve a plan |
| `POST` | `/sessions/{session_id}/approval` | Explicit coach decision |

## Evidence viewer

After running `generate_evidence_artifacts.py` for a session, open this local browser URL:

```text
http://127.0.0.1:8000/review/match-20261012-video-retest-polygon
```

It plays the annotated session video and renders candidate heatmap, zone-matrix, and team-shape artifacts. It is an evidence viewer, not a source of verified tactical facts.

## Agent Vision Chat API

`POST /sessions/{session_id}/chat` accepts a single coach question and returns a candidate-only answer with event, clip, zone, and artifact references. It calls existing session tools, appends the choices to `trace.json`, and never invokes `draft_plan` or `request_approval`.

```json
{"question":"Show candidate evidence in r1c1"}
```

Approve or reject only after reviewing the evidence:

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/sessions/demo-run/approval `
  -ContentType 'application/json' `
  -Body '{"decision":"approved","coach":"Coach Name"}'
```

The endpoint accepts only `approved` or `rejected` and requires a coach name.
It returns a conflict if the plan is not pending approval or has already been
decided. Paths are constrained to the configured session directory.
