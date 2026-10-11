"""Image-relative zones for uncalibrated broadcast footage.

These zones describe the visible frame, not metric pitch coordinates. Camera
movement can change their football meaning, so downstream users must retain
the coordinate system label.
"""


def zone_for_point(x: float, y: float, width: int, height: int) -> str:
    if width <= 0 or height <= 0:
        raise ValueError("Frame dimensions must be positive")
    column = min(2, max(0, int(3 * x / width)))
    row = min(2, max(0, int(3 * y / height)))
    return f"r{row}c{column}"
