"""Write a structural TactiFrame evaluation.json for a completed session."""

import argparse
import json
from pathlib import Path

from agent.evaluation import evaluate_session


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    report = evaluate_session(args.run_dir)
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
