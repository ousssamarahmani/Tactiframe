# TactiFrame CV baseline

The frozen P0 perception reference is the pitch-aware observation path:

```text
football-specific YOLO classes
  → class, size, turf, and manual field-polygon filtering
  → Supervision ByteTrack
  → team-colour sampling and ball candidates
  → annotated video and versioned session metadata
```

Use one fixed clip and a polygon calibration made for that exact clip. The command below is the reference run shape; video, model, polygon file, and session output are Git-ignored local assets.

```powershell
.\.venv\Scripts\python run_agent.py `
  --video data\input\match.mp4 `
  --model models\football.pt `
  --field-polygons data\input\match-field-polygons.json `
  --output-dir data\sessions\reference-polygon-run
```

## Acceptance checks

- `run.json` reports OpenCV 5 and `pitchCalibration: manual-image-polygon`.
- `tracks.json`, `tracks_with_teams.json`, `ball_observations.json`, `ball_candidates_validated.json`, and `tracked.mp4` are nonempty.
- No duplicate `(frame, track_id)` pair exists.
- `events.json` and its evidence clips open after event export.
- The trace shows `list_events` before `draft_plan`, and a plan remains pending until a coach records an explicit decision.

## Known limits

- Track IDs fragment during camera motion, cuts, and occlusion. They cannot identify a player across the match.
- Some on-pitch players are missed; a polygon can also reject players very near a touchline.
- Ball observations are candidates. Pitch markings and small distant objects can create false positives.
- Team labels are sampled jersey-colour guesses and can be wrong.
- Zones are a 3×3 image grid, not calibrated field coordinates. Candidate events must not be presented as verified passes, turnovers, pressure, or possession.

The reference baseline is sufficient for the current candidate-event and agentic-trace demo. Improve quality in measured, isolated passes; do not change the event contract silently. See [EVAL.md](EVAL.md), [FIELD_POLYGON.md](FIELD_POLYGON.md), and [EVENT_CONTRACT.md](EVENT_CONTRACT.md).
