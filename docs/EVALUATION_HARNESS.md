# TactiFrame evaluation harness

`evaluation.json` is a per-session structural quality report. It measures whether the OpenCV run, candidate-event evidence, agent trace, and coach-approval boundary remain internally consistent. It does **not** score tactical accuracy or turn candidate events into verified football facts.

## Run it

Run the agent first, then evaluate the same session:

```powershell
.\.venv\Scripts\python run_agent.py --run-dir data\sessions\your-session
.\.venv\Scripts\python evaluate_session.py --run-dir data\sessions\your-session
```

The command writes `data/sessions/your-session/evaluation.json` and returns exit code `0` only when the structural checks pass.

For an already-completed run, validate raw ball candidates without re-running perception:

```powershell
.\.venv\Scripts\python validate_ball_candidates.py --run-dir data\sessions\your-session
```

This writes `ball_candidates_validated.json` and updates local `run.json` counts. It removes only low-confidence and sustained static-image candidates; it flags large trajectory jumps for review and does not interpolate, infer possession, or claim a verified ball path.

For descriptive ID-churn windows, run:

```powershell
.\.venv\Scripts\python diagnose_tracks.py --run-dir data\sessions\your-session --window-seconds 30
```

It writes `track_diagnostics.json`. These are not ID-switch scores: label continuous player passages before claiming identity accuracy.

## What it measures

- perception counts: frames, observations, player IDs, ball candidates, off-pitch rejections, duplicate frame/track IDs, and short-track share;
- candidate event totals by type and image-relative zone;
- mean detector-rule confidence and local evidence-clip availability;
- the actual agent tool order and whether each recorded vision decision selected the next tool used;
- whether a drafted plan references an existing event and nonempty local evidence clip;
- whether approval remains pending or records a named coach decision.

## Simulated regression scenarios

`tests/test_evaluation_harness.py` runs four deterministic local cases with AWS disabled:

1. density-first candidates select `analyze_zone` before a clip;
2. contest-first candidates select `get_clip` first;
3. no candidates stop without creating a plan;
4. a missing evidence clip stops the agent without creating an unsupported plan.

Run all checks with:

```powershell
.\.venv\Scripts\python -m unittest discover tests -v
```

An evaluation failure is an engineering signal to inspect the session artifacts. It is not a tactical verdict and should never be hidden by a generated plan.
