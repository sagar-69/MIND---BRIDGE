from __future__ import annotations

from llm.ollama_client import chat_completion


def run_resources(state: dict, system_prompt: str) -> dict:
    state["active_agent"] = "resource_agent"
    messages = state.get("messages", [])
    llm_messages = [{"role": m["role"], "content": m["content"]} for m in messages if m.get("role") != "system"]
    reply = chat_completion(system_prompt, llm_messages)

    state["messages"].append({"role": "assistant", "content": reply, "agent": "Resource agent"})
    return state

