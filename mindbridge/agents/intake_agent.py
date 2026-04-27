from __future__ import annotations

import re

from db.session_store import db_factory


INTAKE_QUESTIONS = [
    "To start gently — how have things been feeling for you lately?",
    "Over the last couple of weeks, have you been finding it harder to enjoy things you usually like? (You can answer in your own words.)",
    "How has your sleep been recently (falling asleep, staying asleep, or waking too early)?",
]

RATING_QUESTION = (
    "One quick check-in (0–3): over the last 2 weeks, how often have you felt overwhelmed or down?\n"
    "0 = not at all, 1 = several days, 2 = more than half the days, 3 = nearly every day"
)


def _count_intake_turns(messages: list[dict]) -> int:
    return sum(1 for m in messages if m.get("role") == "assistant" and m.get("agent") == "Intake")


def _extract_rating_0_3(text: str) -> int | None:
    m = re.search(r"\b([0-3])\b", text)
    if not m:
        return None
    return int(m.group(1))


def run_intake(state: dict, system_prompt: str) -> dict:
    """
    Intake asks one question at a time for the first 2-3 turns.
    Final step collects a small 0-3 rating and maps it to a rough 0-27 mood_score.
    """
    messages = state.get("messages", [])
    turns_done = _count_intake_turns(messages)

    state["active_agent"] = "intake_agent"

    if turns_done < len(INTAKE_QUESTIONS):
        prompt = INTAKE_QUESTIONS[turns_done]
        state["messages"].append({"role": "assistant", "content": prompt, "agent": "Intake"})
        return state

    # rating step
    if turns_done == len(INTAKE_QUESTIONS):
        state["messages"].append({"role": "assistant", "content": RATING_QUESTION, "agent": "Intake"})
        return state

    # parse last user message for rating
    last_user = next((m for m in reversed(messages) if m.get("role") == "user"), {})
    rating = _extract_rating_0_3(last_user.get("content", ""))
    if rating is None:
        state["messages"].append(
            {
                "role": "assistant",
                "content": "If you can, reply with a single number from 0 to 3 (it’s totally okay if you’re not sure).",
                "agent": "Intake",
            }
        )
        return state

    mood_score = int(rating * 9)  # 0..27 rough mapping
    state["mood_score"] = mood_score
    db_factory().add_mood_log(state["session_id"], mood_score)

    # hand off to CBT advisor with a warm transition
    transition = (
        "Thank you for sharing that. If you’re open to it, we can try one small coping step together right now.\n\n"
        "What feels most pressing in this moment: racing thoughts, a heavy mood, or trouble sleeping?"
    )
    state["messages"].append({"role": "assistant", "content": transition, "agent": "Intake"})
    return state

