"""Central configuration. Reads the repo-root .env (base_url / api_key / model)."""
import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent

# .env lives at repo root locally; in Docker it is mounted next to the app.
for candidate in (REPO_ROOT / ".env", BACKEND_DIR / ".env"):
    if candidate.exists():
        load_dotenv(candidate)
        break
else:
    load_dotenv()


def _env(*names: str, default: str = "") -> str:
    for n in names:
        v = os.environ.get(n)
        if v:
            return v.strip()
    return default


LLM_BASE_URL = _env("base_url", "BASE_URL", "LLM_BASE_URL")
LLM_API_KEY = _env("api_key", "API_KEY", "LLM_API_KEY")
LLM_MODEL = _env("model", "MODEL", "LLM_MODEL", default="MiniMax-M3")

DATA_DIR = Path(_env("DATA_DIR", default=str(BACKEND_DIR / "data")))
WORKSPACES_DIR = Path(_env("WORKSPACES_DIR", default=str(BACKEND_DIR / "workspaces")))
LESSONS_DIR = BACKEND_DIR / "content" / "lessons"

DATA_DIR.mkdir(parents=True, exist_ok=True)
WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "tutor.db"

# Tool-runner limits
RUN_TIMEOUT_SECONDS = int(_env("RUN_TIMEOUT_SECONDS", default="20"))
RUN_OUTPUT_LIMIT = 12_000  # chars of stdout/stderr kept
MAX_TOOL_ROUNDS = 8

# Memory
COGNEE_ENABLED = _env("COGNEE_ENABLED", default="1") not in ("0", "false", "no")
