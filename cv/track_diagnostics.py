"""Descriptive track-continuity diagnostics; not an identity accuracy score."""

from collections import Counter


def summarize_track_windows(
    tracks: list[dict], *, total_frames: int, fps: float, window_seconds: int = 30,
) -> dict:
    """Summarize ID churn in fixed windows without claiming ID-switch truth."""
    if fps <= 0 or total_frames < 1 or window_seconds < 1:
        raise ValueError("fps, total_frames, and window_seconds must be positive")
    by_id = {}
    for track in tracks:
        if "track_id" in track and "frame" in track:
            by_id.setdefault(track["track_id"], []).append(track["frame"])
    spans = {track_id: (min(frames), max(frames)) for track_id, frames in by_id.items()}
    window_frames = max(1, round(fps * window_seconds))
    windows = []
    for first in range(0, total_frames, window_frames):
        last = min(total_frames, first + window_frames)
        active = {track_id: [frame for frame in frames if first <= frame < last]
                  for track_id, frames in by_id.items()}
        active = {track_id: frames for track_id, frames in active.items() if frames}
        lengths = sorted(len(frames) for frames in active.values())
        per_frame = Counter(frame for frames in active.values() for frame in frames)
        new_ids = sum(start >= first and start < last for start, _ in spans.values())
        ended_ids = sum(end >= first and end < last for _, end in spans.values())
        windows.append({
            "startSecond": round(first / fps, 3),
            "endSecond": round(last / fps, 3),
            "frames": last - first,
            "distinctTrackIds": len(active),
            "newTrackIds": new_ids,
            "endedTrackIds": ended_ids,
            "shortTrackIdsAtOrBelowOneSecond": sum(length <= fps for length in lengths),
            "medianObservationsPerId": lengths[len(lengths) // 2] if lengths else 0,
            "medianTrackedBoxesPerFrame": (
                sorted(per_frame.get(frame, 0) for frame in range(first, last))[(last - first) // 2]
            ),
        })
    return {
        "schemaVersion": 1,
        "assessment": "descriptive ID churn diagnostics; labels are required for ID-switch accuracy",
        "windowSeconds": window_seconds,
        "windows": windows,
    }
