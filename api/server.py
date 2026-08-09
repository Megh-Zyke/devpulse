"""
DevPulse — FastAPI Server

Endpoints:
  POST /run         → trigger a digest run now
  GET  /health      → liveness check
  GET  /last-digest → return the last generated digest markdown

Scheduler:
  APScheduler runs the digest automatically on DIGEST_CRON schedule.
"""

from __future__ import annotations
import os
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import PlainTextResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

load_dotenv()

from core.graph import compiled_graph
from core.state import DevPulseState

# ── In-memory store for last run result ───────────────────────────────────────
last_result: dict = {}


# ── Core runner ───────────────────────────────────────────────────────────────

def build_initial_state() -> DevPulseState:
    topics_raw = os.getenv("TOPICS", "LangGraph,MLOps,FastAPI,Rust")
    repos_raw = os.getenv("GITHUB_REPOS", "")
    return DevPulseState(
        run_date=datetime.now().strftime("%Y-%m-%d"),
        topics=[t.strip() for t in topics_raw.split(",") if t.strip()],
        github_repos=[r.strip() for r in repos_raw.split(",") if r.strip()],
        research_items=[],
        pr_reviews=[],
        monitor_alerts=[],
        tasks_completed=[],
        errors=[],
        digest_markdown="",
        digest_sent=False,
    )


async def run_devpulse():
    global last_result
    print(f"[DevPulse] Starting run at {datetime.now().isoformat()}")
    initial_state = build_initial_state()
    result = await compiled_graph.ainvoke(initial_state)
    last_result = result
    print(f"[DevPulse] Run complete. digest_sent={result.get('digest_sent')}")
    return result


# ── Scheduler setup ───────────────────────────────────────────────────────────

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    cron = os.getenv("DIGEST_CRON", "0 8 * * 1-5")
    parts = cron.split()
    trigger = CronTrigger(
        minute=parts[0], hour=parts[1],
        day=parts[2], month=parts[3], day_of_week=parts[4],
    )
    scheduler.add_job(run_devpulse, trigger, id="devpulse_daily")
    scheduler.start()
    print(f"[DevPulse] Scheduler started. Cron: {cron}")
    yield
    scheduler.shutdown()


# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="DevPulse",
    description="Autonomous engineering intelligence agent powered by LangGraph",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.post("/run")
async def trigger_run(background_tasks: BackgroundTasks):
    """Trigger a DevPulse digest run immediately."""
    background_tasks.add_task(run_devpulse)
    return {"status": "started", "message": "DevPulse run triggered. Check /last-digest in ~60s."}


@app.get("/last-digest", response_class=PlainTextResponse)
async def get_last_digest():
    """Return the last generated digest as Markdown."""
    if not last_result:
        raise HTTPException(status_code=404, detail="No digest generated yet. POST /run to trigger one.")
    return last_result.get("digest_markdown", "Empty digest.")


@app.get("/last-result")
async def get_last_result():
    """Return the full structured result of the last run."""
    if not last_result:
        raise HTTPException(status_code=404, detail="No run yet.")
    # Exclude the raw markdown from the JSON (it's big)
    return {k: v for k, v in last_result.items() if k != "digest_markdown"}
