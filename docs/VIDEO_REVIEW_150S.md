# TactiFrame: 2½-minute local video review

Reviewed 11 October 2026. Input is the 30–180 second portion of the user-supplied screen recording, sampled to 5 fps (750 frames). The segment and all derived files are **local simulation and education material only**, not public submission footage. Segment timestamps below begin at zero; add 30 seconds to locate the corresponding time in the earlier full-duration working copy.

## Files to inspect

- Run: `data/sessions/match-20261011-local-150s-test/`
- Annotated video: `tracked.mp4`
- Event list: `events.json`
- Evidence: `clips/evt-0001.mp4` through the paths listed in `events.json`
- Still frames used for this review: `review/annotated-005s.jpg`, `annotated-035s.jpg`, `annotated-065s.jpg`, `annotated-095s.jpg`, `annotated-125s.jpg`, and `annotated-145s.jpg`

## Technical checks

The annotated video opens with 750 frames. The run has 13,206 track observations, 96 final IDs, and no duplicate `(frame, track_id)` pairs. It has 236 **unverified** ball candidates. Event export produced 38 candidate events (19 `zone_density`, 19 `zone_contest`) and 38 clips; every clip opens and has the frame count recorded in `events.json`. Median tracked boxes per frame range from 16 to 20 across five 30-second windows, but each window contains 41–52 distinct final IDs. This indicates substantial track turnover; it is not an ID-switch metric against labeled ground truth.

## Visual spot check

| Segment time | Observation |
|---|---|
| 5 s | Most visible on-pitch players and the goalkeeper have boxes; several labels overlap around midfield. |
| 35 s | Broad on-pitch coverage, but a visible orange player near the lower-left touchline lacks a box. |
| 65 s | The crowded attack is largely boxed; at least one visible orange player left of the central group is missed. |
| 95 s | YouTube player controls appear in the source recording. Several players around the penalty area are missed or obscured, so this interval needs careful manual review. |
| 125 s | **Failure:** multiple people beyond the right goal line are tracked. Candidate `evt-0030` (`zone_density`, `r0c2`, 115.0–130.6 s) overlaps this area and is likely a false event. The current goal-line heuristic does not generalize to this camera view. |
| 145 s | The on-pitch defensive shape is mostly boxed, with overlapping labels in the central group. No reliable ball path is visible in the output. |

This is a six-frame qualitative sample plus file-integrity checks, **not** measured detection precision, recall, event precision, or ball accuracy. The raw evidence clips have no annotations; compare them with `tracked.mp4` and the source when reviewing candidates.

## Decision

The 2½-minute observation → candidate event → clip pipeline works technically. **Do not present all 38 events as valid tactical evidence.** Before agent tools consume them, fix or gate the right-goal-line leakage, manually label representative event clips, and either reject false events or mark them as unverified. Pass and turnover events remain blocked by unverified ball detections and weak track continuity.
