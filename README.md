# 🧠 DevPulse

> **Autonomous engineering intelligence agent** — a multi-agent system that monitors your GitHub repos, researches relevant papers and news, and delivers a daily digest to Slack or email.

![Python](https://img.shields.io/badge/python-3.11+-blue) ![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-green) ![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-teal) ![License](https://img.shields.io/badge/license-MIT-orange)

---

## What it does

DevPulse runs on a schedule (default: 8am weekdays) and produces a Markdown digest covering:

| Section | Source | What you get |
|---|---|---|
| 🔍 Research | ArXiv + HackerNews | LLM-summarised papers & stories relevant to your stack |
| 🔧 PR Reviews | GitHub API | LLM code review + action items for your open PRs |
| 📊 Monitoring | GitHub Releases + Status APIs | New releases for tools you care about + API outages |

Delivered to **Slack** and/or **email** automatically.

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  LangGraph Graph                 │
│                                                 │
│   ┌──────────┐                                  │
│   │supervisor│                                  │
│   └────┬─────┘                                  │
│        │  fan-out (parallel)                    │
│   ┌────┴──────────────────┐                     │
│   ▼           ▼           ▼                     │
│ research   code_review  monitor                 │
│  _agent     _agent      _agent                  │
│   │           │           │                     │
│   └────┬──────┴───────────┘                     │
│        │  merge (shared state)                  │
│        ▼                                        │
│   digest_agent ──► Slack / Email                │
│        │                                        │
│       END                                       │
└─────────────────────────────────────────────────┘
```

### 1. Clone & install

```bash
git clone https://github.com/YOUR_USERNAME/devpulse
cd devpulse
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env with your API keys (see Configuration section)
```

Minimum required (free):
```
GROQ_API_KEY=gsk_...
```

### 3. Run a digest now (CLI)

```bash
# Run and print digest, no Slack/email delivery
python run.py --no-send

# Run with custom topics
python run.py --topics "Rust,PostgreSQL,LangGraph" --no-send

# Full run with delivery
python run.py
```

### 4. Start the server

```bash
uvicorn api.server:app --reload
```

Then:
- `POST http://localhost:8000/run` — trigger a run
- `GET  http://localhost:8000/last-digest` — view the digest
- `GET  http://localhost:8000/health` — liveness check
- `GET  http://localhost:8000/docs` — interactive API docs

---
