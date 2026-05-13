"""
agent.py
────────────────────────────────────────────────────────────────────────────────
AI Finance Credit Follow-Up Agent — Orchestrator

This is the main entry-point for running the agent programmatically (CLI / cron).
For the web dashboard, use: streamlit run app.py

Pipeline:
    1. Load invoices from CSV
    2. Filter overdue invoices
    3. Assign escalation stages
    4. Generate personalised AI emails (LangChain + OpenAI)
    5. Send emails (or dry-run)
    6. Log all results to SQLite + JSON

Usage:
    python agent.py                    # dry-run (no emails sent)
    python agent.py --send             # actually send emails
    python agent.py --invoice INV-001  # process a single invoice
"""

import argparse
import logging
import sys
import uuid
from pathlib import Path

from utils.config import config
from utils.invoice_processor import load_invoices, get_overdue_invoices
from utils.email_generator import EmailGenerator
from utils.email_sender import EmailSender
from utils.logger import follow_up_logger

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(config.LOG_DIR / "agent.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def run_agent(
    dry_run: bool = True,
    invoice_id_filter: str | None = None,
    sender_name: str = "Finance Team",
) -> dict:
    """
    Run the full follow-up pipeline.

    Returns:
        A results summary dict suitable for display or API response.
    """
    session_id = str(uuid.uuid4())[:8]
    logger.info("═══ Agent session %s starting (dry_run=%s) ═══", session_id, dry_run)

    # ── Validate config ───────────────────────────────────────────────────────
    errors = config.validate()
    if errors:
        for err in errors:
            logger.warning("Config warning: %s", err)

    # ── Load invoices ─────────────────────────────────────────────────────────
    logger.info("Loading invoices from %s", config.INVOICES_CSV)
    invoices, parse_errors = load_invoices()

    if parse_errors:
        for err in parse_errors:
            logger.warning("Parse error: %s", err)

    overdue = get_overdue_invoices(invoices)
    logger.info("Found %d total invoices, %d overdue", len(invoices), len(overdue))

    # ── Optional single-invoice filter ───────────────────────────────────────
    if invoice_id_filter:
        overdue = [i for i in overdue if i.invoice_id == invoice_id_filter]
        if not overdue:
            logger.error("Invoice %s not found or not overdue", invoice_id_filter)
            return {"error": f"Invoice {invoice_id_filter} not found or not overdue"}

    # ── Generate emails ───────────────────────────────────────────────────────
    gen = EmailGenerator()
    sender = EmailSender(dry_run=dry_run)

    results = []
    for invoice in overdue:
        logger.info(
            "Processing %s | %s | Stage %d | %d days overdue",
            invoice.invoice_id, invoice.client_name,
            invoice.escalation_stage, invoice.days_overdue,
        )

        # Generate
        email = gen.generate(invoice, sender_name=sender_name)

        # Send
        send_result = sender.send(invoice.client_email, email)

        # Determine status string
        if not email.is_successful:
            status = "failed"
        elif send_result.dry_run:
            status = "dry_run"
        elif send_result.success:
            status = "sent"
        else:
            status = "failed"

        # Log
        follow_up_logger.log_email(
            invoice_id=invoice.invoice_id,
            client_name=invoice.client_name,
            client_email=invoice.client_email,
            amount=invoice.amount,
            currency=invoice.currency,
            days_overdue=invoice.days_overdue,
            escalation_stage=invoice.escalation_stage,
            escalation_label=invoice.escalation_label,
            email_subject=email.subject,
            email_body=email.body,
            send_status=status,
            model_used=email.model_used,
            send_error=send_result.error or email.error,
            session_id=session_id,
        )

        results.append({
            "invoice_id": invoice.invoice_id,
            "client": invoice.client_name,
            "stage": invoice.escalation_stage,
            "stage_label": invoice.escalation_label,
            "days_overdue": invoice.days_overdue,
            "amount": invoice.amount_formatted,
            "subject": email.subject,
            "body": email.body,
            "status": status,
            "error": send_result.error or email.error,
        })

        icon = "✓" if status in ("sent", "dry_run") else "✗"
        logger.info("%s %s → %s", icon, invoice.invoice_id, status.upper())

    summary = {
        "session_id": session_id,
        "total_processed": len(results),
        "sent": sum(1 for r in results if r["status"] == "sent"),
        "dry_run": sum(1 for r in results if r["status"] == "dry_run"),
        "failed": sum(1 for r in results if r["status"] == "failed"),
        "results": results,
        "parse_errors": parse_errors,
    }

    logger.info(
        "═══ Session %s complete | %d processed | %d ok | %d failed ═══",
        session_id, summary["total_processed"],
        summary["sent"] + summary["dry_run"], summary["failed"],
    )
    return summary


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Finance Credit Follow-Up Agent")
    parser.add_argument("--send", action="store_true", help="Actually send emails (default: dry-run)")
    parser.add_argument("--invoice", type=str, help="Process only this invoice ID")
    parser.add_argument("--sender", type=str, default="Finance Team", help="Sender name in emails")
    args = parser.parse_args()

    summary = run_agent(
        dry_run=not args.send,
        invoice_id_filter=args.invoice,
        sender_name=args.sender,
    )

    print("\n" + "═" * 60)
    print(f"  Session: {summary.get('session_id')}")
    print(f"  Processed: {summary.get('total_processed')}")
    print(f"  Sent/DryRun: {summary.get('sent', 0) + summary.get('dry_run', 0)}")
    print(f"  Failed: {summary.get('failed')}")
    print("═" * 60)
