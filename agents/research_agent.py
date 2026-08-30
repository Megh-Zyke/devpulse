"""
Research Agent
Searches ArXiv and HackerNews for content relevant to the user's topics.
Returns a list of ResearchItems added to shared state.
"""

from __future__ import annotations
import httpx
import feedparser
from datetime import datetime, timedelta
from urllib.parse import quote

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

from core.state import DevPulseState, ResearchItem
from core.errors import safe_error_detail


# ── LLM ───────────────────────────────────────────────────────────────────────

llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0, max_retries=6)


# ── Tool: ArXiv ───────────────────────────────────────────────────────────────

def fetch_arxiv(topics: list[str], max_results: int = 5) -> list[dict]:
    """Fetch recent ArXiv papers matching topics."""
    query = " OR ".join(f'"{t}"' for t in topics)
    url = (
        f"https://export.arxiv.org/api/query"
        f"?search_query=all:{quote(query)}"
        f"&sortBy=submittedDate&sortOrder=descending"
        f"&max_results={max_results}"
    )
    feed = feedparser.parse(url)
    results = []
    for entry in feed.entries:
        results.append({
            "title": entry.title.strip(),
            "summary": entry.summary[:600].strip(),
            "url": entry.link,
            "source": "arxiv",
        })
    return results

# ── Summariser ────────────────────────────────────────────────────────────────

summarise_prompt = ChatPromptTemplate.from_messages([
    ("system", (
        "You are a senior engineer summarising research for a daily digest. "
        "Given a title and raw summary, write 2 crisp sentences: "
        "what it is and why it matters to an ML/backend engineer. "
        "Be concrete, skip filler words."
    )),
    ("human", "Title: {title}\n\nRaw: {raw_summary}"),
])

summarise_chain = summarise_prompt | llm


def summarise_item(item: dict) -> str:
    result = summarise_chain.invoke({
        "title": item["title"],
        "raw_summary": item["summary"],
    })
    return result.content.strip()


# ── Agent node ────────────────────────────────────────────────────────────────

def research_agent(state: DevPulseState) -> dict:
    """
    LangGraph node: fetches research items and summarises them.
    Returns a partial state update.
    """
    topics = state.get("topics", ["LangGraph", "MLOps", "LLM"])
    items: list[ResearchItem] = []
    errors: list[str] = []

    raw = []
    try:
        raw += fetch_arxiv(topics, max_results=4)
    except Exception as e:
        errors.append(f"research_agent/arxiv: {e}")

    # Summarise each item with LLM
    for item in raw:
        try:
            better_summary = summarise_item(item)
            items.append(ResearchItem(
                title=item["title"],
                summary=better_summary,
                url=item["url"],
                source=item["source"],
            ))
        except Exception as e:
            errors.append(f"research_agent/summarise: {safe_error_detail(e)}")

    return {
        "research_items": items,
        "tasks_completed": ["research"],
        "errors": errors,
    }
