"""Conservative candidate events from tracked player positions.

No possession, pass, or turnover is inferred from unverified ball candidates.
"""

from collections import defaultdict

from cv.zones import zone_for_point


DETECTOR_NAME = "sustained-zone-observation"
DETECTOR_VERSION = "1"
DENSITY_MIN_DISTINCT_TRACK_IDS = 4
CONTEST_MIN_PLAYERS_PER_TEAM = 2


def candidate_confidence(span: dict, min_frames: int) -> dict:
    """Return a transparent rule-support score, not a calibrated probability."""
    duration_score = min(1.0, span["observedFrames"] / (min_frames * 2))
    occupancy_score = min(1.0, span["totalDistinctIds"] / 8)
    return {
        "score": round(0.6 * duration_score + 0.4 * occupancy_score, 3),
        "method": "rule-support-v1",
        "calibrated": False,
        "components": {
            "observedFrames": span["observedFrames"],
            "minimumFrames": min_frames,
            "meanDistinctTrackIds": round(span["totalDistinctIds"] / span["observedFrames"], 3),
        },
    }


def detect_events(tracks: list[dict], fps: float, width: int, height: int,
                  min_seconds: float = 4.0, max_gap_seconds: float = 0.4) -> list[dict]:
    """Find sustained zone density and two-team contests on sampled frames."""
    if fps <= 0:
        raise ValueError("fps must be positive")
    by_frame = defaultdict(list)
    for track in tracks:
        if track.get("class_name") == "player":
            by_frame[int(track["frame"])].append(track)

    active = {}
    finished = []
    max_gap = max(1, round(max_gap_seconds * fps))
    min_frames = max(1, round(min_seconds * fps))

    for frame in sorted(by_frame):
        zones = defaultdict(list)
        for track in by_frame[frame]:
            # Player feet approximate pitch contact better than box centre.
            x1, _, x2, y2 = track["bbox"]
            zone = zone_for_point((x1 + x2) / 2, y2, width, height)
            zones[zone].append(track)

        observed = {}
        for zone, members in zones.items():
            # Distinct IDs avoid duplicate boxes inflating the occupancy count.
            ids = {member["track_id"] for member in members}
            if len(ids) >= DENSITY_MIN_DISTINCT_TRACK_IDS:
                observed[("zone_density", zone)] = ids
            teams = {team: {member["track_id"] for member in members
                            if member.get("team") == team}
                     for team in ("team_a", "team_b")}
            if all(len(team_ids) >= CONTEST_MIN_PLAYERS_PER_TEAM for team_ids in teams.values()):
                observed[("zone_contest", zone)] = ids

        for key, ids in observed.items():
            previous = active.get(key)
            if previous is None or frame - previous["lastFrame"] > max_gap:
                if previous is not None:
                    finished.append((key, previous))
                active[key] = {"startFrame": frame, "lastFrame": frame,
                               "observedFrames": 1, "trackIds": set(ids),
                               "totalDistinctIds": len(ids)}
            else:
                previous["lastFrame"] = frame
                previous["observedFrames"] += 1
                previous["trackIds"].update(ids)
                previous["totalDistinctIds"] += len(ids)

        for key in list(active):
            if key not in observed and frame - active[key]["lastFrame"] >= max_gap:
                finished.append((key, active.pop(key)))

    finished.extend(active.items())
    events = []
    for (kind, zone), span in sorted(finished, key=lambda item: (item[1]["startFrame"], item[0])):
        if span["observedFrames"] < min_frames:
            continue
        event_id = f"evt-{len(events) + 1:04d}"
        events.append({
            "id": event_id,
            "type": kind,
            "status": "candidate",
            "startFrame": span["startFrame"],
            "endFrame": span["lastFrame"],
            "startSeconds": round(span["startFrame"] / fps, 3),
            "endSeconds": round(span["lastFrame"] / fps, 3),
            "zone": {"id": zone, "coordinateSystem": "image_relative_3x3"},
            "trackIds": sorted(span["trackIds"]),
            "confidence": candidate_confidence(span, min_frames),
            "detector": {
                "name": DETECTOR_NAME,
                "version": DETECTOR_VERSION,
                "parameters": {
                    "minSeconds": min_seconds,
                    "maxGapSeconds": max_gap_seconds,
                    "densityMinDistinctTrackIds": DENSITY_MIN_DISTINCT_TRACK_IDS,
                    "contestMinPlayersPerTeam": CONTEST_MIN_PLAYERS_PER_TEAM,
                },
            },
            "evidence": {"clipPath": f"clips/{event_id}.mp4"},
            "limitations": ["Uncalibrated broadcast view", "Team and track IDs are unverified"],
        })
    return events
