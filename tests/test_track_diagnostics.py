import unittest

from cv.track_diagnostics import summarize_track_windows


class TrackDiagnosticsTests(unittest.TestCase):
    def test_reports_id_churn_in_fixed_windows(self):
        tracks = [
            {"frame": 0, "track_id": 1}, {"frame": 1, "track_id": 1},
            {"frame": 4, "track_id": 2}, {"frame": 5, "track_id": 2},
            {"frame": 8, "track_id": 3},
        ]
        report = summarize_track_windows(tracks, total_frames=10, fps=2, window_seconds=2)
        self.assertEqual(len(report["windows"]), 3)
        self.assertEqual(report["windows"][0]["newTrackIds"], 1)
        self.assertEqual(report["windows"][1]["distinctTrackIds"], 1)
        self.assertEqual(report["windows"][2]["newTrackIds"], 1)

    def test_rejects_invalid_window_configuration(self):
        with self.assertRaises(ValueError):
            summarize_track_windows([], total_frames=0, fps=5, window_seconds=30)
