# 💳 AI Finance Credit Follow-Up Agent

A production-ready AI-powered email agent that automatically detects overdue invoices, determines escalation urgency, and generates personalised follow-up emails using GPT-4o via LangChain.

---

## ✨ Features

- **📊 Smart Invoice Processing** — Reads CSV, validates records, detects overdue status
- **🎯 4-Stage Escalation** — Friendly → Formal → Urgent → Legal warning
- **🤖 AI Email Generation** — GPT-4o writes personalised, stage-appropriate emails
- **📧 Real Email Sending** — SMTP integration (Gmail / any provider)
- **💾 Audit Logging** — Every action logged to SQLite + JSON
- **🖥️ Premium Dashboard** — Streamlit UI with auth, charts, and email preview
- **🔒 Secure** — `.env` for secrets, no hardcoded credentials, input validation

---

## 🚀 Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your OpenAI API key and SMTP credentials
```

### 3. Run the dashboard

```bash
streamlit run app.py --server.port 8502
```

Login with: `admin` / `changeme123` (change in `.env`)

### 4. Or run via CLI (dry-run, no emails sent)

```bash
python agent.py
```

### 5. Send real emails

```bash
python agent.py --send
```

---

## 📁 Project Structure

```
ai-finance-agent/
├── app.py                      # Streamlit dashboard (multi-page, with auth)
├── agent.py                    # CLI orchestrator
├── requirements.txt
├── .env.example                # Copy to .env and fill in values
├── .gitignore
│
├── data/
│   └── invoices.csv            # Invoice data (add your real invoices here)
│
├── utils/
│   ├── config.py               # Centralised config + env loading
│   ├── invoice_processor.py    # CSV loading, validation, escalation logic
│   ├── email_generator.py      # LangChain + OpenAI email generation
│   ├── email_sender.py         # SMTP email sending
│   └── logger.py               # SQLite + JSON audit logging
│
├── prompts/
│   └── email_prompts.py        # Stage-specific LangChain prompt templates
│
├── logs/                       # Auto-created: follow_ups.db + follow_ups.json
└── tests/
    └── test_invoice_processor.py
```

---

## 📊 Escalation Stages

| Stage | Days Overdue | Tone         |
|-------|-------------|--------------|
| 1     | 1–14        | Friendly reminder |
| 2     | 15–29       | Formal notice |
| 3     | 30–59       | Urgent escalation |
| 4     | 60+         | Final / legal warning |

---

## 🧪 Running Tests

```bash
python -m pytest tests/ -v
```

---

## 🔑 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | ✅ | Your OpenAI API key |
| `OPENAI_MODEL` | No | Default: `gpt-4o-mini` |
| `EMAIL_HOST` | For sending | SMTP host (default: smtp.gmail.com) |
| `EMAIL_PORT` | For sending | Default: 587 |
| `EMAIL_USER` | For sending | Your email address |
| `EMAIL_PASSWORD` | For sending | App password (not your main password) |
| `APP_USERNAME` | No | Dashboard login (default: admin) |
| `APP_PASSWORD` | No | Dashboard password (default: changeme123) |

---

## 📝 Invoice CSV Format

Your `data/invoices.csv` must have these columns:

```
invoice_id, client_name, client_email, amount, currency,
issue_date, due_date, status, days_overdue, contact_person,
company, previous_reminders
```

- `status`: `overdue` | `paid` | `pending`
- `issue_date` / `due_date`: `YYYY-MM-DD` format

---

## 🔒 Security Notes

- Never commit `.env` to git (it's in `.gitignore`)
- Use Gmail App Passwords, not your main password
- Change the default dashboard credentials in `.env`
- The agent validates all input before processing

---

## 📜 License

MIT License — Use freely, attribution appreciated.
