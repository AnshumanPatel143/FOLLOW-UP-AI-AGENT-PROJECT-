"""
prompts/email_prompts.py
────────────────────────────────────────────────────────────────────────────────
Stage-specific prompt templates for the AI email generator.
These are plain Python dicts — no LangChain runtime required.
The email_generator.py module uses these for documentation and reference;
actual prompt construction is done inline for maximum portability.

Stage escalation logic:
    Stage 1 —  1-14 days  → Friendly Reminder
    Stage 2 — 15-29 days  → Formal Notice
    Stage 3 — 30-59 days  → Urgent Escalation
    Stage 4 — 60+ days    → Final / Legal Warning
"""

STAGE_DEFINITIONS = {
    1: {
        "name": "Friendly Reminder",
        "days_range": "1-14 days overdue",
        "tone": "Warm, helpful, assumes an honest oversight. No threats or urgency.",
        "key_points": [
            "Polite and friendly opener",
            "State invoice ID and amount clearly",
            "Assume payment may be in progress",
            "Offer to help with any questions",
        ],
    },
    2: {
        "name": "Formal Notice",
        "days_range": "15-29 days overdue",
        "tone": "Professional and firm. References prior reminders. Requests immediate action.",
        "key_points": [
            "Formal salutation",
            "Reference previous reminders sent",
            "State invoice details and days past due",
            "Request immediate payment or contact",
        ],
    },
    3: {
        "name": "Urgent Escalation",
        "days_range": "30-59 days overdue",
        "tone": "Serious and urgent. Mentions potential credit hold. 5-business-day deadline.",
        "key_points": [
            "Escalation language — this has been raised internally",
            "Risk of account hold or service suspension",
            "Clear 5-day deadline",
            "Option to discuss payment plan",
        ],
    },
    4: {
        "name": "Final / Legal Warning",
        "days_range": "60+ days overdue",
        "tone": "Unambiguous. Zero-ambiguity 48-hour deadline. Legal referral stated.",
        "key_points": [
            "Final notice language",
            "Specific 48-hour deadline",
            "State legal/collections referral consequence",
            "Professional but non-aggressive tone",
        ],
    },
}

SYSTEM_PROMPT = (
    "You are a senior credit controller at a professional finance company. "
    "Write payment follow-up emails that are professional, personalised, legally sound, "
    "and appropriately toned for the escalation stage. "
    "Always respond with valid JSON only — no markdown, no preamble:\n"
    '{"subject": "<subject line>", "body": "<full email body using \\n for line breaks>"}'
)


def get_stage_definition(stage: int) -> dict:
    """Return the definition dict for a given stage number (1-4)."""
    if stage not in STAGE_DEFINITIONS:
        raise ValueError(f"Invalid stage {stage}. Must be 1-4.")
    return STAGE_DEFINITIONS[stage]
