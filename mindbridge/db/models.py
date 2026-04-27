from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional


Role = Literal["user", "assistant", "system"]


@dataclass(frozen=True)
class Message:
    session_id: str
    role: Role
    content: str
    agent: Optional[str] = None
    timestamp: Optional[datetime] = None


@dataclass(frozen=True)
class Session:
    id: str
    created_at: datetime
    mood_score: Optional[int] = None
    risk_level: str = "low"


@dataclass(frozen=True)
class MoodLog:
    session_id: str
    score: int
    logged_at: datetime

