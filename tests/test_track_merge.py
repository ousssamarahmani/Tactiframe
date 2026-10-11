"""Prevent one ID from being assigned to two players in the same frame."""

import os
import unittest
from pathlib import Path

import numpy as np


config_dir = Path(__file__).resolve().parents[1] / "data" / "ultralytics"
(config_dir / "Ultralytics").mkdir(parents=True, exist_ok=True)
os.environ.setdefault("YOLO_CONFIG_DIR", str(config_dir))

from cv.tracker import PlayerTracker


class TestTrackMerge(unittest.TestCase):
    def test_appearance_merge_never_overlaps_an_earlier_merged_track(self):
        # B and C each precede A, but B and C overlap each other.
        tracks = [
            {"frame": frame, "track_id": track_id, "x": float(track_id), "y": 0.0}
            for track_id, frames in ((1, range(10, 21)), (2, range(0, 6)), (3, range(3, 8)))
            for frame in frames
        ]
        colors = {track_id: [np.array([20., 30., 40.])] * 2 for track_id in (1, 2, 3)}
        worker = PlayerTracker.__new__(PlayerTracker)
        merged = worker._merge_by_appearance(tracks, colors, max_gap=20)
        worker._assert_unique_frame_ids(merged, "test")
        ids = {item["track_id"] for item in merged}
        self.assertEqual(len(ids), 2)


if __name__ == "__main__":
    unittest.main()
