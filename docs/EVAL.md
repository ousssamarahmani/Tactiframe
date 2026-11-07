# TactiFrame evaluation status

## Structural evaluation harness

The current evaluation harness writes `evaluation.json` for a completed session. On the local pitch-polygon session it recorded 750 frames, 11,760 track observations, 87 unique player IDs, 236 unverified ball candidates, 4,312 off-pitch rejections, 35 candidate events, and 35/35 locally available evidence clips. It also confirmed the vision result selected `analyze_zone` as the next tool, that the plan cited `evt-0002` and its clip, and that the plan remained pending explicit coach approval. This is a structural consistency report, not a labeled accuracy score. See [EVALUATION_HARNESS.md](EVALUATION_HARNESS.md).

## Verified in this checkout

The observation worker completed a full-duration technical run on a supplied 4-minute-15-second match segment. It processed a 5 fps working copy of all 7,661 source frames (1,277 sampled frames), wrote five nonempty run files, and produced a playable annotated video with 1,277 frames. The run folder is `data/sessions/match-20261011-5fps/`; its `run.json` records the input and model hashes, environment, counts, and 453-second execution time. The working copy's manifest at `data/input/video-project-3-5fps-1280.json` links it to the original source checksum. Per the user's instruction, this footage and its visual derivatives are for local simulation and education only; they are not public-submission assets. See [ASSETS.md](ASSETS.md).

Measured output: 20,005 track observations, 220 final track IDs, 55 ball observations, and provisional team votes for 141 IDs. Sample annotated frames show player boxes and labels, but IDs fragment across camera motion and cuts; some sideline people are labeled as players. Ball coverage is 55/1,277 frames. This establishes a runnable observation baseline, not reliable possession or event evidence.

## Filtered run on the same local clip

`data/sessions/match-20261011-filtered-960/` completed in 380 seconds on the same 1,277-frame working copy. It used football YOLOv8 weights, `imgsz=960`, ball confidence 0.15, player confidence 0.30, IoU 0.5, a visible-green-turf check before Supervision ByteTrack, and a 10-pixel minimum player box height. Its `run.json` records OpenCV 5.0.0, Ultralytics 8.4.115, Torch 2.14.1+cpu, model path/checksum, settings, and rejection counts. Five files are nonempty; `tracked.mp4` opens with 1,277 frames.

It produced 22,640 track observations and 179 final IDs, versus 20,005 and 220 for the upstream-style run. The pre-track filter rejected 1,021 off-turf candidates and 4,272 candidates below the player threshold. Unique final IDs in 30-second windows still range from 38 to 55, so track continuity remains insufficient for possession claims. The 507 ball candidates include pitch markings mistaken for the ball; this is **not** a verified increase in ball coverage. Do not interpolate these observations or use them as event evidence yet. These outputs remain local simulation material.

Visual review exposed 1,597 duplicate `(frame, track_id)` pairs in this run: post-processing could assign the same ID to several players in a frame. This run must not be used as an identity-quality baseline. The merge logic has since been corrected and now fails a run if that invariant is violated.

## Corrected full video run

`data/sessions/match-20261011-safe-merge/` processed the same 1,277 frames in 383 seconds and wrote all five nonempty files. Its annotated video opens with 1,277 frames. It has 22,640 player observations, 174 final IDs, 507 unverified ball candidates, and **zero duplicate `(frame, track_id)` pairs**. The run metadata identifies the checkpoint architecture as `yolov8s.yaml` and logs the software versions and inference settings. Three local 30-second review clips, their diagnostics, and the next manual labeling protocol are in [VIDEO_QA.md](VIDEO_QA.md). The corrected run still has substantial ID turnover, so it does not establish reliable possession or event evidence.

## Right-boundary video test

The same full clip was rerun at `data/sessions/match-20261011-right-boundary/` after adding a visible right goal-line check before tracking. It completed in 418 seconds, wrote all five nonempty files, and produced an annotated video with 1,277 frames. The run has 21,578 player observations, 171 final IDs, 507 unverified ball candidates, and zero duplicate `(frame, track_id)` pairs. The filter recorded 2,841 candidate rejections beyond the right goal line. At source frames 101–108 it rejects both reported outside boxes (#132 and #568 in the prior run) while retaining the on-pitch goalkeeper and a nearby player. A 30-second rerun around those frames also completed with the two boxes absent. Sampled views elsewhere show removal of right-side staff boxes without an obvious on-pitch loss, but ground-truth labels are still needed to measure recall. The ball result did not improve.

The CV unit tests pass with `python -m unittest discover tests -q`, including the pre-track filter and candidate event checks. The virtual environment lacks `pytest`, so that runner has not been used.

## Candidate event and clip run

`detect_events.py` processed `data/sessions/match-20261011-right-boundary/` into 41 candidate events: 31 `zone_density` and 10 `zone_contest`. Each `events.json` record has an image-relative 3×3 zone and a local clip path. All 41 clip files opened and their reported frame counts matched the actual video frame counts. Two representative clip frames were reviewed: one shows a visible group of players in the named region, and the other shows both kit colors in the central region. This is a structural and spot visual check, **not** a precision or recall score. The first clip also contains the recorded video-player interface, which reinforces that the footage is a local simulation asset only. See [EVENT_CONTRACT.md](EVENT_CONTRACT.md). No possession, pass, turnover, or approval claim follows from these candidate types.

## Manual field-polygon A/B gate

The 2½-minute local segment was rerun at `data/sessions/match-20261011-local-150s-polygon/` with clip-specific polygon keyframes. Relative to the identical segment without the polygon, final track observations fell from 13,206 to 11,760, final IDs from 96 to 87, and candidate events from 38 to 35. The known false `r0c2` density event around segment time 125 seconds disappeared. The polygon rejected 4,312 pre-track candidate boxes; 1,461 earlier final track observations fall outside it. Box matching found 11,744 of 11,745 earlier inside-polygon observations in the new run. This is an A/B check against the manually placed boundary, **not** labeled player recall. Ball candidates remained 236 and unverified. The 35 new clips all opened with expected frame counts, and the 21 unit tests pass. See [VIDEO_QA.md](VIDEO_QA.md) and [FIELD_POLYGON.md](FIELD_POLYGON.md).

## Local agent tool-order test

`run_agent.py` was run against both completed local sessions. The baseline events (19 density, 19 contest) made the orchestrator call `get_clip` after `list_events`; the polygon events (18 density, 17 contest) made it call `analyze_zone` next. Both runs then used the other evidence tool, drafted a candidate plan, and wrote `trace.json` plus a pending coach-approval request. The code enforces `list_events` before `draft_plan`; no approval is fabricated. There are 24 passing unit tests, including tool-order and approval checks. This demonstrates a vision-influenced local tool sequence, but AWS integration and a cleared public demo clip remain outstanding. See [AGENT_LOOP.md](AGENT_LOOP.md).

## Detector comparison on one 12-second segment

With the same 60-frame local segment and `imgsz=960`, the faster football YOLOv8s checkpoint produced 1,023 player observations, 29 final IDs, and 29 ball candidates in about 25 seconds. The football YOLO11m checkpoint produced 1,046 player observations, 32 final IDs, and 14 ball candidates in about 52 seconds. This sample does not establish which checkpoint recognizes the ball more accurately; candidate counts include pitch-marking errors. YOLO11m did not improve ID continuity in this short comparison and was not chosen for the full local evaluation run.

## Reproduce the observation baseline

Use Python 3.11 or 3.13, a rights-cleared football clip, and football-specific YOLO weights with class IDs ball=0, goalkeeper=1, player=2, referee=3. Do not use generic COCO weights for this check.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python prepare_clip.py --input data\input\match.mp4 --output data\input\match-5fps.mp4 --fps 5 --width 1280
.\.venv\Scripts\python run_pipeline.py --video data\input\match-5fps.mp4 --model models\yolo-football-player-detection.pt --device cpu
```

The run should create `run.json`, `tracks.json`, `tracks_with_teams.json`, `ball_observations.json`, and `tracked.mp4` in a new `data/sessions/<run-id>/` folder. Inspect the files, counts, video playability, and nonempty detections before claiming success. `run.json` records input and model checksums and actual library versions. If inference fails after the folder is created, it records `status: failed` and the error.

Run the existing CV unit tests after installing dependencies:

```powershell
.\.venv\Scripts\python -m unittest discover tests -q
```

## Not yet implemented

Candidate event extraction, image-relative zones, and clip export have a local technical run but no labeled accuracy evaluation. The local agent tools, trace, and pending coach approval have a scripted test but no live coach decision. AWS integration, API endpoints, and a cleared public demo have no evaluation results yet. Their acceptance criteria are listed in [HACKATHON.md](HACKATHON.md).

## Known observation limitations

Team labels are based on jersey colors sampled from player boxes. If the selected calibration frame has fewer than six player boxes, team calibration is unavailable and labels are `unknown`. The first run used upstream BoT-SORT; the filtered run uses ByteTrack. Both use post-processing that can merge track fragments, and both still fragment identities. The visible-turf filter can remove legitimate players on or just outside the touchline. The worker outputs observations only, not verified tactical evidence. Sampling at 5 fps can miss quick ball movement.
