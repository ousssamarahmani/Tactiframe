# TactiFrame asset inventory

This document separates local simulation assets from assets that may be included in a public hackathon submission. Video and weights remain under Git-ignored `data/` and `models/`.

## Local simulation footage

| Item | Record |
|---|---|
| Source | `data/input/video-project-3.mp4` — user-provided screen recording of a YouTube match, 4 min 15 sec, 1920×1080, 30 fps |
| SHA-256 | `0f41addef7835fde93776fe720cc05d5eb497432cce997ec5cde6ce2187c798c` |
| Prepared copy | `data/input/video-project-3-5fps-1280.mp4` — full duration sampled to 1280×720, 5 fps; mapping and hashes in its adjacent `.json` manifest |
| Use | **Local simulation and education only**, per the user's instruction. No claim of a license to the underlying match footage. |
| Derived output | `data/sessions/match-20261011-5fps/` has the same local-only use boundary, including `tracked.mp4`, frames, and any clips extracted from it. |

Do not put this footage or its visual derivatives in public submission materials without separate permission for the underlying video. The source file and outputs are not committed.

## Detector weights

| Checkpoint | Status |
|---|---|
| [`martinjolif/yolo-football-player-detection`](https://huggingface.co/martinjolif/yolo-football-player-detection), revision `5e83fafa8d564243001ce8e063612a618a138fbe` | Published license: AGPL-3.0. Local path: `models/yolo-football-player-detection.pt`. SHA-256: `69c652bfa9814ef882c439617f04b8fd5749b6b8455aaa3c36110bc2e802aadd`. Class order verified: ball, goalkeeper, player, referee. Candidate for a reproducible submission after checking the obligations of its stated license. |
| [`uisikdag/yolo-v8-football-players-detection`](https://huggingface.co/uisikdag/yolo-v8-football-players-detection), revision `01c4d0e18813ac75a2c73cc35145bc240af85342` | License metadata is absent. Local path: `models/uisikdag/best.pt`. SHA-256: `844e9ad1ebafbd0c07f066e45aa87d9b87595dd9092dfee9cac3b10a6a5fa730`. Class order verified. Used for the faster local simulation run; **not selected for public distribution**. |

The [training image dataset](https://huggingface.co/datasets/martinjolif/football-player-detection) is labeled CC BY 4.0. It is not demo footage. Local training attempts have not produced a usable checkpoint.

## Submission footage to obtain

A [SoccerTrack v2](https://huggingface.co/datasets/atomscott/soccertrack-v2) panoramic match segment is a candidate: its dataset metadata states CC BY 4.0 and its MOT subset contains paired four-minute clips. Access is gated and requires the account holder to accept the dataset's access terms; no match footage from it has been acquired here. Its attribution and use terms must be recorded with any selected clip.

An original field-side recording with permission for public reuse is another option. A screen recording of someone else's broadcast does not establish those rights.

**Current gate:** the technical pipeline has run, but TactiFrame has no approved public-submission clip yet. Keep using the current clip for local tests; use a separately cleared source for any public demo video or screenshots.
