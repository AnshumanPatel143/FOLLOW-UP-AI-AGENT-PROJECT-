"""
utils/invoice_processor.py
────────────────────────────────────────────────────────────────────────────────
Reads invoice data from CSV, validates records, detects overdue status,
and assigns an escalation stage to each overdue invoice.

Escalation stages:
    Stage 1 —  1–14 days overdue   → Friendly reminder
    Stage 2 — 15–29 days overdue   → Formal payment notice
    Stage 3 — 30–59 days overdue   → Urgent escalation
    Stage 4 — 60+ days overdue     → Final notice / legal warning
"""

import pandas as pd
from datetime import datetime, date
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from utils.config import config


# ── Date parsing helper ───────────────────────────────────────────────────────

_DATE_FORMATS = ["%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"]


def _parse_date(raw: str) -> date:
    """Try multiple date formats and return a date object."""
    raw = raw.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognised date format: '{raw}'")


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class Invoice:
    """Validated, enriched invoice record ready for AI processing."""
    invoice_id: str
    client_name: str
    client_email: str
    amount: float
    currency: str
    issue_date: date
    due_date: date
    status: str
    days_overdue: int
    contact_person: str
    company: str
    previous_reminders: int
    escalation_stage: int = 0
    escalation_label: str = ""

    @property
    def amount_formatted(self) -> str:
        """Human-readable amount, e.g. '$15,000.00'."""
        symbols = {"USD": "$", "EUR": "€", "GBP": "£", "INR": "₹"}
        sym = symbols.get(self.currency, self.currency + " ")
        return f"{sym}{self.amount:,.2f}"

    @property
    def is_overdue(self) -> bool:
        return self.status.lower() == "overdue"


# ── Stage assignment ──────────────────────────────────────────────────────────

STAGE_LABELS = {
    1: "Friendly Reminder",
    2: "Formal Notice",
    3: "Urgent Escalation",
    4: "Final / Legal Warning",
}


def assign_escalation_stage(days_overdue: int) -> tuple[int, str]:
    """Return (stage_number, stage_label) based on days overdue."""
    if days_overdue >= config.STAGE_4_DAYS:
        stage = 4
    elif days_overdue >= config.STAGE_3_DAYS:
        stage = 3
    elif days_overdue >= config.STAGE_2_DAYS:
        stage = 2
    else:
        stage = 1
    return stage, STAGE_LABELS[stage]


# ── CSV loader & validator ────────────────────────────────────────────────────

REQUIRED_COLUMNS = {
    "invoice_id", "client_name", "client_email", "amount",
    "currency", "issue_date", "due_date", "status",
    "days_overdue", "contact_person", "company", "previous_reminders",
}


def load_invoices(csv_path: Optional[Path] = None) -> tuple[list[Invoice], list[str]]:
    """
    Load and validate invoices from CSV.

    Returns:
        invoices: list of validated Invoice objects
        errors:   list of row-level error strings (non-fatal)
    """
    path = csv_path or config.INVOICES_CSV
    if not path.exists():
        raise FileNotFoundError(f"Invoice CSV not found: {path}")

    df = pd.read_csv(path, dtype=str).fillna("")

    # ── Column validation ─────────────────────────────────────────────────────
    missing_cols = REQUIRED_COLUMNS - set(df.columns)
    if missing_cols:
        raise ValueError(f"CSV missing required columns: {missing_cols}")

    invoices: list[Invoice] = []
    errors: list[str] = []

    for idx, row in df.iterrows():
        row_id = row.get("invoice_id", f"row-{idx}")
        try:
            amount = float(row["amount"])
            days_overdue = int(row["days_overdue"])
            previous_reminders = int(row["previous_reminders"])
            issue_date = _parse_date(row["issue_date"])
            due_date = _parse_date(row["due_date"])

            # Basic email format check
            email = row["client_email"].strip()
            if "@" not in email or "." not in email.split("@")[-1]:
                errors.append(f"{row_id}: invalid email '{email}', skipping")
                continue

            stage, label = assign_escalation_stage(days_overdue)

            invoices.append(Invoice(
                invoice_id=row_id.strip(),
                client_name=row["client_name"].strip(),
                client_email=email,
                amount=amount,
                currency=row["currency"].strip().upper(),
                issue_date=issue_date,
                due_date=due_date,
                status=row["status"].strip().lower(),
                days_overdue=days_overdue,
                contact_person=row["contact_person"].strip(),
                company=row["company"].strip(),
                previous_reminders=previous_reminders,
                escalation_stage=stage,
                escalation_label=label,
            ))
        except Exception as exc:
            errors.append(f"{row_id}: parse error — {exc}")

    return invoices, errors


def get_overdue_invoices(invoices: list[Invoice]) -> list[Invoice]:
    """Filter to only overdue invoices, sorted by days_overdue descending."""
    return sorted(
        [inv for inv in invoices if inv.is_overdue],
        key=lambda i: i.days_overdue,
        reverse=True,
    )


def get_summary_stats(invoices: list[Invoice]) -> dict:
    """Return dashboard-ready summary statistics."""
    overdue = get_overdue_invoices(invoices)
    total_overdue_amount = sum(i.amount for i in overdue)
    by_stage = {s: [] for s in range(1, 5)}
    for inv in overdue:
        by_stage[inv.escalation_stage].append(inv)

    return {
        "total_invoices": len(invoices),
        "overdue_count": len(overdue),
        "paid_count": sum(1 for i in invoices if i.status == "paid"),
        "pending_count": sum(1 for i in invoices if i.status == "pending"),
        "total_overdue_amount": total_overdue_amount,
        "by_stage": {k: len(v) for k, v in by_stage.items()},
        "avg_days_overdue": (
            sum(i.days_overdue for i in overdue) / len(overdue) if overdue else 0
        ),
    }
