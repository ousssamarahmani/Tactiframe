"""Manually calibrated, image-space pitch polygons for a specific clip."""

import json
from pathlib import Path

import cv2
import numpy as np


class FieldPolygonTimeline:
    def __init__(self, keyframes: list[dict], frame_size: tuple[int, int],
                 video_checksum: str):
        if len(keyframes) < 1:
            raise ValueError("At least one polygon keyframe is required")
        if frame_size[0] <= 0 or frame_size[1] <= 0:
            raise ValueError("Invalid calibration frame size")
        if not video_checksum.startswith("sha256:"):
            raise ValueError("Calibration must identify its exact video checksum")
        frames = [int(k["frame"]) for k in keyframes]
        if frames != sorted(set(frames)):
            raise ValueError("Polygon keyframes must have unique increasing frame numbers")
        count = len(keyframes[0]["points"])
        if count < 3 or any(len(k["points"]) != count for k in keyframes):
            raise ValueError("Polygon keyframes need the same number of >=3 points")
        width, height = frame_size
        polygons = []
        for keyframe in keyframes:
            points = np.asarray(keyframe["points"], dtype=np.float32)
            if points.shape != (count, 2) or not np.isfinite(points).all():
                raise ValueError("Invalid polygon coordinates")
            if (points[:, 0].min() < 0 or points[:, 0].max() > width
                    or points[:, 1].min() < 0 or points[:, 1].max() > height):
                raise ValueError("Polygon coordinates exceed the calibration frame")
            if abs(cv2.contourArea(points)) < width * height * 0.05:
                raise ValueError("Polygon area is too small")
            polygons.append(points)
        self.frames = frames
        self.polygons = polygons
        self.frame_size = frame_size
        self.video_checksum = video_checksum

    @classmethod
    def from_file(cls, path: Path, *, video_checksum: str,
                  frame_size: tuple[int, int]) -> "FieldPolygonTimeline":
        config = json.loads(path.read_text(encoding="utf-8"))
        if config.get("videoChecksum") != video_checksum:
            raise ValueError("Field polygon calibration is for another video")
        if tuple(config.get("frameSize", [])) != frame_size:
            raise ValueError("Field polygon calibration has a different frame size")
        return cls(config["keyframes"], frame_size, video_checksum)

    def polygon_at(self, frame: int) -> np.ndarray:
        if frame <= self.frames[0]:
            return self.polygons[0]
        if frame >= self.frames[-1]:
            return self.polygons[-1]
        index = int(np.searchsorted(self.frames, frame, side="right"))
        before, after = index - 1, index
        fraction = (frame - self.frames[before]) / (self.frames[after] - self.frames[before])
        return self.polygons[before] * (1 - fraction) + self.polygons[after] * fraction

    def contains(self, frame: int, x: float, y: float, margin_px: float = 5.0) -> bool:
        polygon = self.polygon_at(frame)
        distance = cv2.pointPolygonTest(polygon, (float(x), float(y)), True)
        return distance >= -margin_px
