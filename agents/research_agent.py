"""
Research Agent
Searches ArXiv and HackerNews for content relevant to the user's topics.
Returns a list of ResearchItems added to shared state.
"""

from __future__ import annotations
import httpx
import feedparser
from datetime import datetime, timedelta

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

from core.state import DevPulseState, ResearchItem


# ── LLM ───────────────────────────────────────────────────────────────────────

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)


# ── Tool: ArXiv ───────────────────────────────────────────────────────────────

def fetch_arxiv(topics: list[str], max_results: int = 5) -> list[dict]:
    """Fetch recent ArXiv papers matching topics."""
    query = " OR ".join(f'"{t}"' for t in topics)
    url = (
        f"https://export.arxiv.org/api/query"
        f"?search_query=all:{query}"
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


# ── Tool: HackerNews ──────────────────────────────────────────────────────────

def fetch_hackernews(topics: list[str], max_results: int = 5) -> list[dict]:
    """Search HackerNews Algolia API for topic-relevant stories."""
    results = []
    seen = set()
    yesterday = int((datetime.now() - timedelta(days=1)).timestamp())

    for topic in topics[:3]:   # limit API calls
        url = (
            f"https://hn.algolia.com/api/v1/search"
            f"?query={topic}&tags=story"
            f"&numericFilters=created_at_i>{yesterday}"
            f"&hitsPerPage={max_results}"
        )
        try:
            resp = httpx.get(url, timeout=10)
            resp.raise_for_status()
            for hit in resp.json().get("hits", []):
                hn_url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit['objectID']}"
                if hn_url not in seen:
                    seen.add(hn_url)
                    results.append({
                        "title": hit.get("title", ""),
                        "summary": f"HN points: {hit.get('points', 0)} | comments: {hit.get('num_comments', 0)}",
                        "url": hn_url,
                        "source": "hackernews",
                    })
        except Exception:
            pass
    return results[:max_results]


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

    # Fetch from both sources
    raw = []
    try:
        raw += fetch_arxiv(topics, max_results=4)
    except Exception as e:
        errors.append(f"research_agent/arxiv: {e}")

    try:
        raw += fetch_hackernews(topics, max_results=4)
    except Exception as e:
        errors.append(f"research_agent/hackernews: {e}")

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
            errors.append(f"research_agent/summarise: {e}")

    return {
        "research_items": items,
        "tasks_completed": ["research"],
        "errors": errors,
    }
