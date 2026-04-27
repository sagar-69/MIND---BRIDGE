from __future__ import annotations

CRISIS_MESSAGE = """I’m really sorry you’re feeling this way. You don’t have to carry this alone.

If you might hurt yourself or you feel unsafe, please reach out **right now**:

- **iCall (India)**: 9152987821
- **Vandrevala Foundation (India)**: 1860-2662-345
- **Global directory**: https://findahelpline.com

If you’re in immediate danger, please call your local emergency number or go to the nearest emergency room.
"""


def handle_crisis(state: dict) -> dict:
    state["active_agent"] = "crisis_handler"
    state["risk_level"] = "high"
    state.setdefault("messages", []).append(
        {"role": "assistant", "content": CRISIS_MESSAGE, "agent": "Crisis handler"}
    )
    return state

