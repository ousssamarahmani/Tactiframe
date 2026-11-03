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
| `POST` | `/sessions/{session_id}/approval` | Explicit coach decision |

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
