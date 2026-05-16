"""
LangGraph-powered stateful conversational search.

Session lifecycle:
  - Each chat session has a UUID (session_id) from the frontend.
  - MemorySaver persists SearchState between HTTP requests keyed by thread_id.
  - "New Chat" generates a new UUID → fresh thread → no bleed-over.

State transitions:
  interpret → new_search/refine  → search        → finalize → END
           ↘ filter_existing     → filter        → finalize → END
           ↘ rerank_existing     → rerank        → finalize → END
           ↘ chat_only                           → finalize → END
"""

import json
import operator
import re
from typing import Annotated, List, TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from .llm_service import chat_completion


# ── State ─────────────────────────────────────────────────────────────────────

class SearchState(TypedDict):
    # Accumulated across turns (operator.add appends lists)
    messages: Annotated[List[dict], operator.add]

    # Persisted search context — always reflects what the user currently sees
    last_search_query: str
    last_results: List[dict]       # serialized; what the user last saw
    active_filters: dict

    # Per-turn outputs (set fresh each turn)
    pending_action: str
    rerank_criteria: str           # semantic criteria for rerank_existing
    response_intro: str
    current_results: List[dict]


# ── System prompt ─────────────────────────────────────────────────────────────

_INTERPRET_SYSTEM = """You are a stateful AI HR assistant for a talent search platform.

You see the full conversation history and the current search state.
Decide what action to take — choose the MOST SPECIFIC one that fits:

  "new_search"       — User wants to find entirely different people (new topic/role).
                       Use when no prior results exist, or user clearly changes topic.

  "refine"           — User wants to add/change search criteria and re-query the database.
                       Use when user adds skills, seniority, or other attributes to broaden/narrow
                       beyond what was shown. Will run a fresh ChromaDB search.

  "filter_existing"  — User wants to filter shown results by SIMPLE ATTRIBUTES ONLY:
                       availability ("only available ones"), location ("just Pune"), or count ("top 2").
                       Do NOT use for semantic/role-based filtering.

  "rerank_existing"  — User wants to semantically SELECT or RANK from the ALREADY SHOWN profiles.
                       Use when user asks: "who could be a lead?", "best Python developer from these",
                       "most experienced", "who fits a backend role?", "which one for QA lead?",
                       "from above list give me...". AI picks from existing results without re-querying.

  "chat_only"        — General question/comment, no search or filter needed.

IMPORTANT:
  - Prefer "rerank_existing" over "filter_existing" whenever the user references role, seniority, or
    any criterion that requires reading skill/experience details.
  - Only use "refine" when you need more candidates than what's currently shown.
  - After "filter_existing" or "rerank_existing", the filtered/reranked list becomes the new baseline.

Return ONLY valid JSON (no markdown fences):
{
  "action": "new_search" | "refine" | "filter_existing" | "rerank_existing" | "chat_only",
  "search_query": "<full natural-language ChromaDB query — only for new_search/refine, else null>",
  "rerank_criteria": "<what to select/rank by — only for rerank_existing, else null>",
  "filters": {
    "available_only": false,
    "location": null
  },
  "response_intro": "<conversational 1-2 sentence reply>"
}"""


def _interpret_user_content(state: SearchState) -> str:
    last_query = state.get("last_search_query") or "none"
    last_results = state.get("last_results") or []
    shown = [
        f"{r['employee']['name']} ({r['employee'].get('title', '')})"
        for r in last_results[:6]
    ]

    ctx = (
        f"Current state:\n"
        f"  Last search query: \"{last_query}\"\n"
        f"  Currently shown profiles ({len(shown)}): {', '.join(shown) if shown else 'none yet'}\n"
        f"  Active filters: {json.dumps(state.get('active_filters') or {})}\n\n"
        f"Conversation:"
    )
    for m in state.get("messages", []):
        ctx += f"\n{m['role'].upper()}: {m['content']}"
    return ctx


# ── Helpers ───────────────────────────────────────────────────────────────────

def _serialize_result(r: dict) -> dict:
    emp = r["employee"]
    return {
        "employee": {
            "id": emp.id,
            "name": emp.name,
            "title": emp.title,
            "email": emp.email,
            "location": emp.location,
            "current_project": emp.current_project,
            "is_available": emp.is_available,
            "created_at": emp.created_at.isoformat(),
            "skills": [
                {
                    "id": s.id,
                    "name": s.name,
                    "category": s.category,
                    "proficiency": s.proficiency,
                    "years_experience": s.years_experience,
                    "is_inferred": s.is_inferred,
                    "employee_id": s.employee_id,
                    "confidence": s.confidence,
                }
                for s in emp.skills
            ],
        },
        "match_score": r["match_score"],
        "explanation": r["explanation"],
    }


def _apply_filters(results: list, filters: dict) -> list:
    if filters.get("available_only"):
        results = [r for r in results if r["employee"].get("is_available")]
    if filters.get("location"):
        loc = filters["location"].lower()
        results = [r for r in results if loc in (r["employee"].get("location") or "").lower()]
    return results


def _build_profiles_text(results: list) -> str:
    text = ""
    for r in results:
        emp = r["employee"]
        skills_str = ", ".join(
            f"{s['name']}({s['proficiency']},{s['years_experience']}yr)"
            for s in emp.get("skills", [])
            if not s.get("is_inferred")
        )
        avail = "Available" if emp.get("is_available") else f"On project: {emp.get('current_project') or 'N/A'}"
        text += (
            f"\nID: {emp['id']} | {emp['name']} | {emp.get('title', '')} | "
            f"{emp.get('location', '')} | {avail}\n"
            f"Skills: {skills_str}\n"
        )
    return text


# ── Rerank prompt ─────────────────────────────────────────────────────────────

_RERANK_PROMPT = """You are an expert HR assistant. The user wants to select or re-rank candidates
from an existing shortlist based on specific criteria.

Selection criteria: "{criteria}"

Candidate profiles:
{profiles}

From the candidates above, select ONLY those who genuinely fit the criteria and re-score them.
Explain clearly why each selected candidate fits (or doesn't).

Return ONLY a valid JSON array (may be empty if no one fits):
[
  {{
    "employee_id": 1,
    "match_score": 92,
    "explanation": "2-3 sentences why this person fits the criteria"
  }}
]
Order by match_score descending. Include only strong matches."""


# ── Nodes ─────────────────────────────────────────────────────────────────────

def interpret_node(state: SearchState, config: RunnableConfig) -> dict:
    provider = config.get("configurable", {}).get("provider", "gemma")

    try:
        raw = chat_completion(
            messages=[
                {"role": "system", "content": _INTERPRET_SYSTEM},
                {"role": "user", "content": _interpret_user_content(state)},
            ],
            provider=provider,
            temperature=0.1,
        )
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"```(?:json)?\n?", "", cleaned).strip().rstrip("`").strip()
        intent = json.loads(cleaned)
    except Exception:
        last = state.get("messages", [{}])[-1].get("content", "")
        intent = {
            "action": "new_search",
            "search_query": last,
            "rerank_criteria": None,
            "filters": {"available_only": False, "location": None},
            "response_intro": "Let me search for that...",
        }

    action = intent.get("action", "new_search")
    update: dict = {
        "pending_action": action,
        "active_filters": intent.get("filters") or {},
        "response_intro": intent.get("response_intro", "Here are the results:"),
    }
    if action in ("new_search", "refine") and intent.get("search_query"):
        update["last_search_query"] = intent["search_query"]
    if action == "rerank_existing" and intent.get("rerank_criteria"):
        update["rerank_criteria"] = intent["rerank_criteria"]

    return update


def search_node(state: SearchState, config: RunnableConfig) -> dict:
    from ..database import SessionLocal
    from .search_service import semantic_search

    provider = config.get("configurable", {}).get("provider", "gemma")
    query = state.get("last_search_query", "")

    db = SessionLocal()
    try:
        raw = semantic_search(query, db, provider=provider, top_k=5)
        results = [_serialize_result(r) for r in raw]
    finally:
        db.close()

    results = _apply_filters(results, state.get("active_filters") or {})
    # Update last_results so future turns work on what the user sees
    return {"last_results": results, "current_results": results}


def filter_node(state: SearchState) -> dict:
    results = list(state.get("last_results") or [])
    results = _apply_filters(results, state.get("active_filters") or {})
    # IMPORTANT: update last_results so next turn's context is accurate
    return {"last_results": results, "current_results": results}


def rerank_node(state: SearchState, config: RunnableConfig) -> dict:
    """Semantically select/re-rank existing results using LLM — no ChromaDB call."""
    provider = config.get("configurable", {}).get("provider", "gemma")
    criteria = state.get("rerank_criteria") or "best overall fit for the role"
    candidates = list(state.get("last_results") or [])

    if not candidates:
        return {"current_results": [], "last_results": []}

    profiles_text = _build_profiles_text(candidates)
    prompt = _RERANK_PROMPT.format(criteria=criteria, profiles=profiles_text)

    try:
        raw = chat_completion(
            messages=[{"role": "user", "content": prompt}],
            provider=provider,
            temperature=0.2,
        )
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"```(?:json)?\n?", "", cleaned).strip().rstrip("`").strip()
        rankings = json.loads(cleaned)
    except Exception:
        # On failure, return candidates unchanged
        return {"current_results": candidates, "last_results": candidates}

    emp_map = {r["employee"]["id"]: r for r in candidates}
    reranked = []
    for rank in sorted(rankings, key=lambda x: x.get("match_score", 0), reverse=True):
        emp_id = rank.get("employee_id")
        if emp_id in emp_map:
            original = emp_map[emp_id]
            reranked.append({
                **original,
                "match_score": rank.get("match_score", original["match_score"]),
                "explanation": rank.get("explanation", original["explanation"]),
            })

    # Update last_results so next turn continues from this refined list
    return {"last_results": reranked, "current_results": reranked}


def chat_only_node(state: SearchState) -> dict:
    return {"current_results": []}


def finalize_node(state: SearchState) -> dict:
    """Append the assistant turn to messages so history is complete."""
    return {"messages": [{"role": "assistant", "content": state.get("response_intro", "")}]}


# ── Routing ───────────────────────────────────────────────────────────────────

def _route(state: SearchState) -> str:
    action = state.get("pending_action", "new_search")
    if action in ("new_search", "refine"):
        return "search"
    if action == "filter_existing":
        return "filter"
    if action == "rerank_existing":
        return "rerank"
    return "chat_only"


# ── Graph factory (singleton) ─────────────────────────────────────────────────

def _build_graph():
    g = StateGraph(SearchState)

    g.add_node("interpret", interpret_node)
    g.add_node("search", search_node)
    g.add_node("filter", filter_node)
    g.add_node("rerank", rerank_node)
    g.add_node("chat_only", chat_only_node)
    g.add_node("finalize", finalize_node)

    g.set_entry_point("interpret")
    g.add_conditional_edges("interpret", _route, {
        "search": "search",
        "filter": "filter",
        "rerank": "rerank",
        "chat_only": "chat_only",
    })
    g.add_edge("search", "finalize")
    g.add_edge("filter", "finalize")
    g.add_edge("rerank", "finalize")
    g.add_edge("chat_only", "finalize")
    g.add_edge("finalize", END)

    return g.compile(checkpointer=MemorySaver())


_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = _build_graph()
    return _graph
