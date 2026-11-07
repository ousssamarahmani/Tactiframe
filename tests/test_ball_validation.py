import unittest

from cv.ball_validation import validate_ball_candidates


class BallValidationTests(unittest.TestCase):
    def test_removes_low_confidence_and_static_marking_candidates(self):
        candidates = [
            {"frame": 0, "x": 1, "y": 1, "confidence": 0.1},
            *[{"frame": frame, "x": 100, "y": 200, "confidence": 0.8}
              for frame in range(1, 6)],
            {"frame": 7, "x": 160, "y": 210, "confidence": 0.9},
        ]
        validated, summary = validate_ball_candidates(candidates)
        self.assertEqual([item["frame"] for item in validated], [7])
        self.assertEqual(summary["rejected"], {"low_confidence": 1, "static_position": 5})

    def test_retains_motion_and_marks_large_jumps_for_review(self):
        candidates = [
            {"frame": 0, "x": 10, "y": 10, "confidence": 0.8},
            {"frame": 1, "x": 20, "y": 10, "confidence": 0.8},
            {"frame": 2, "x": 300, "y": 10, "confidence": 0.8},
        ]
        validated, summary = validate_ball_candidates(candidates)
        self.assertEqual(len(validated), 3)
        self.assertEqual(validated[-1]["trajectoryWarning"], "large_jump")
        self.assertEqual(summary["trajectoryWarnings"]["large_jump"], 1)
