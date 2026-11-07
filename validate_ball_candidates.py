"""Validate raw ball candidates in an existing TactiFrame session without rerunning YOLO."""

import argparse
import json
from pathlib import Path

from cv.ball_validation import validate_ball_candidates
from run_pipeline import write_json


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--min-confidence", type=float, default=0.20)
    args = parser.parse_args()
    if not 0 < args.min_confidence <= 1:
        parser.error("--min-confidence must be in (0, 1]")

    run_dir = args.run_dir.resolve()
    run_path = run_dir / "run.json"
    run = json.loads(run_path.read_text(encoding="utf-8"))
    raw_path = run_dir / run.get("outputs", {}).get("ballObservations", "ball_observations.json")
    candidates = json.loads(raw_path.read_text(encoding="utf-8"))
    validated, summary = validate_ball_candidates(candidates, min_confidence=args.min_confidence)
    output_name = "ball_candidates_validated.json"
    write_json(run_dir / output_name, validated)
    run.setdefault("outputs", {})["validatedBallCandidates"] = output_name
    run.setdefault("counts", {})["validatedBallCandidates"] = len(validated)
    run["ballValidation"] = summary
    write_json(run_path, run)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
