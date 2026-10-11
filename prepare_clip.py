"""Create a smaller, time-preserving observation input from a local match video."""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import cv2


def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(chunk)
    return f"sha256:{sha.hexdigest()}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fps", type=float, default=5.0)
    parser.add_argument("--width", type=int, default=1280)
    args = parser.parse_args()

    if args.output.exists():
        raise FileExistsError(args.output)
    if args.fps <= 0 or args.width <= 0:
        raise ValueError("fps and width must be positive")
    cap = cv2.VideoCapture(str(args.input))
    if not cap.isOpened():
        raise ValueError(f"Could not open {args.input}")
    source_fps = float(cap.get(cv2.CAP_PROP_FPS))
    source_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    source_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    source_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if source_fps <= 0 or source_width <= 0 or source_height <= 0:
        raise ValueError("Input video has invalid metadata")
    stride = round(source_fps / args.fps)
    if stride < 1 or abs(source_fps / stride - args.fps) > 0.01:
        raise ValueError("Requested fps must be an integer stride of source fps")
    target_fps = source_fps / stride
    target_height = round(source_height * args.width / source_width)
    if target_height % 2:
        target_height += 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(
        str(args.output), cv2.VideoWriter_fourcc(*"mp4v"), target_fps, (args.width, target_height)
    )
    if not writer.isOpened():
        raise ValueError(f"Could not write {args.output}")
    decoded = written = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if decoded % stride == 0:
                writer.write(cv2.resize(frame, (args.width, target_height), interpolation=cv2.INTER_AREA))
                written += 1
            decoded += 1
    finally:
        cap.release()
        writer.release()
    if written == 0 or args.output.stat().st_size == 0:
        raise RuntimeError("No output frames were written")
    manifest = {
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "source": {"path": str(args.input.resolve()), "sha256": digest(args.input), "frames": source_frames,
                   "fps": source_fps, "width": source_width, "height": source_height},
        "prepared": {"path": str(args.output.resolve()), "sha256": digest(args.output), "frames": written,
                     "fps": target_fps, "width": args.width, "height": target_height},
        "frameStride": stride,
        "scope": "entire source duration sampled at a lower frame rate; audio omitted",
    }
    args.output.with_suffix(".json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"sourceFramesDecoded": decoded, "preparedFrames": written,
                      "output": str(args.output), "fps": target_fps}, indent=2))


if __name__ == "__main__":
    main()
