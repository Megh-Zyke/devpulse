"""
Code Review Agent
Polls GitHub repos for open PRs, fetches the diff, and produces
an LLM-powered review summary + action items.
"""

from __future__ import annotations
import os
from github import Github, GithubException
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

from core.state import DevPulseState, PRReview


# ── LLM ───────────────────────────────────────────────────────────────────────

llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0, max_retries=6)

review_prompt = ChatPromptTemplate.from_messages([
    ("system", (
        "You are a senior software engineer doing a code review. "
        "Given a PR title, description, and diff snippet, produce:\n"
        "1. A 3-sentence summary of what this PR does.\n"
        "2. A bullet list of up to 4 concrete action items or concerns.\n\n"
        "Format your response exactly as:\n"
        "SUMMARY: <summary>\n"
        "ACTION_ITEMS:\n- item1\n- item2\n..."
    )),
    ("human", (
        "PR: {title}\n\n"
        "Description: {body}\n\n"
        "Diff (truncated):\n{diff}"
    )),
])

review_chain = review_prompt | llm


def parse_review(text: str) -> tuple[str, list[str]]:
    """Parse LLM output into summary + action_items."""
    summary, action_items = "", []
    for line in text.splitlines():
        if line.startswith("SUMMARY:"):
            summary = line.replace("SUMMARY:", "").strip()
        elif line.startswith("- "):
            action_items.append(line[2:].strip())
    return summary, action_items


# ── GitHub helpers ────────────────────────────────────────────────────────────

def get_open_prs(repo_name: str, gh: Github) -> list:
    """Return open PRs updated in last 24h."""
    try:
        repo = gh.get_repo(repo_name)
        return list(repo.get_pulls(state="open", sort="updated", direction="desc"))[:5]
    except GithubException as e:
        raise RuntimeError(f"GitHub error for {repo_name}: {e}") from e


def get_pr_diff(pr, max_chars: int = 3000) -> str:
    """Fetch and truncate the unified diff of a PR."""
    files = list(pr.get_files())
    diff_parts = []
    total = 0
    for f in files:
        patch = getattr(f, "patch", "") or ""
        part = f"### {f.filename}\n{patch}\n"
        if total + len(part) > max_chars:
            diff_parts.append("... (diff truncated)")
            break
        diff_parts.append(part)
        total += len(part)
    return "\n".join(diff_parts) or "No diff available."


# ── Agent node ────────────────────────────────────────────────────────────────

def code_review_agent(state: DevPulseState) -> dict:
    """
    LangGraph node: reviews open PRs across configured repos.
    """
    token = os.getenv("GITHUB_TOKEN")
    repos = state.get("github_repos", [])

    if not token or not repos:
        return {
            "tasks_completed": ["code_review"],
            "errors": ["code_review_agent: GITHUB_TOKEN or repos not configured — skipping."],
        }

    gh = Github(token)
    reviews: list[PRReview] = []
    errors: list[str] = []

    for repo_name in repos:
        try:
            prs = get_open_prs(repo_name, gh)
            for pr in prs:
                try:
                    diff = get_pr_diff(pr)
                    result = review_chain.invoke({
                        "title": pr.title,
                        "body": pr.body or "No description.",
                        "diff": diff,
                    })
                    summary, action_items = parse_review(result.content)
                    reviews.append(PRReview(
                        repo=repo_name,
                        pr_number=pr.number,
                        pr_title=pr.title,
                        pr_url=pr.html_url,
                        review_summary=summary,
                        action_items=action_items,
                    ))
                except Exception as e:
                    errors.append(f"code_review_agent/pr#{pr.number}: {e}")
        except Exception as e:
            errors.append(f"code_review_agent/{repo_name}: {e}")

    return {
        "pr_reviews": reviews,
        "tasks_completed": ["code_review"],
        "errors": errors,
    }
