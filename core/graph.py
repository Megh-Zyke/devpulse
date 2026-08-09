"""
DevPulse — LangGraph Graph Definition

Architecture:
  supervisor → [research_agent, code_review_agent, monitor_agent] → digest_agent → END

Key LangGraph concepts used:
  - StateGraph with a shared TypedDict state
  - Parallel fan-out from supervisor to all worker agents
  - Conditional edge: only run digest after all workers complete
  - Add_edge for sequential flow
"""

from __future__ import annotations
from langgraph.graph import StateGraph, END

from core.state import DevPulseState
from agents.research_agent import research_agent
from agents.code_review_agent import code_review_agent
from agents.monitor_agent import monitor_agent
from agents.digest_agent import digest_agent


# ── Supervisor node ───────────────────────────────────────────────────────────

def supervisor(state: DevPulseState) -> dict:
    """
    Entry point node. Could add routing logic here later
    (e.g. skip code_review if no repos configured).
    For now it's a passthrough that kicks off the graph.
    """
    return {}   # no state changes — workers run in parallel after this


# ── Conditional edge: wait for all workers, then go to digest ─────────────────

def all_workers_done(state: DevPulseState) -> str:
    """
    Routes to 'digest' once all three worker agents have completed.
    This is called after each parallel branch finishes.
    LangGraph will only proceed past a fan-out when ALL branches resolve.
    """
    completed = set(state.get("tasks_completed", []))
    required = {"research", "code_review", "monitor"}
    if required.issubset(completed):
        return "digest"
    return "wait"   # LangGraph won't route here in parallel mode, but good for clarity


# ── Build the graph ───────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    graph = StateGraph(DevPulseState)

    # Register nodes
    graph.add_node("supervisor", supervisor)
    graph.add_node("research_agent", research_agent)
    graph.add_node("code_review_agent", code_review_agent)
    graph.add_node("monitor_agent", monitor_agent)
    graph.add_node("digest_agent", digest_agent)

    # Entry point
    graph.set_entry_point("supervisor")

    # Supervisor fans out to all three workers in parallel
    graph.add_edge("supervisor", "research_agent")
    graph.add_edge("supervisor", "code_review_agent")
    graph.add_edge("supervisor", "monitor_agent")

    # All three workers feed into digest
    graph.add_edge("research_agent", "digest_agent")
    graph.add_edge("code_review_agent", "digest_agent")
    graph.add_edge("monitor_agent", "digest_agent")

    # Digest is the final node
    graph.add_edge("digest_agent", END)

    return graph


# ── Compiled graph (importable) ───────────────────────────────────────────────

compiled_graph = build_graph().compile()


# ── Visualise (run directly to see the graph) ─────────────────────────────────

if __name__ == "__main__":
    try:
        img = compiled_graph.get_graph().draw_mermaid()
        print(img)
    except Exception as e:
        print(f"Could not draw graph: {e}")
