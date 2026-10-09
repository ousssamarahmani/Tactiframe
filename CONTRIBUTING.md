# Contributing to TactiFrame

TactiFrame is a hackathon project. Contributions that improve correctness, test coverage, or documentation are welcome.

## Getting Started

```bash
git clone https://github.com/ousssamarahmani/tactiframe.git
cd tactiframe
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Ground Rules

- **Never modify** `cv/detector.py`, `cv/tracker.py`, `cv/team_classifier.py`, or `cv/ball_interpolation.py` — these are copied from TactiScout-CV as-is.
- All business logic lives in `agent/tools.py`. The MCP server and FastAPI adapter must remain thin wrappers with zero duplicated logic.
- Every new invariant should be expressed as a Hypothesis property test in `tests/`.
- Run `pytest tests/ -v` before opening a PR. No live AWS credentials are needed.
- No model weight files, match video files, or `.env` files in commits.

## Coding Style

- Python 3.11+, type hints on all function signatures.
- `config.py` for any new tuneable constant — no magic numbers inline.
- Error responses always return `{"error": "..."}` — never raise exceptions to callers.

## Opening a PR

1. Branch from `master`: `git checkout -b feat/your-feature`
2. Add or update tests for your change.
3. `pytest tests/ -v` must pass.
4. Open a PR with a short description of what changed and why.
