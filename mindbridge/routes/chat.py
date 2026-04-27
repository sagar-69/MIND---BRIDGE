from __future__ import annotations

import json
from collections.abc import Generator

from flask import Blueprint, Response, jsonify, request, stream_with_context

from agents.crisis_handler import CRISIS_MESSAGE
from agents.intake_agent import run_intake
from agents.orchestrator import (
    SYSTEM_CBT,
    SYSTEM_INTAKE,
    SYSTEM_RESOURCE,
    detect_crisis,
    route,
)
from db.session_store import db_factory
from llm.ollama_client import stream_completion

chat_bp = Blueprint("chat", __name__)


def _sse(data: str) -> str:
    # Send JSON-string payload so the client can safely reconstruct text
    # without newline/token formatting artifacts.
    payload = json.dumps(data)
    return f"data: {payload}\n\n"


@chat_bp.post("/chat")
def chat():
    body = request.get_json(force=True, silent=True) or {}
    user_text = (body.get("message") or "").strip()
    session_id = (body.get("session_id") or "").strip()
    if not user_text or not session_id:
        return jsonify({"error": "message and session_id are required"}), 400

    store = db_factory()
    state_holder = {"state": store.get_state(session_id)}
    state_holder["state"].setdefault("messages", []).append({"role": "user", "content": user_text})

    latest = user_text.lower()

    def generate() -> Generator[str, None, None]:
        assistant_agent = None
        assistant_text_parts: list[str] = []
        try:
            # Hard pre-check: crisis always wins, no LLM latency.
            if detect_crisis(latest):
                state_holder["state"]["risk_level"] = "high"
                assistant_agent = "Crisis handler"
                assistant_text_parts.append(CRISIS_MESSAGE)
                yield _sse(CRISIS_MESSAGE)
                return

            choice = route(state_holder["state"])

            if choice == "intake":
                before_len = len(state_holder["state"].get("messages", []))
                state_holder["state"] = run_intake(state_holder["state"], SYSTEM_INTAKE)
                new_msgs = state_holder["state"].get("messages", [])[before_len:]
                assistant = next((m for m in new_msgs if m.get("role") == "assistant"), None)
                text = (assistant or {}).get("content", "")
                agent = (assistant or {}).get("agent", "Intake")
                assistant_agent = agent
                assistant_text_parts.append(text)
                yield _sse(text)
                return

            system_prompt = SYSTEM_RESOURCE if choice == "resource" else SYSTEM_CBT
            assistant_agent = "Resource agent" if choice == "resource" else "CBT advisor"

            llm_messages = [
                {"role": m["role"], "content": m["content"]}
                for m in state_holder["state"].get("messages", [])
            ]
            for chunk in stream_completion(system_prompt, llm_messages):
                assistant_text_parts.append(chunk)
                yield _sse(chunk)
        finally:
            full_text = "".join(assistant_text_parts).strip()
            if full_text and assistant_agent:
                state_holder["state"].setdefault("messages", []).append(
                    {"role": "assistant", "content": full_text, "agent": assistant_agent}
                )
            store.save_state(state_holder["state"])

    return Response(stream_with_context(generate()), mimetype="text/event-stream")

