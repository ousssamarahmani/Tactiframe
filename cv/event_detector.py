"""Conservative candidate events from tracked player positions.

No possession, pass, or turnover is inferred from unverified ball candidates.
"""

from collections import defaultdict

from cv.zones import zone_for_point


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
            if len(ids) >= 4:
                observed[("zone_density", zone)] = ids
            teams = {team: {member["track_id"] for member in members
                            if member.get("team") == team}
                     for team in ("team_a", "team_b")}
            if all(len(team_ids) >= 2 for team_ids in teams.values()):
                observed[("zone_contest", zone)] = ids

        for key, ids in observed.items():
            previous = active.get(key)
            if previous is None or frame - previous["lastFrame"] > max_gap:
                if previous is not None:
                    finished.append((key, previous))
                active[key] = {"startFrame": frame, "lastFrame": frame,
                               "observedFrames": 1, "trackIds": set(ids)}
            else:
                previous["lastFrame"] = frame
                previous["observedFrames"] += 1
                previous["trackIds"].update(ids)

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
            "evidence": {"clipPath": f"clips/{event_id}.mp4"},
            "limitations": ["Uncalibrated broadcast view", "Team and track IDs are unverified"],
        })
    return events
