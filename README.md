# Finance Credit Follow-Up Email Agent

An AI agent that automates follow-up emails for overdue invoices. It reads pending credit records, determines the appropriate escalation stage based on days overdue, generates a personalised email at the correct tone using an LLM, logs every action, and optionally sends via SMTP.

Live Demo: https://financereminder.streamlit.app/
Demo video : Demo .mp4
Presentation : PPT.pdf file upload 

---

## Tech Stack and Decision Log

| Layer | Technology | Decision Rationale |
|---|---|---|
| LLM | GPT-4o-mini via OpenAI API | Cost-effective for high-volume email generation. Reliable JSON output. Sufficient instruction-following for tone-controlled generation. |
| Agent Framework | LangChain + custom pipeline | LangChain provides structured prompt management and chain composition. No multi-agent overhead needed for a linear escalation workflow. |
| UI | Streamlit | Rapid dashboard development. Built-in support for tables, forms, and state management without a separate frontend. |
| Data Source | CSV / SQLite (pandas) | Lightweight for prototype-scale invoice data. Easily replaceable with a production database. |
| Email Send | SMTP (smtplib) | Standard library, no third-party dependency. Dry-run mode implemented for safe testing. |
| Logging | SQLite audit table | Persistent, queryable log of every generated email with timestamp, stage, and send status. |
| Config | python-dotenv | Secrets kept out of source code. `.env` never committed. |

---

## LLM Choice — GPT-4o-mini

**Model:** `gpt-4o-mini`
**Provider:** OpenAI API
**Version:** `openai>=1.30.0`

### Why GPT-4o-mini over alternatives

| Criterion | GPT-4o-mini | GPT-4o | Claude 3.5 Sonnet | Gemini 1.5 Flash |
|---|---|---|---|---|
| Cost per 1M input tokens | $0.15 | $2.50 | $3.00 | $0.075 |
| Instruction following | Strong | Very strong | Very strong | Good |
| Tone control | Good | Excellent | Excellent | Moderate |
| JSON output reliability | Good | Excellent | Excellent | Moderate |
| Suitable for volume email gen | Yes | Overkill | Overkill | Yes |

GPT-4o-mini was selected because the task is well-defined (tone-controlled email generation with structured inputs), volume may be high, and the cost difference at scale is significant. For a production deployment with strict tone accuracy requirements, upgrading to GPT-4o or Claude Sonnet would be straightforward.

---

## Agent Framework

### Design: Custom Sequential Pipeline on LangChain

The agent does not use CrewAI, AutoGen, or multi-agent orchestration. The workflow is linear and deterministic — a full agent framework adds overhead without benefit for this use case.

### Agent Flow

```
Invoice Data (CSV / DB)
        |
        v
Stage Classifier
  - Reads days_overdue and follow_up_count
  - Assigns escalation stage (1-4 or Escalation Flag)
        |
        v
Email Generator (LLM Call)
  - Injects: client_name, invoice_no, amount, due_date,
             days_overdue, stage, tone instructions
  - Returns: subject line + email body
        |
        v
Output Validator
  - Checks required fields present
  - Confirms tone matches stage
        |
        v
Send / Dry-Run
  - SMTP send or dry-run log entry
        |
        v
Audit Logger
  - Writes to SQLite: timestamp, invoice_no, stage,
    tone, subject, send_status
        |
        v
Streamlit Dashboard
  - Queue view, sent count, escalated records
```

---

## Tone Escalation Matrix

| Stage | Trigger | Tone | Key Message | CTA |
|---|---|---|---|---|
| 1st Follow-Up | 1-7 days overdue | Warm and Friendly | Gentle reminder, assume oversight | Pay now link / bank details |
| 2nd Follow-Up | 8-14 days overdue | Polite but Firm | Payment still pending; request confirmation | Confirm payment date |
| 3rd Follow-Up | 15-21 days overdue | Formal and Serious | Escalating concern; mention impact | Respond within 48 hours |
| 4th Follow-Up | 22-30 days overdue | Stern and Urgent | Final reminder before escalation | Pay immediately or call us |
| Escalation Flag | 30+ days overdue | Flag for Legal | Human review required; no auto email | Assign to finance manager |

After Stage 4, the agent flags the record and stops sending automated emails. A human review task is created instead.

---

## Prompt Design

### Design Principles

All LLM calls follow the same guardrail pattern:

1. System prompt instructs the model to return only the email — no preamble, no explanation, no markdown
2. Structured input schema injects all required fields explicitly — the model is never asked to infer missing data
3. Tone instructions are explicit per stage, not left to the model's interpretation
4. Output is validated post-generation — subject line and body are checked for required fields before logging or sending

### System Prompt

```
You are a professional finance communication specialist writing credit follow-up emails on behalf of a company's finance team.

You will be given invoice details and a tone level. Write a follow-up email that exactly matches the tone level specified.

Rules:
- Output ONLY the email. Start with Subject: on the first line, then a blank line, then the body.
- Do not add any explanation, preamble, or sign-off notes outside the email itself.
- Every email must include: client name, invoice number, amount due, due date, days overdue.
- Do not invent any information not provided. If a field is missing, omit it gracefully.
- Match the tone level exactly as instructed. Do not soften a stern tone or harden a warm tone.
```

### User Prompt Template

```
Client Name: {client_name}
Invoice Number: {invoice_no}
Amount Due: {currency}{amount}
Due Date: {due_date}
Days Overdue: {days_overdue}
Previous Follow-Ups Sent: {follow_up_count}
Stage: {stage_label}
Tone Instructions: {tone_instructions}
Payment Link: {payment_link}
Finance Contact: {finance_contact}

Write the follow-up email now.
```

### Tone Instructions Per Stage

Each stage passes explicit tone instructions into the prompt rather than relying on the stage label alone:

- Stage 1: "Write in a warm, friendly tone. Assume the client may have simply overlooked the invoice. Be helpful and non-accusatory."
- Stage 2: "Write in a polite but firm tone. Note the invoice is still outstanding and ask the client to confirm a payment date."
- Stage 3: "Write in a formal, serious tone. State clearly that the invoice is significantly overdue and that continued non-payment may affect the client's credit terms."
- Stage 4: "Write in a stern, urgent tone. This is a final reminder. State that failure to pay within 24 hours will result in escalation to the legal and recovery team."

---

## Security Risk Mitigation

| Risk | Description | Mitigation |
|---|---|---|
| Prompt Injection | Malicious input in client name or invoice fields manipulating the agent | Input fields are sanitised before injection into prompts. Output schema validation ensures the model cannot be instructed to return non-email content. |
| API Key Exposure | OpenAI API key and SMTP credentials leaked in source code | All secrets stored in `.env` via `python-dotenv`. `.env` is listed in `.gitignore`. Only `.env.example` with placeholder values is committed. Streamlit Cloud secrets used in deployment. |
| Data Privacy / PII | Client names, emails, and financial data in prompts sent to a cloud LLM | No PII is written to application logs. Invoice data is processed in memory only. Prompts contain the minimum required fields. |
| Hallucination Risk | LLM generating incorrect invoice amounts, dates, or client names | All variable fields are injected from the data source — the model is explicitly instructed not to invent information. Output is validated against source data before sending. |
| Unauthorised Access | Unauthenticated access to the Streamlit dashboard | App-level username and password authentication implemented via `st.secrets`. Credentials stored in Streamlit Cloud secrets, not in code. |
| Email Spoofing | Emails appearing to come from an unverified sender | Sending domain uses Gmail SMTP with App Password authentication. SPF record is in place at the domain level. Dry-run mode available for testing without live send. |
| Escalation Bypass | Agent sending emails past the escalation cap | Hard check before every send: if `days_overdue > 30`, the record is flagged and no email is generated or sent, regardless of follow-up count. |

---

## Setup Instructions

### Prerequisites

- Python 3.10+
- OpenAI API key
- Gmail account with App Password enabled (for live send)

### 1. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/follow-up-ai-agent.git
cd follow-up-ai-agent
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Fill in `.env`:

```env
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-4o-mini
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=your@gmail.com
EMAIL_PASSWORD=your_app_password
EMAIL_FROM_NAME=Finance Team
APP_ENV=development
LOG_LEVEL=INFO
LOG_DIR=logs
DB_PATH=logs/follow_ups.db
APP_USERNAME=admin
APP_PASSWORD=changeme123
```

### 3. Run locally

```bash
streamlit run app.py
```

Open `http://localhost:8501`

### 4. Deploy to Streamlit Cloud

1. Push the repository to GitHub (ensure `.env` is in `.gitignore`)
2. Go to share.streamlit.io and connect the repository
3. Under Settings → Secrets, paste all variables from `.env` in TOML format
4. Deploy

---

## Project Structure

```
follow-up-ai-agent/
├── app.py                    # Streamlit dashboard entry point
├── agent/
│   └── agent.py              # LangChain agent pipeline
├── utils/
│   ├── __init__.py
│   ├── config.py             # Environment variable loader
│   ├── invoice_processor.py  # Stage classifier and data ingestion
│   └── logger.py             # SQLite audit logger
├── data/
│   └── sample_invoices.csv   # Sample invoice data for testing
├── logs/                     # Auto-created at runtime
├── requirements.txt
├── .env.example
└── README.md
```

---

## Sample Invoice Data Format

The agent expects a CSV or database table with the following columns:

| Column | Type | Description |
|---|---|---|
| invoice_no | string | Unique invoice identifier |
| client_name | string | Debtor company or individual name |
| amount | float | Amount outstanding |
| currency | string | Currency symbol (e.g. Rs., $) |
| due_date | date | Original payment due date |
| days_overdue | int | Days since due date |
| contact_email | string | Recipient email address |
| follow_up_count | int | Number of follow-ups already sent |
| payment_link | string | Payment portal URL or bank details |
| finance_contact | string | Finance team contact for queries |

---

## Audit Log Schema

Every generated email is recorded in `logs/follow_ups.db`:

| Column | Description |
|---|---|
| id | Auto-increment primary key |
| timestamp | UTC datetime of generation |
| invoice_no | Invoice reference |
| client_name | Recipient name |
| stage | Escalation stage (1-4 or ESCALATED) |
| tone | Tone label used |
| subject | Generated email subject |
| send_status | SENT, DRY_RUN, FAILED, or ESCALATED |
| error_message | Populated only on FAILED status |

---

## Deliverables

- [x] GitHub repository with source code
- [x] `.env.example` with all required keys
- [x] `requirements.txt` with all dependencies
- [x] README with architecture, LLM rationale, agent framework, prompt design, and security documentation
- [x] Live demo at https://financereminder.streamlit.app/
- [x] Sample invoice CSV for testing
- [ ] Sample output log export (run the app with sample data and export the audit log)
- [ ] 3-5 minute screen recording
- [ ] 8-10 slide presentation deck
