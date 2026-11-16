# Tracking A/B result — retain the 5-second baseline

**Decision:** retain the existing **5-second** lost-track buffer. Do not promote
the 8-second candidate to the TactiFrame default.

## Controlled comparison

| Setting | Baseline | Candidate |
|---|---:|---:|
| Lost-track buffer | 5 seconds (pipeline default) | 8 seconds |
| Source video | Same | Same |
| YOLO model | Same | Same |
| Field-polygon checksum | Same | Same |
| Sampled frames | 750 | 750 |

The baseline was created before the buffer value was persisted to `run.json`;
the code default in `run_pipeline.py` and `cv/tracker.py` is 5 seconds. The
candidate explicitly records 8 seconds.

## Measured outcome

| Metric | 5 seconds | 8 seconds | Result |
|---|---:|---:|---|
| Unique player IDs | 87 | 93 | Worse |
| Mean new IDs / 30 s window | 17.4 | 18.6 | Worse |
| Mean observations / ID | 135.17 | 126.55 | Worse |
| Median observations / ID | 28 | 24 | Worse |
| Short-track share | 2.3% | 3.2% | Worse |
| Track observations | 11,760 | 11,769 | Effectively unchanged |
| Validated ball candidates | 163 | 163 | Unchanged |

Both sessions passed the structural evaluation: no duplicate frame/track pairs,
local evidence clips were available, and the vision-dependent tool path remained
valid. These checks do not turn candidate tracks into labeled ID-switch accuracy.

## Visual spot check

The annotated outputs were sampled at 15 s, 75 s, and 125 s. The 8-second
candidate showed no clear recovery of missing on-pitch players or reduction of
sideline/crowd candidates, while its continuity metrics worsened. This is enough
to reject the setting for the current single-camera clip.

## Next CV experiment

Keep the 5-second default. Any future tracking experiment must change exactly
one setting, reuse this same clip and polygon, create a new session directory,
and compare the same metrics plus annotated passages before changing a default.
