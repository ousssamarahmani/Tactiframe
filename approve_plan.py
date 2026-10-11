"""Record a coach's explicit decision on a TactiFrame draft plan."""

import argparse
import json
from pathlib import Path

from agent.tools import ToolLayer


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--decision", choices=["approved", "rejected"], required=True)
    parser.add_argument("--coach", required=True)
    args = parser.parse_args()
    tools = ToolLayer()
    tools.run_dir = args.run_dir.resolve()
    trace_path = tools.run_dir / "trace.json"
    if trace_path.is_file():
        prior_trace = json.loads(trace_path.read_text(encoding="utf-8"))
        tools.run_id = prior_trace.get("runId")
        tools.trace = prior_trace["steps"]
    else:
        tools.run_id = json.loads((tools.run_dir / "run.json").read_text(encoding="utf-8"))["runId"]
    print(json.dumps(tools.request_approval(decision=args.decision, coach=args.coach), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
