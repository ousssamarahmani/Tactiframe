"""
config.py — Central configuration for TactiFrame.
All tuneable constants are defined here and imported by other modules.
Values can be overridden via environment variables.
"""

import os
from pathlib import Path


def _load_local_env() -> None:
    """Load simple KEY=VALUE settings from the repository's ignored .env file."""
    path = Path(__file__).with_name(".env")
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key and key.replace("_", "").isalnum():
            os.environ.setdefault(key, value.strip().strip('"').strip("'"))


_load_local_env()

# ── Perception ────────────────────────────────────────────────────────────────
YOLO_CONF_THRESHOLD: float = float(os.getenv("YOLO_CONF_THRESHOLD", "0.15"))
YOLO_WEIGHTS_PATH: str = os.getenv("YOLO_WEIGHTS_PATH", "models/best.pt")

# ── Zone Analyzer ─────────────────────────────────────────────────────────────
# rows × cols must be between 6 and 64 inclusive (Requirement 2.1)
ZONE_ROWS: int = int(os.getenv("ZONE_ROWS", "4"))
ZONE_COLS: int = int(os.getenv("ZONE_COLS", "3"))   # default: 4×3 = 12 zones

# ── Approval Gate ─────────────────────────────────────────────────────────────
APPROVAL_TIMEOUT_SECONDS: int = int(os.getenv("APPROVAL_TIMEOUT_SECONDS", "300"))

# ── Amazon Bedrock ────────────────────────────────────────────────────────────
BEDROCK_MODEL_ID: str = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")
AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
AWS_PROFILE: str = os.getenv("AWS_PROFILE", "")
AWS_ENABLED: bool = os.getenv("AWS_ENABLED", "false").lower() == "true"

# ── AWS S3 ────────────────────────────────────────────────────────────────────
S3_BUCKET: str = os.getenv("S3_BUCKET", "tactiframe-sessions")

# ── Amazon Bedrock AgentCore (optional) ──────────────────────────────────────
AGENTCORE_ENABLED: bool = os.getenv("AGENTCORE_ENABLED", "false").lower() == "true"
AGENTCORE_RUNTIME_ID: str = os.getenv("AGENTCORE_RUNTIME_ID", "")

# ── MCP Server ────────────────────────────────────────────────────────────────
# Supported values: "stdio" | "streamable-http"
MCP_TRANSPORT: str = os.getenv("MCP_TRANSPORT", "stdio")
MCP_HOST: str = os.getenv("MCP_HOST", "0.0.0.0")
MCP_PORT: int = int(os.getenv("MCP_PORT", "8001"))

# ── Session Store ─────────────────────────────────────────────────────────────
SESSION_DIR: str = os.getenv("SESSION_DIR", "data/sessions")
