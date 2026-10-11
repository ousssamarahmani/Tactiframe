import numpy as np
import unittest

from cv.detection_filter import filter_detections, right_goal_line
from cv.field_polygon import FieldPolygonTimeline


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

    def test_manual_polygon_rejects_green_runoff_before_tracking(self):
        frame = np.full((120, 180, 3), (20, 110, 20), dtype=np.uint8)
        polygon = FieldPolygonTimeline([
            {"frame": 0, "points": [[0, 20], [100, 10], [180, 75], [180, 120], [0, 120]]},
        ], (180, 120), "sha256:test")
        boxes = np.array([
            [145, 18, 160, 38],  # staff, green runoff outside diagonal
            [120, 70, 135, 95],  # on-pitch player
            [145, 35, 151, 41],  # ball outside
        ], dtype=float)
        keep, rejected = filter_detections(
            frame, boxes, np.array([0.9, 0.9, 0.9]), np.array([2, 2, 0]),
            player_conf=0.3, ball_conf=0.15, min_player_height=10,
            use_pitch_mask=True, field_polygon=polygon, frame_index=0,
        )
        self.assertEqual(keep.tolist(), [False, True, False])
        self.assertEqual(rejected["off_pitch_rejected"], 2)

    def test_polygon_interpolates_and_checks_video_identity(self):
        polygon = FieldPolygonTimeline([
            {"frame": 0, "points": [[0, 10], [90, 10], [90, 90], [0, 90]]},
            {"frame": 10, "points": [[10, 10], [100, 10], [100, 90], [10, 90]]},
        ], (100, 100), "sha256:test")
        self.assertAlmostEqual(polygon.polygon_at(5)[0, 0], 5)
        self.assertTrue(polygon.contains(5, 50, 50))
        self.assertFalse(polygon.contains(5, 0, 50, margin_px=0))
