import numpy as np
import unittest

from cv.detection_filter import filter_detections, right_goal_line


class TestDetectionFilter(unittest.TestCase):
    def test_filters_before_tracking_using_feet_and_class_thresholds(self):
        frame = np.zeros((120, 180, 3), dtype=np.uint8)
        frame[30:100, 10:150] = (20, 110, 20)  # visible turf
        boxes = np.array([
            [20, 30, 35, 80],    # player, feet on turf
            [155, 5, 170, 40],   # staff beyond the pitch
            [50, 45, 55, 50],    # plausible ball with lower threshold
            [60, 45, 75, 80],    # player below player threshold
            [85, 45, 100, 80],   # unrelated class
        ], dtype=float)
        keep, rejected = filter_detections(
            frame, boxes, np.array([0.5, 0.8, 0.18, 0.18, 0.9]),
            np.array([2, 2, 0, 2, 5]), player_conf=0.3, ball_conf=0.15,
            min_player_height=10, use_pitch_mask=True,
        )
        self.assertEqual(keep.tolist(), [True, False, True, False, False])
        self.assertEqual(rejected, {"pitch": 1, "confidence": 1, "class": 1})

    def test_right_goal_line_rejects_green_runoff_staff(self):
        frame = np.full((720, 1280, 3), (20, 110, 20), dtype=np.uint8)
        import cv2
        cv2.line(frame, (1000, 80), (1279, 325), (255, 255, 255), 2)
        boxes = np.array([
            [1160, 60, 1175, 100],   # staff outside goal line
            [1230, 145, 1250, 180],  # second staff outside
            [1090, 260, 1110, 300],  # goalkeeper inside
        ], dtype=float)
        keep, rejected = filter_detections(
            frame, boxes, np.array([0.8, 0.8, 0.8]),
            np.array([2, 2, 1]), player_conf=0.3, ball_conf=0.15,
            min_player_height=10, use_pitch_mask=True,
        )
        self.assertIsNotNone(right_goal_line(frame))
        self.assertEqual(keep.tolist(), [False, False, True])
        self.assertEqual(rejected["outside_right_goal_line"], 2)
