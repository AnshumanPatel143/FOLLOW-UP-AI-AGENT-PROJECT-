"""
tests/test_invoice_processor.py
────────────────────────────────────────────────────────────────────────────────
Unit tests for utils/invoice_processor.py

Run: python -m pytest tests/ -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import tempfile
import csv
from pathlib import Path
from datetime import date, timedelta

from utils.invoice_processor import (
    Invoice,
    load_invoices,
    get_overdue_invoices,
    get_summary_stats,
    assign_escalation_stage,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

VALID_CSV_ROWS = [
    {
        "invoice_id": "TEST-001",
        "client_name": "ACME Corp",
        "client_email": "billing@acme.com",
        "amount": "5000",
        "currency": "USD",
        "issue_date": "2024-01-01",
        "due_date": "2024-01-31",
        "status": "overdue",
        "days_overdue": "45",
        "contact_person": "John Doe",
        "company": "ACME Corporation",
        "previous_reminders": "2",
    },
    {
        "invoice_id": "TEST-002",
        "client_name": "Globex",
        "client_email": "ap@globex.com",
        "amount": "12000",
        "currency": "USD",
        "issue_date": "2024-02-01",
        "due_date": "2024-03-01",
        "status": "paid",
        "days_overdue": "0",
        "contact_person": "Jane Smith",
        "company": "Globex Inc",
        "previous_reminders": "0",
    },
    {
        "invoice_id": "TEST-003",
        "client_name": "MegaCorp",
        "client_email": "finance@megacorp.io",
        "amount": "8500",
        "currency": "USD",
        "issue_date": "2024-01-15",
        "due_date": "2024-02-14",
        "status": "overdue",
        "days_overdue": "80",
        "contact_person": "Bob Lee",
        "company": "MegaCorp Ltd",
        "previous_reminders": "3",
    },
]


def make_csv(rows: list[dict], path: Path):
    """Write rows to a CSV file for testing."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=VALID_CSV_ROWS[0].keys())
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture
def valid_csv(tmp_path):
    p = tmp_path / "invoices.csv"
    make_csv(VALID_CSV_ROWS, p)
    return p


# ── Tests: assign_escalation_stage ────────────────────────────────────────────

class TestEscalationStage:
    def test_stage_1_early_days(self):
        stage, label = assign_escalation_stage(5)
        assert stage == 1
        assert "Friendly" in label

    def test_stage_2_boundary(self):
        stage, _ = assign_escalation_stage(15)
        assert stage == 2

    def test_stage_3_boundary(self):
        stage, _ = assign_escalation_stage(30)
        assert stage == 3

    def test_stage_4_boundary(self):
        stage, label = assign_escalation_stage(60)
        assert stage == 4
        assert "Legal" in label or "Final" in label

    def test_stage_4_extreme(self):
        stage, _ = assign_escalation_stage(200)
        assert stage == 4

    def test_stage_1_one_day(self):
        stage, _ = assign_escalation_stage(1)
        assert stage == 1


# ── Tests: load_invoices ──────────────────────────────────────────────────────

class TestLoadInvoices:
    def test_loads_all_rows(self, valid_csv):
        invoices, errors = load_invoices(valid_csv)
        assert len(invoices) == 3
        assert errors == []

    def test_invoice_fields(self, valid_csv):
        invoices, _ = load_invoices(valid_csv)
        inv = next(i for i in invoices if i.invoice_id == "TEST-001")
        assert inv.client_name == "ACME Corp"
        assert inv.amount == 5000.0
        assert inv.currency == "USD"
        assert inv.days_overdue == 45

    def test_escalation_assigned(self, valid_csv):
        invoices, _ = load_invoices(valid_csv)
        inv = next(i for i in invoices if i.invoice_id == "TEST-001")
        assert inv.escalation_stage == 3  # 45 days → stage 3

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_invoices(Path("/nonexistent/path.csv"))

    def test_invalid_email_skipped(self, tmp_path):
        bad_row = {**VALID_CSV_ROWS[0], "invoice_id": "BAD-001", "client_email": "not-an-email"}
        p = tmp_path / "bad.csv"
        make_csv([bad_row], p)
        invoices, errors = load_invoices(p)
        assert len(invoices) == 0
        assert any("invalid email" in e for e in errors)

    def test_amount_formatted(self, valid_csv):
        invoices, _ = load_invoices(valid_csv)
        inv = next(i for i in invoices if i.invoice_id == "TEST-001")
        assert "$5,000.00" == inv.amount_formatted


# ── Tests: get_overdue_invoices ───────────────────────────────────────────────

class TestGetOverdueInvoices:
    def test_filters_to_overdue_only(self, valid_csv):
        invoices, _ = load_invoices(valid_csv)
        overdue = get_overdue_invoices(invoices)
        assert all(i.is_overdue for i in overdue)
        assert len(overdue) == 2  # TEST-001 and TEST-003

    def test_sorted_by_days_desc(self, valid_csv):
        invoices, _ = load_invoices(valid_csv)
        overdue = get_overdue_invoices(invoices)
        days = [i.days_overdue for i in overdue]
        assert days == sorted(days, reverse=True)

    def test_no_overdue_returns_empty(self, tmp_path):
        paid_row = {**VALID_CSV_ROWS[1]}  # status: paid
        p = tmp_path / "paid.csv"
        make_csv([paid_row], p)
        invoices, _ = load_invoices(p)
        overdue = get_overdue_invoices(invoices)
        assert overdue == []


# ── Tests: get_summary_stats ──────────────────────────────────────────────────

class TestSummaryStats:
    def test_counts(self, valid_csv):
        invoices, _ = load_invoices(valid_csv)
        stats = get_summary_stats(invoices)
        assert stats["total_invoices"] == 3
        assert stats["overdue_count"] == 2
        assert stats["paid_count"] == 1

    def test_total_overdue_amount(self, valid_csv):
        invoices, _ = load_invoices(valid_csv)
        stats = get_summary_stats(invoices)
        # TEST-001: 5000, TEST-003: 8500
        assert stats["total_overdue_amount"] == 13500.0

    def test_by_stage(self, valid_csv):
        invoices, _ = load_invoices(valid_csv)
        stats = get_summary_stats(invoices)
        # TEST-001: 45d → Stage 3, TEST-003: 80d → Stage 4
        assert stats["by_stage"][3] == 1
        assert stats["by_stage"][4] == 1
