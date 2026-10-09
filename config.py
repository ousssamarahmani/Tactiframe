"""
config.py — Central configuration for TactiFrame.
All tuneable constants are defined here and imported by other modules.
Values can be overridden via environment variables.
"""

import os

# ── Perception ────────────────────────────────────────────────────────────────
YOLO_CONF_THRESHOLD: float = float(os.getenv("YOLO_CONF_THRESHOLD", "0.5"))
YOLO_WEIGHTS_PATH: str = os.getenv("YOLO_WEIGHTS_PATH", "models/yolo.pt")

# ── Zone Analyzer ─────────────────────────────────────────────────────────────
# rows × cols must be between 6 and 64 inclusive (Requirement 2.1)
ZONE_ROWS: int = int(os.getenv("ZONE_ROWS", "4"))
ZONE_COLS: int = int(os.getenv("ZONE_COLS", "3"))   # default: 4×3 = 12 zones

# ── Approval Gate ─────────────────────────────────────────────────────────────
APPROVAL_TIMEOUT_SECONDS: int = int(os.getenv("APPROVAL_TIMEOUT_SECONDS", "300"))

# ── Amazon Bedrock ────────────────────────────────────────────────────────────
BEDROCK_MODEL_ID: str = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")
AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")

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
