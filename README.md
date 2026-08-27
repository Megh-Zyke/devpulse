# DevPulse

> **Autonomous engineering intelligence agent** — a multi-agent system that monitors your GitHub repos, researches relevant papers and news, and delivers a daily digest to Discord.
---

## What it does

DevPulse runs on a schedule (default: 8am weekdays) and produces a Markdown digest covering:

| Section | Source | What you get |
|---|---|---|
| 🔍 Research | ArXiv + HackerNews | LLM-summarised papers & stories relevant to your stack |
| 🔧 PR Reviews | GitHub API | LLM code review + action items for your open PRs |
| 📊 Monitoring | GitHub Releases + Status APIs | New releases for tools you care about + API outages |

Delivered to Discord every day, and every run is persisted to Firestore for history.
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
│   digest_agent ──► Discord + Firestore          │
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
# Run and print digest, no Discord delivery
python run.py --no-send

# Run with custom topics
python run.py --topics "Rust,PostgreSQL,LangGraph" --no-send

# Full run with delivery
python run.py
```

### 4. (Optional) Persist runs to Firestore

Every run's agent output (research items, PR reviews, monitor alerts, and the
final digest) is saved to a Firebase Firestore `digests` collection, keyed by
date, so history survives restarts.

1. Create a Firebase project at https://console.firebase.google.com and enable Firestore.
2. Project settings → Service accounts → Generate new private key.
3. Save the downloaded JSON as `firebase-credentials.json` in the project root
   (or set `FIREBASE_CREDENTIALS_JSON` to the JSON contents directly, useful on
   hosts without a persistent filesystem).

If no credentials are configured, DevPulse still runs — Firestore writes are
simply skipped.

### 5. Start the server

```bash
uvicorn api.server:app --reload
```

Then:
- `POST http://localhost:8000/run` — trigger a run
- `GET  http://localhost:8000/last-digest` — view the digest
- `GET  http://localhost:8000/health` — liveness check
- `GET  http://localhost:8000/docs` — interactive API docs

---
