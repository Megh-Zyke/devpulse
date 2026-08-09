"""
DevPulse — Shared Graph State
All agents read from and write to this TypedDict.
LangGraph merges updates automatically via Annotated reducers.
"""

from __future__ import annotations
from typing import Annotated, Any
from typing_extensions import TypedDict
import operator


def merge_lists(a: list, b: list) -> list:
    """Reducer: append new items to existing list."""
    return a + b


class ResearchItem(TypedDict):
    title: str
    summary: str
    url: str
    source: str          # "arxiv" | "hackernews" | "github_trending"


class PRReview(TypedDict):
    repo: str
    pr_number: int
    pr_title: str
    pr_url: str
    review_summary: str
    action_items: list[str]


class MonitorAlert(TypedDict):
    source: str          # e.g. "github_releases", "api_status"
    title: str
    detail: str
    url: str
    severity: str        # "info" | "warning" | "critical"


class DevPulseState(TypedDict):
    # ── Inputs ────────────────────────────────────────────────────────────────
    run_date: str                        # ISO date string for this run
    topics: list[str]                    # e.g. ["LangGraph", "Rust", "MLOps"]
    github_repos: list[str]             # ["owner/repo", ...]

    # ── Agent outputs (reducers allow safe concurrent writes) ─────────────────
    research_items: Annotated[list[ResearchItem], merge_lists]
    pr_reviews: Annotated[list[PRReview], merge_lists]
    monitor_alerts: Annotated[list[MonitorAlert], merge_lists]

    # ── Supervisor routing ────────────────────────────────────────────────────
    tasks_completed: Annotated[list[str], merge_lists]   # which agents finished
    errors: Annotated[list[str], merge_lists]

    # ── Final output ──────────────────────────────────────────────────────────
    digest_markdown: str
    digest_sent: bool
