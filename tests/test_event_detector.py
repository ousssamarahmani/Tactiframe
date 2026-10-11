import unittest

from cv.event_detector import detect_events
from cv.zones import zone_for_point


class EventDetectorTests(unittest.TestCase):
    def test_zone_clamps_edges(self):
        self.assertEqual(zone_for_point(-1, 200, 900, 600), "r1c0")
        self.assertEqual(zone_for_point(900, 600, 900, 600), "r2c2")

    def test_two_candidate_types_require_sustained_evidence(self):
        tracks = []
        for frame in range(25):
            for track_id, team in enumerate(["team_a", "team_a", "team_b", "team_b"], 1):
                tracks.append({"frame": frame, "track_id": track_id,
                               "class_name": "player", "team": team,
                               "bbox": [50, 50, 70, 90]})
        events = detect_events(tracks, fps=5, width=300, height=300)
        self.assertEqual({event["type"] for event in events},
                         {"zone_density", "zone_contest"})
        self.assertTrue(all(event["zone"]["coordinateSystem"] == "image_relative_3x3"
                            for event in events))

    def test_short_or_unknown_team_does_not_create_contest(self):
        tracks = [{"frame": frame, "track_id": track_id,
                   "class_name": "player", "team": "unknown",
                   "bbox": [50, 50, 70, 90]}
                  for frame in range(10) for track_id in range(4)]
        self.assertEqual(detect_events(tracks, 5, 300, 300), [])


if __name__ == "__main__":
    unittest.main()
