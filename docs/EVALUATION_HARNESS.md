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

Generate candidate evidence artifacts before Agentic Vision Chat uses a session:

```powershell
.\.venv\Scripts\python generate_evidence_artifacts.py --run-dir data\sessions\your-session
```

It writes `artifacts/heatmap.json`, `artifacts/zone_matrix.json`, and `artifacts/team_shape_snapshots.json`, then registers them in `run.json`. These are deterministic, image-relative JSON artifacts—not calibrated tactical facts or rendered coach-facing charts.

## Controlled tracking A/B run

Run this from a normal local PowerShell terminal (not a time-limited automation window). It reuses the baseline session's exact video, model, and pitch polygon, changes **only** the lost-track buffer from its baseline default of 5 seconds to 8 seconds, disables AWS for the experiment, then writes `tracking_ab_comparison.json` in the candidate session:

```powershell
.\run_tracking_ab.ps1 `
  -BaselineRunDir data\sessions\match-20261012-video-retest-polygon `
  -CandidateRunDir data\sessions\match-ab-lost-buffer-8s `
  -LostTrackBufferSeconds 8
```

Do not select a winner from the JSON alone. Reject runs that break structural checks, then review the same labeled player passages and the annotated video before accepting a changed setting.

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
