"""Compare evaluation and track-diagnostic outputs from two TactiFrame sessions."""

import argparse
import json
from pathlib import Path

from cv.tracking_ab import compare_tracking_runs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-run-dir", type=Path, required=True)
    parser.add_argument("--candidate-run-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(compare_tracking_runs(args.baseline_run_dir, args.candidate_run_dir), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
