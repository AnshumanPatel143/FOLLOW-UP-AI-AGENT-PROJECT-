"""
utils/email_generator.py
────────────────────────────────────────────────────────────────────────────────
Generates personalised follow-up emails via the OpenAI API (stdlib urllib only).

FIX: When the real OpenAI API fails (wrong key, network error, rate limit),
     the generator now gracefully falls back to high-quality mock templates
     instead of returning [Generation Failed].

Modes:
  1. REAL API  — OPENAI_API_KEY is set and valid → calls OpenAI GPT
  2. MOCK      — no API key set → uses built-in templates (full functionality)
  3. FALLBACK  — API key set but call fails → falls back to mock + logs warning
"""

import json
import re
import logging
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Optional

from utils.config import config
from utils.invoice_processor import Invoice

logger = logging.getLogger(__name__)


# ── Output model ──────────────────────────────────────────────────────────────

@dataclass
class GeneratedEmail:
    invoice_id: str
    subject: str
    body: str
    stage: int
    model_used: str
    error: Optional[str] = None
    used_fallback: bool = False        # True when API failed but mock succeeded

    @property
    def is_successful(self) -> bool:
        return bool(self.subject and self.body and self.error is None)


# ── Prompt builder ────────────────────────────────────────────────────────────

STAGE_TONES = {
    1: ("FRIENDLY REMINDER (1-14 days overdue)",
        "Warm and helpful. Assume it was an oversight. No urgency, no threats."),
    2: ("FORMAL PAYMENT NOTICE (15-29 days overdue)",
        "Professional and firm. Reference prior reminders. Request immediate action."),
    3: ("URGENT ESCALATION (30-59 days overdue)",
        "Serious and urgent. Mention credit hold risk. Request payment within 5 business days."),
    4: ("FINAL NOTICE / LEGAL WARNING (60+ days overdue)",
        "Unambiguous. 48-hour deadline. State account will be referred to legal/collections."),
}

SYSTEM_PROMPT = (
    "You are a senior credit controller at a professional finance company. "
    "Write payment follow-up emails that are professional, personalised, legally sound, "
    "and appropriately toned for the escalation stage. "
    "Always respond with valid JSON only — no markdown, no preamble — in this exact format:\n"
    '{"subject": "<subject line>", "body": "<full email body, use \\n for line breaks>"}'
)


def _build_prompt(invoice: Invoice, sender_name: str) -> str:
    stage = invoice.escalation_stage
    stage_name, tone = STAGE_TONES.get(stage, STAGE_TONES[1])
    return (
        f"Stage: {stage_name}\nTone: {tone}\n\n"
        f"Invoice details:\n"
        f"- Invoice ID: {invoice.invoice_id}\n"
        f"- Client company: {invoice.company}\n"
        f"- Contact person: {invoice.contact_person}\n"
        f"- Amount due: {invoice.amount_formatted}\n"
        f"- Original due date: {invoice.due_date.strftime('%B %d, %Y')}\n"
        f"- Days overdue: {invoice.days_overdue}\n"
        f"- Previous reminders sent: {invoice.previous_reminders}\n"
        f"- Sender name: {sender_name}\n\n"
        "Write the email now (JSON only):"
    )


# ── OpenAI call via stdlib urllib ─────────────────────────────────────────────

class OpenAIError(Exception):
    """Raised when the OpenAI API returns an error response."""
    pass


def _call_openai(prompt: str) -> dict:
    """Call OpenAI /v1/chat/completions. Raises OpenAIError on any failure."""
    payload = json.dumps({
        "model": config.OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        "temperature": 0.4,
        "max_tokens": 800,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=payload,
        headers={
            "Content-Type":  "application/json",
            "Authorization": f"Bearer {config.OPENAI_API_KEY}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        try:
            err_data  = json.loads(body)
            err_msg   = err_data.get("error", {}).get("message", body[:200])
        except Exception:
            err_msg = body[:200]
        raise OpenAIError(f"OpenAI API error {e.code}: {err_msg}") from e
    except urllib.error.URLError as e:
        raise OpenAIError(f"Network error reaching OpenAI: {e.reason}") from e
    except Exception as e:
        raise OpenAIError(f"Unexpected error calling OpenAI: {e}") from e

    raw     = data["choices"][0]["message"]["content"]
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise OpenAIError(f"Could not parse JSON from response: {cleaned[:300]}")


# ── Mock / fallback templates ─────────────────────────────────────────────────

_MOCK = {
    1: {
        "subject": "Friendly Reminder: Invoice {invoice_id} — {amount} Due",
        "body": (
            "Dear {contact_person},\n\n"
            "I hope this message finds you well. I'm writing with a friendly reminder "
            "that invoice {invoice_id} for {amount} was due on {due_date}.\n\n"
            "If payment has already been arranged, please disregard this message. "
            "Otherwise, we would be grateful if you could process it at your earliest "
            "convenience.\n\n"
            "Please don't hesitate to reach out if you have any questions about this invoice.\n\n"
            "Kind regards,\n{sender_name}"
        ),
    },
    2: {
        "subject": "Formal Payment Notice: Invoice {invoice_id} — {days_overdue} Days Overdue",
        "body": (
            "Dear {contact_person},\n\n"
            "This is a formal notice that invoice {invoice_id} for {amount}, "
            "due on {due_date}, remains unpaid {days_overdue} days past the due date.\n\n"
            "Despite {previous_reminders} previous reminder(s), we have not yet received "
            "payment or a response. We kindly request that you arrange payment immediately "
            "or contact us to discuss your account.\n\n"
            "Please treat this as a matter requiring urgent attention.\n\n"
            "Regards,\n{sender_name}"
        ),
    },
    3: {
        "subject": "URGENT: Invoice {invoice_id} — Immediate Payment Required",
        "body": (
            "Dear {contact_person},\n\n"
            "We write with urgency regarding invoice {invoice_id} for {amount}, "
            "now {days_overdue} days overdue.\n\n"
            "Following {previous_reminders} unanswered communication(s), this matter has been "
            "escalated internally. Unless full payment is received within 5 business days, "
            "we may be required to place a hold on your account and suspend services.\n\n"
            "To avoid disruption, please arrange payment immediately or contact us to "
            "discuss a payment plan.\n\n"
            "Regards,\n{sender_name}"
        ),
    },
    4: {
        "subject": "FINAL NOTICE: Invoice {invoice_id} — Legal Action Pending in 48 Hours",
        "body": (
            "Dear {contact_person},\n\n"
            "This is a final notice regarding invoice {invoice_id} for {amount}, "
            "now {days_overdue} days overdue. We have sent {previous_reminders} prior "
            "communications, none of which have received a response.\n\n"
            "Unless full payment is received within 48 hours of this notice, your account "
            "will be referred to our legal and collections department. This may result in "
            "additional costs and formal legal proceedings being initiated.\n\n"
            "To resolve this matter immediately, please contact us today without delay.\n\n"
            "Yours sincerely,\n{sender_name}\nCredit Control Department"
        ),
    },
}


def _generate_mock(invoice: Invoice, sender_name: str) -> dict:
    """Generate a professional templated email — no API needed."""
    tpl = _MOCK.get(invoice.escalation_stage, _MOCK[1])
    v = {
        "invoice_id":         invoice.invoice_id,
        "amount":             invoice.amount_formatted,
        "due_date":           invoice.due_date.strftime("%B %d, %Y"),
        "days_overdue":       invoice.days_overdue,
        "previous_reminders": invoice.previous_reminders,
        "contact_person":     invoice.contact_person,
        "sender_name":        sender_name,
    }
    return {
        "subject": tpl["subject"].format(**v),
        "body":    tpl["body"].format(**v),
    }


# ── Generator ─────────────────────────────────────────────────────────────────

class EmailGenerator:
    """
    Generates follow-up emails for overdue invoices.

    Priority order:
      1. OpenAI API  (when OPENAI_API_KEY is set and valid)
      2. Mock templates (fallback when API fails OR no key set)

    NEVER returns [Generation Failed] — always produces a usable email.
    """

    def __init__(self):
        self.use_real_api = bool(
            config.OPENAI_API_KEY
            and not config.OPENAI_API_KEY.startswith("sk-your")
            and len(config.OPENAI_API_KEY) > 20
        )
        mode = f"OpenAI {config.OPENAI_MODEL}" if self.use_real_api else "mock templates"
        logger.info("EmailGenerator ready — mode: %s", mode)

    def generate(self, invoice: Invoice, sender_name: str = "Finance Team") -> GeneratedEmail:
        """
        Generate a follow-up email. Always returns a valid email — never fails silently.
        If the real API fails, automatically falls back to professional mock templates.
        """

        # ── Attempt 1: Real OpenAI API ────────────────────────────────────────
        if self.use_real_api:
            try:
                logger.info("Calling OpenAI for %s (stage %d)", invoice.invoice_id, invoice.escalation_stage)
                parsed  = _call_openai(_build_prompt(invoice, sender_name))
                subject = parsed.get("subject", "").strip()
                body    = parsed.get("body", "").strip()
                if not subject or not body:
                    raise OpenAIError("API returned empty subject or body")
                return GeneratedEmail(
                    invoice_id=invoice.invoice_id,
                    subject=subject, body=body,
                    stage=invoice.escalation_stage,
                    model_used=config.OPENAI_MODEL,
                )
            except OpenAIError as api_err:
                logger.warning(
                    "OpenAI API failed for %s (%s) — falling back to mock template",
                    invoice.invoice_id, api_err
                )
                # Fall through to mock below

        # ── Attempt 2: Mock / fallback templates ──────────────────────────────
        try:
            parsed  = _generate_mock(invoice, sender_name)
            subject = parsed["subject"]
            body    = parsed["body"]
            used_fallback = self.use_real_api  # True only if we tried API first
            model_label   = f"mock (API fallback)" if used_fallback else "mock"

            if used_fallback:
                logger.warning("Using mock template fallback for %s", invoice.invoice_id)

            return GeneratedEmail(
                invoice_id=invoice.invoice_id,
                subject=subject, body=body,
                stage=invoice.escalation_stage,
                model_used=model_label,
                used_fallback=used_fallback,
            )

        except Exception as mock_err:
            # This should never happen — mock templates are pure Python
            logger.error("Even mock generation failed for %s: %s", invoice.invoice_id, mock_err)
            return GeneratedEmail(
                invoice_id=invoice.invoice_id,
                subject="Payment Follow-Up Required",
                body=f"Dear {invoice.contact_person},\n\nPlease contact us regarding invoice {invoice.invoice_id} for {invoice.amount_formatted}.\n\nRegards,\n{sender_name}",
                stage=invoice.escalation_stage,
                model_used="emergency-fallback",
                error=str(mock_err),
            )

    def generate_batch(self, invoices: list[Invoice], sender_name: str = "Finance Team") -> list[GeneratedEmail]:
        return [self.generate(inv, sender_name=sender_name) for inv in invoices]
