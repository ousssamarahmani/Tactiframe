# TactiFrame video quality gate

The supplied match recording and every review clip below are **local simulation and education material only**. Do not include their frames or clips in a public submission.

## Current review set

Run: `data/sessions/match-20261011-right-boundary/` (1,277 frames at 5 fps). The clips and `diagnostics.json` are under its `review/` folder. Recreate them with:

```powershell
.\.venv\Scripts\python cv\video_review.py --run-dir data\sessions\match-20261011-right-boundary
```

| Video window | Median tracked boxes/frame | Distinct IDs | Duplicate frame/ID pairs | Ball candidate frames |
|---|---:|---:|---:|---:|
| 0–30 s | 18 | 55 | 0 | 58 |
| 110–140 s | 17 | 52 | 0 | 34 |
| 220–250 s | 18 | 39 | 0 | 94 |

These are diagnostics, **not precision, recall, ID-switch, or ball-accuracy scores**. The earlier filtered run had 1,597 duplicate frame/ID pairs across 901 frames; the safe-merge and right-boundary runs have zero. The right-boundary run removes the two off-pitch boxes identified in the user's screenshot. ID turnover remains high, and ball candidates include pitch markings.

## Next task: label evidence before further tuning

1. Review each 30-second clip alongside its source video. Mark which visible boxes are on-pitch players/goalkeepers and which are staff, officials, or false detections.
2. Label the real ball where it is visible; mark frames where the ball is hidden or off screen. A model candidate is not a ball label.
3. Follow several visible players through continuous 5–10 second passages and record ID changes. Treat camera cuts separately.
4. Compute player precision/recall, ball candidate precision/recall on labeled frames, and ID switches on the continuous passages. Record the annotation file and clip checksum with the results.
5. Change one detector or tracker setting at a time, rerun the same review windows, and compare the same measures. Recheck the unique frame/ID invariant and video playability after every run.

Do not use `cv/evaluate.py` as an accuracy gate: it has no ground-truth annotations and its older summaries overstated success. Ball interpolation remains disabled in the main pipeline until real ball observations can be distinguished from pitch markings and scene cuts.

## 2½-minute local segment test

The 30–180 second portion of the same local recording was copied to `data/input/video-project-3-local-30s-to-180s.mp4` (750 frames at 5 fps). `run_pipeline.py` completed a fresh observation run at `data/sessions/match-20261011-local-150s-test/`, then `detect_events.py` exported events and clips. This segment and all derivatives remain local simulation and education material only.

| Check | Result |
|---|---:|
| Annotated video frames | 750; opens successfully |
| Track observations / final IDs | 13,206 / 96 |
| Duplicate `(frame, track_id)` pairs | 0 |
| Ball candidates | 236; unverified |
| Candidate events | 38: 19 zone density, 19 zone contest |
| Event clips | 38; all open and have expected frame counts |

Thirty-second windows had median 16–20 boxes per frame and 41–52 distinct final IDs. The ID count remains high for continuity claims. A frame at segment time 25 seconds (`review/annotated-25s.jpg`) shows several correctly boxed on-pitch players, two or more missed players near the central region, and no obvious tracked sideline staff. Two event-clip midframes were also opened for a spot check. No ground-truth accuracy or event precision was measured.

## Manual field-polygon A/B test on the same segment

`data/sessions/match-20261011-local-150s-polygon/` reran the same 750-frame clip and model with `--field-polygons data/input/video-project-3-local-150s-field-polygons.json`. The calibration is clip-specific and ignored by Git. The run produced 11,760 track observations, 87 final IDs, 236 unverified ball candidates, and zero duplicate frame/ID pairs. Its metadata records the calibration checksum and 4,312 pre-track `off_pitch_rejected` candidate boxes. It produced 35 candidate events (18 zone density, 17 zone contest) and 35 playable clips with expected frame counts.

The earlier run had 13,206 track observations, 96 IDs, and 38 events. Applying the polygon to earlier final tracks identifies 1,461 observations outside it; the new run has one observation just beyond the mathematical boundary within the configured five-pixel line margin. Greedy same-frame box matching at IoU ≥0.3 matches 11,744 of 11,745 earlier inside-polygon observations in the new run. This suggests the reduced count came chiefly from outside boxes, but it is **not a labeled player-recall result**.

The earlier `zone_density` candidate in `r0c2` from 115.0–130.6 seconds, driven by staff on green runoff, is absent in the new `events.json`. The goal-area frames at 105, 115, 125, and 135 seconds visibly retain the player group and goalkeeper while removing the staff boxes. Missed on-pitch players, team-label errors, high ID turnover, and unverified ball candidates remain. The manual polygon must be recalibrated for new footage or substantially different camera views.
