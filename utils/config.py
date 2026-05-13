"""
utils/config.py
────────────────────────────────────────────────────────────────────────────────
Centralised configuration loader.

FIX: Searches for .env in multiple locations so it works regardless of
     which directory Streamlit/Python is launched from.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ── Find .env robustly — check multiple candidate locations ──────────────────
def _find_env_file() -> Path | None:
    candidates = [
        Path(__file__).resolve().parent.parent / ".env",   # project root (normal)
        Path.cwd() / ".env",                                # current working dir
        Path(__file__).resolve().parent / ".env",           # inside utils/
        Path.home() / ".env",                               # home dir fallback
    ]
    for p in candidates:
        if p.exists():
            return p
    return None

_env_path = _find_env_file()
if _env_path:
    load_dotenv(_env_path, override=True)
else:
    # .env not found — load from environment variables directly (Docker / CI)
    load_dotenv(override=True)

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    """Single source of truth for all application configuration."""

    # ── OpenAI ────────────────────────────────────────────────────────────────
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL:   str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # ── Email / SMTP ──────────────────────────────────────────────────────────
    EMAIL_HOST:      str = os.getenv("EMAIL_HOST", "smtp.gmail.com")
    EMAIL_PORT:      int = int(os.getenv("EMAIL_PORT", "587"))
    EMAIL_USER:      str = os.getenv("EMAIL_USER", "")
    EMAIL_PASSWORD:  str = os.getenv("EMAIL_PASSWORD", "")
    EMAIL_FROM_NAME: str = os.getenv("EMAIL_FROM_NAME", "Finance Team")

    # ── Application ───────────────────────────────────────────────────────────
    APP_ENV:   str  = os.getenv("APP_ENV", "development")
    LOG_LEVEL: str  = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR:   Path = BASE_DIR / os.getenv("LOG_DIR", "logs")
    DB_PATH:   Path = BASE_DIR / os.getenv("DB_PATH", "logs/follow_ups.db")

    # ── Auth ──────────────────────────────────────────────────────────────────
    APP_USERNAME: str = os.getenv("APP_USERNAME", "admin")
    APP_PASSWORD: str = os.getenv("APP_PASSWORD", "changeme123")

    # ── Data ──────────────────────────────────────────────────────────────────
    INVOICES_CSV: Path = BASE_DIR / "data" / "invoices.csv"

    # ── Escalation thresholds (days overdue) ──────────────────────────────────
    STAGE_1_DAYS: int = 1
    STAGE_2_DAYS: int = 15
    STAGE_3_DAYS: int = 30
    STAGE_4_DAYS: int = 60

    def validate(self) -> list[str]:
        errors = []
        if not self.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY is not set in .env")
        if not self.EMAIL_USER and self.APP_ENV == "production":
            errors.append("EMAIL_USER is not set (required in production)")
        self.LOG_DIR.mkdir(parents=True, exist_ok=True)
        return errors

    def debug_info(self) -> dict:
        """Return non-sensitive config info for debugging."""
        return {
            "env_file_found": str(_env_path) if _env_path else "NOT FOUND",
            "base_dir": str(BASE_DIR),
            "cwd": str(Path.cwd()),
            "api_key_set": bool(self.OPENAI_API_KEY),
            "api_key_prefix": self.OPENAI_API_KEY[:12] + "..." if self.OPENAI_API_KEY else "EMPTY",
            "model": self.OPENAI_MODEL,
            "csv_exists": self.INVOICES_CSV.exists(),
        }


config = Config()
