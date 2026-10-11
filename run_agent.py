"""Run the TactiFrame local agent loop; leave the plan for coach approval."""

import argparse
import json
from pathlib import Path

from agent.orchestrator import run_agent
from agent.tools import ToolLayer


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, help="Existing completed perception run")
    parser.add_argument("--video", type=Path, help="New clip to process")
    parser.add_argument("--model", type=Path, help="Football YOLO checkpoint")
    parser.add_argument("--field-polygons", type=Path)
    parser.add_argument("--output-dir", type=Path, help="Required for a new perception run")
    args = parser.parse_args()
    if args.run_dir is None and not (args.video and args.model and args.output_dir):
        parser.error("Use --run-dir or --video, --model, and --output-dir")
    tools = ToolLayer()
    result = run_agent(tools, run_dir=args.run_dir, video=args.video,
                       model=args.model, field_polygons=args.field_polygons,
                       output_dir=args.output_dir)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
