# TactiFrame manual field polygon

Use `--field-polygons <path.json>` with `run_pipeline.py` for clips where green runoff turf or sideline staff pass the visible-turf filter. The polygon is checked **before ByteTrack**. Player and goalkeeper boxes use the foot point; ball boxes use the center. Allowed class, confidence, and size checks still run first. The polygon replaces the older right-goal-line heuristic for that run, while the green-turf check remains active.

The JSON contains `videoChecksum` (SHA-256 with `sha256:` prefix), `frameSize` (`[width, height]`), and `keyframes`. Each keyframe has a zero-based `frame` and the same number of clockwise image-pixel `points`. Polygon vertices are linearly interpolated between keyframes and held at the nearest keyframe outside that range. The input checksum and frame size must match; a calibration cannot silently be reused on another clip. Keep clip-specific calibration files under ignored `data/` until the source footage is cleared for publication.

The 2½-minute local simulation clip uses 16 manually reviewed keyframes, denser near the right goal. Its calibration is at `data/input/video-project-3-local-150s-field-polygons.json` and is intentionally ignored by Git. This is an image-space gate, not a metric pitch map. A new camera angle, zoom, or cut may require another keyframe. A narrow margin near the line can retain a few borderline boxes; inspect those frames before using the resulting events.

```powershell
.\.venv\Scripts\python run_pipeline.py `
  --video data\input\your-clip.mp4 `
  --model models\your-football-weights.pt `
  --field-polygons data\input\your-clip-field-polygons.json
.\.venv\Scripts\python detect_events.py --run-dir data\sessions\your-run-id
```
