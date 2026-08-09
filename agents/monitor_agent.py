"""
Monitor Agent
Watches GitHub release feeds and public API status pages for tools
the user cares about. Emits MonitorAlerts into shared state.
"""

from __future__ import annotations
import httpx
import feedparser
from datetime import datetime, timezone, timedelta

from core.state import DevPulseState, MonitorAlert


# ── Configurable watchlist ─────────────────────────────────────────────────────
# Edit this list to track whatever tools matter to you.

GITHUB_RELEASE_WATCHES = [
    "langchain-ai/langgraph",
    "langchain-ai/langchain",
    "openai/openai-python",
    "tiangolo/fastapi",
    "pydantic/pydantic",
    "TransformerLensOrg/TransformerLens",
    "jbloomAus/SAELens",
    "EleutherAI/elk",
    "PKU-Alignment/safe-rlhf",
    "EleutherAI/lm-evaluation-harness",
    "huggingface/alignment-handbook",
    "openai/evals",
    "openai/weak-to-strong",
        "vllm-project/vllm",
    "huggingface/transformers",
    "huggingface/trl",
    "OpenRLHF/OpenRLHF",
    "verl-project/verl",
    "Lightning-AI/litgpt",
    "microsoft/promptbench",
]

API_STATUS_PAGES = [
    {
        "name": "OpenAI",
        "url": "https://status.openai.com/api/v2/status.json",
        "indicator_path": ["status", "indicator"],   # path in JSON to status value
        "ok_value": "none",
    },
]


# ── Tool: GitHub releases via RSS ─────────────────────────────────────────────

def check_github_releases(repos: list[str], lookback_hours: int = 25) -> list[MonitorAlert]:
    alerts = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

    for repo in repos:
        url = f"https://github.com/{repo}/releases.atom"
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:3]:
                published = entry.get("published_parsed")
                if published:
                    pub_dt = datetime(*published[:6], tzinfo=timezone.utc)
                    if pub_dt < cutoff:
                        continue
                alerts.append(MonitorAlert(
                    source="github_releases",
                    title=f"🚀 New release: {repo}",
                    detail=entry.get("title", ""),
                    url=entry.get("link", f"https://github.com/{repo}/releases"),
                    severity="info",
                ))
        except Exception:
            pass
    return alerts


# ── Tool: API status pages ─────────────────────────────────────────────────────

def check_api_statuses(pages: list[dict]) -> list[MonitorAlert]:
    alerts = []
    for page in pages:
        try:
            resp = httpx.get(page["url"], timeout=8)
            resp.raise_for_status()
            data = resp.json()
            # Walk nested path to get indicator
            value = data
            for key in page["indicator_path"]:
                value = value[key]
            if value != page["ok_value"]:
                alerts.append(MonitorAlert(
                    source="api_status",
                    title=f"⚠️ {page['name']} status: {value}",
                    detail=f"Status page returned indicator={value!r} (expected {page['ok_value']!r})",
                    url=page["url"].replace("/api/v2/status.json", ""),
                    severity="warning" if value != "critical" else "critical",
                ))
        except Exception as e:
            alerts.append(MonitorAlert(
                source="api_status",
                title=f"❓ Could not reach {page['name']} status page",
                detail=str(e),
                url="",
                severity="warning",
            ))
    return alerts


# ── Agent node ────────────────────────────────────────────────────────────────

def monitor_agent(state: DevPulseState) -> dict:
    """
    LangGraph node: checks releases and API statuses.
    """
    alerts: list[MonitorAlert] = []
    errors: list[str] = []

    try:
        alerts += check_github_releases(GITHUB_RELEASE_WATCHES)
    except Exception as e:
        errors.append(f"monitor_agent/releases: {e}")

    try:
        alerts += check_api_statuses(API_STATUS_PAGES)
    except Exception as e:
        errors.append(f"monitor_agent/status: {e}")

    return {
        "monitor_alerts": alerts,
        "tasks_completed": ["monitor"],
        "errors": errors,
    }
