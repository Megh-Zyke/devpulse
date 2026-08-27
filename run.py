"""
DevPulse CLI runner
Usage:
    python run.py                  # run with env vars
    python run.py --topics "Rust,LangGraph" --no-send
"""

from __future__ import annotations
import asyncio
import argparse
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from core.graph import compiled_graph
from core.state import DevPulseState


async def main(topics: list[str], repos: list[str], no_send: bool):
    if no_send:
        # Temporarily unset delivery env vars
        os.environ.pop("DISCORD_WEBHOOK_URL", None)

    initial_state = DevPulseState(
        run_date=datetime.now().strftime("%Y-%m-%d"),
        topics=topics,
        github_repos=repos,
        research_items=[],
        pr_reviews=[],
        monitor_alerts=[],
        tasks_completed=[],
        errors=[],
        digest_markdown="",
        digest_sent=False,
    )

    print(f"\n🚀 Starting DevPulse run | topics={topics} | repos={repos}\n{'─'*60}")
    result = await compiled_graph.ainvoke(initial_state)

    print("\n✅ Run complete!\n")
    print(f"  Research items : {len(result['research_items'])}")
    print(f"  PR reviews     : {len(result['pr_reviews'])}")
    print(f"  Monitor alerts : {len(result['monitor_alerts'])}")
    print(f"  Errors         : {len(result['errors'])}")
    print(f"  Digest sent    : {result['digest_sent']}")

    if result["errors"]:
        print("\n⚠️  Errors:")
        for e in result["errors"]:
            print(f"   {e}")

    print(f"\n{'─'*60}\n📄 DIGEST\n{'─'*60}\n")
    print(result["digest_markdown"])

    # Save digest to file
    out = f"digest_{result['run_date']}.md"
    with open(out, "w") as f:
        f.write(result["digest_markdown"])
    print(f"\n💾 Digest saved to {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run DevPulse")
    parser.add_argument("--topics", default=os.getenv("TOPICS", "LangGraph,FastAPI,MLOps"))
    parser.add_argument("--repos", default=os.getenv("REPOS", ""))
    parser.add_argument("--no-send", action="store_true", help="Skip Discord delivery")
    args = parser.parse_args()

    topic_list = [t.strip() for t in args.topics.split(",") if t.strip()]
    repo_list = [r.strip() for r in args.repos.split(",") if r.strip()]

    asyncio.run(main(topic_list, repo_list, args.no_send))
