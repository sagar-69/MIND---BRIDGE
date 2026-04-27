from __future__ import annotations

import os
import re
from typing import Literal, TypedDict

from langgraph.graph import END, StateGraph

from agents.cbt_advisor import run_cbt
from agents.crisis_handler import handle_crisis
from agents.intake_agent import run_intake
from agents.resource_agent import run_resources


class ChatState(TypedDict, total=False):
    messages: list[dict]
    active_agent: str
    mood_score: int | None
    risk_level: Literal["low", "medium", "high"]
    session_id: str
    _is_new_session: bool


CRISIS_KEYWORDS = [
    "self harm",
    "self-harm",
    "suicide",
    "kill myself",
    "end it",
    "can't go on",
    "cant go on",
    "hopeless",
    "hurt myself",
    "die",
]


def _load_prompt(filename: str) -> str:
    base = os.path.join(os.path.dirname(__file__), "..", "llm", "prompts")
    path = os.path.abspath(os.path.join(base, filename))
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


SYSTEM_INTAKE = _load_prompt("system_intake.txt")
SYSTEM_CBT = _load_prompt("system_cbt.txt")
SYSTEM_CRISIS = _load_prompt("system_crisis.txt")
SYSTEM_RESOURCE = _load_prompt("system_resource.txt")


def _latest_user_text(state: ChatState) -> str:
    for m in reversed(state.get("messages", [])):
        if m.get("role") == "user":
            return (m.get("content") or "").lower()
    return ""


def detect_crisis(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in CRISIS_KEYWORDS)


def route(state: ChatState) -> str:
    text = _latest_user_text(state)
    if detect_crisis(text):
        return "crisis"

    if state.get("_is_new_session"):
        return "intake"

    # lightweight intent routing
    if re.search(r"\b(article|resources?|read|sleep|insomnia|hotline|helpline)\b", text):
        return "resource"
    if re.search(r"\b(breath|breathing|grounding|technique|exercise|panic|anxiety)\b", text):
        return "cbt"

    return "cbt"


def _node_intake(state: ChatState) -> ChatState:
    return run_intake(state, SYSTEM_INTAKE)  # system prompt kept for future LLM-driven intake


def _node_cbt(state: ChatState) -> ChatState:
    return run_cbt(state, SYSTEM_CBT)


def _node_resource(state: ChatState) -> ChatState:
    return run_resources(state, SYSTEM_RESOURCE)


def _node_crisis(state: ChatState) -> ChatState:
    return handle_crisis(state)


def build_graph():
    g = StateGraph(ChatState)
    g.add_node("router", lambda s: s)
    g.add_node("intake", _node_intake)
    g.add_node("cbt", _node_cbt)
    g.add_node("resource", _node_resource)
    g.add_node("crisis", _node_crisis)

    g.set_entry_point("router")

    g.add_conditional_edges(
        "router",
        route,
        {
            "intake": "intake",
            "cbt": "cbt",
            "resource": "resource",
            "crisis": "crisis",
        },
    )
    g.add_edge("intake", END)
    g.add_edge("cbt", END)
    g.add_edge("resource", END)
    g.add_edge("crisis", END)

    return g.compile()


_GRAPH = None


def invoke(state: ChatState) -> ChatState:
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_graph()

    # Hard crisis pre-check before any LLM work.
    if detect_crisis(_latest_user_text(state)):
        return _node_crisis(state)

    return _GRAPH.invoke(state)

