"""Class, confidence, size, and visible-pitch filters applied before tracking."""

from collections import Counter

import cv2
import numpy as np


BALL, GOALKEEPER, PLAYER, REFEREE = 0, 1, 2, 3
ALLOWED_CLASSES = {BALL, GOALKEEPER, PLAYER, REFEREE}


def pitch_mask(frame: np.ndarray) -> np.ndarray:
    """Find visible green turf in a frame; this is a camera-space ROI, not pitch coordinates."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    green = cv2.inRange(hsv, (28, 35, 25), (95, 255, 255))
    return cv2.morphologyEx(green, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))


def right_goal_line(frame: np.ndarray) -> tuple[float, float] | None:
    """Estimate the visible right goal line as y = slope*x + intercept.

    Only accept a long diagonal from the far corner toward the right image
    border. When the line is not visible, return None instead of guessing.
    """
    height, width = frame.shape[:2]
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    white = cv2.inRange(hsv, (0, 0, 110), (179, 120, 255))
    white[: int(height * 0.07)] = 0
    white[int(height * 0.58) :] = 0
    white[:, : int(width * 0.55)] = 0
    lines = cv2.HoughLinesP(
        white, 1, np.pi / 360, threshold=25,
        minLineLength=int(width * 0.12), maxLineGap=35,
    )
    if lines is None:
        return None
    candidates = []
    for x1, y1, x2, y2 in lines.reshape(-1, 4):
        if x1 > x2:
            x1, y1, x2, y2 = x2, y2, x1, y1
        dx = float(x2 - x1)
        if dx < width * 0.12 or x1 < width * 0.55 or x1 > width * 0.84:
            continue
        slope = float(y2 - y1) / dx
        intercept = float(y1) - slope * float(x1)
        right_y = slope * (width - 1) + intercept
        if (0.55 <= slope <= 1.45 and y1 <= height * 0.20
                and x2 >= width * 0.90 and height * 0.28 <= right_y <= height * 0.55):
            candidates.append((dx, right_y, slope, intercept))
    if not candidates:
        return None
    _, _, slope, intercept = max(candidates)
    return slope, intercept


def filter_detections(
    frame: np.ndarray,
    xyxy: np.ndarray,
    confidences: np.ndarray,
    class_ids: np.ndarray,
    *,
    player_conf: float,
    ball_conf: float,
    min_player_height: int,
    use_pitch_mask: bool,
) -> tuple[np.ndarray, Counter]:
    """Return a keep mask and rejection counts; test the player's feet against turf."""
    h, w = frame.shape[:2]
    turf = pitch_mask(frame) if use_pitch_mask else None
    turf_support = cv2.blur((turf > 0).astype(np.float32), (19, 19)) if turf is not None else None
    right_line = right_goal_line(frame) if use_pitch_mask else None
    keep = np.zeros(len(xyxy), dtype=bool)
    rejected = Counter()

    for i, (box, confidence, class_id) in enumerate(zip(xyxy, confidences, class_ids)):
        cls = int(class_id)
        x1, y1, x2, y2 = box
        if cls not in ALLOWED_CLASSES:
            rejected["class"] += 1
            continue
        if confidence < (ball_conf if cls == BALL else player_conf):
            rejected["confidence"] += 1
            continue
        if x2 <= x1 or y2 <= y1 or (cls != BALL and y2 - y1 < min_player_height):
            rejected["size"] += 1
            continue
        if turf_support is not None:
            px = min(w - 1, max(0, int((x1 + x2) / 2)))
            py = min(h - 1, max(0, int((y1 + y2) / 2 if cls == BALL else y2)))
            if right_line is not None:
                slope, intercept = right_line
                boundary_x = (py - intercept) / slope
                if px > boundary_x + 5:
                    rejected["outside_right_goal_line"] += 1
                    continue
            if turf_support[py, px] < 0.6:
                rejected["pitch"] += 1
                continue
        keep[i] = True
    return keep, rejected
