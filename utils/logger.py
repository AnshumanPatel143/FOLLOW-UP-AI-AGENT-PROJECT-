"""
utils/logger.py
────────────────────────────────────────────────────────────────────────────────
Persistent logging for all email generation and send events.
Stores records in both:
  - SQLite database  (logs/follow_ups.db)  — queryable, structured
  - JSON log file    (logs/follow_ups.json) — human-readable, portable

Tables:
  email_logs  — one row per email generated/sent
"""

import json
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from utils.config import config

logger = logging.getLogger(__name__)


# ── Schema ────────────────────────────────────────────────────────────────────

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS email_logs (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at        TEXT NOT NULL,
    invoice_id        TEXT NOT NULL,
    client_name       TEXT,
    client_email      TEXT,
    amount            REAL,
    currency          TEXT,
    days_overdue      INTEGER,
    escalation_stage  INTEGER,
    escalation_label  TEXT,
    email_subject     TEXT,
    email_body        TEXT,
    send_status       TEXT,           -- 'sent' | 'dry_run' | 'failed' | 'generated'
    send_error        TEXT,
    model_used        TEXT,
    session_id        TEXT
)
"""


# ── Logger class ──────────────────────────────────────────────────────────────

class FollowUpLogger:
    """
    Records every email generation and send event.
    Initialises the SQLite DB on first use.
    """

    def __init__(
        self,
        db_path: Optional[Path] = None,
        json_path: Optional[Path] = None,
    ):
        self.db_path = db_path or config.DB_PATH
        self.json_path = json_path or (config.LOG_DIR / "follow_ups.json")
        self._init_db()

    def _init_db(self):
        """Create tables if they don't exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(CREATE_TABLE_SQL)
            conn.commit()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def log_email(
        self,
        invoice_id: str,
        client_name: str,
        client_email: str,
        amount: float,
        currency: str,
        days_overdue: int,
        escalation_stage: int,
        escalation_label: str,
        email_subject: str,
        email_body: str,
        send_status: str,
        model_used: str,
        send_error: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> int:
        """Insert a log record. Returns the new row ID."""
        record = {
            "created_at": datetime.utcnow().isoformat(),
            "invoice_id": invoice_id,
            "client_name": client_name,
            "client_email": client_email,
            "amount": amount,
            "currency": currency,
            "days_overdue": days_overdue,
            "escalation_stage": escalation_stage,
            "escalation_label": escalation_label,
            "email_subject": email_subject,
            "email_body": email_body,
            "send_status": send_status,
            "send_error": send_error,
            "model_used": model_used,
            "session_id": session_id,
        }

        # ── SQLite ─────────────────────────────────────────────────────────
        with self._get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO email_logs
                   (created_at, invoice_id, client_name, client_email, amount, currency,
                    days_overdue, escalation_stage, escalation_label, email_subject,
                    email_body, send_status, send_error, model_used, session_id)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                list(record.values()),
            )
            row_id = cursor.lastrowid
            conn.commit()

        # ── JSON append ────────────────────────────────────────────────────
        self._append_json(record)

        logger.debug("Logged email event for invoice %s (id=%d)", invoice_id, row_id)
        return row_id

    def _append_json(self, record: dict):
        """Append a record to the JSON log file (creates if missing)."""
        self.json_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            if self.json_path.exists():
                with open(self.json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = []
            data.append(record)
            with open(self.json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as exc:
            logger.warning("JSON log write failed: %s", exc)

    def get_all_logs(self) -> list[dict]:
        """Return all log records as a list of dicts."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM email_logs ORDER BY created_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def get_logs_for_invoice(self, invoice_id: str) -> list[dict]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM email_logs WHERE invoice_id = ? ORDER BY created_at DESC",
                (invoice_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def clear_logs(self):
        """Delete all log records (useful for demo resets)."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM email_logs")
            conn.commit()
        if self.json_path.exists():
            self.json_path.write_text("[]")


# Singleton
follow_up_logger = FollowUpLogger()
