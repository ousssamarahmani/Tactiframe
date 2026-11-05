# TactiFrame repeatable review demo

Use a completed session that already sits directly under `data/sessions/`. The
source clip, weights, and session directory are ignored by Git.

```powershell
.\demo.ps1 `
  -RunDir data\sessions\your-session `
  -Decision approved `
  -Coach "Coach Name"
```

The script performs one controlled flow:

```text
completed OpenCV session
  → agent selects evidence from candidate events
  → Bedrock proposal or local fail-soft proposal
  → local HTTP review of events, trace, and plan
  → explicit named coach decision through POST /approval
```

Use `-Decision rejected` whenever the coach does not accept the candidate
finding. The script requires both the decision and coach name; it cannot
auto-approve a plan.

The API server is started only for the demo and stopped when the script exits.
For manual API use, see [API.md](API.md).
