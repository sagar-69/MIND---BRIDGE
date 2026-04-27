from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Optional

from pymongo import MongoClient


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


class BaseStore:
    def create_session(self) -> str:
        raise NotImplementedError

    def list_sessions(self, limit: int = 50) -> list[dict]:
        raise NotImplementedError

    def get_state(self, session_id: str) -> dict:
        raise NotImplementedError

    def save_state(self, state: dict) -> None:
        raise NotImplementedError

    def add_mood_log(self, session_id: str, score: int) -> None:
        raise NotImplementedError


class SQLiteStore(BaseStore):
    def __init__(self, path: str = "mindbridge.db"):
        self.path = path
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions(
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    mood_score INTEGER,
                    risk_level TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    agent TEXT,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS mood_logs(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    logged_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                )
                """
            )

    def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO sessions(id, created_at, mood_score, risk_level) VALUES(?, ?, ?, ?)",
                (session_id, _now_iso(), None, "low"),
            )
        return session_id

    def list_sessions(self, limit: int = 50) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, created_at, mood_score, risk_level FROM sessions ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_state(self, session_id: str) -> dict:
        with self._conn() as conn:
            s = conn.execute(
                "SELECT id, created_at, mood_score, risk_level FROM sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
            if not s:
                # create-on-read for robustness
                conn.execute(
                    "INSERT INTO sessions(id, created_at, mood_score, risk_level) VALUES(?, ?, ?, ?)",
                    (session_id, _now_iso(), None, "low"),
                )
                mood_score, risk_level = None, "low"
            else:
                mood_score, risk_level = s["mood_score"], s["risk_level"]

            msgs = conn.execute(
                "SELECT role, content, agent, timestamp FROM messages WHERE session_id = ? ORDER BY id ASC",
                (session_id,),
            ).fetchall()

        messages = [
            {
                "role": m["role"],
                "content": m["content"],
                **({"agent": m["agent"]} if m["agent"] else {}),
            }
            for m in msgs
        ]

        return {
            "messages": messages,
            "active_agent": "orchestrator",
            "mood_score": mood_score,
            "risk_level": risk_level or "low",
            "session_id": session_id,
            "_is_new_session": len(messages) == 0,
        }

    def save_state(self, state: dict) -> None:
        session_id = state["session_id"]
        mood_score = state.get("mood_score")
        risk_level = state.get("risk_level") or "low"

        with self._conn() as conn:
            conn.execute(
                "UPDATE sessions SET mood_score = ?, risk_level = ? WHERE id = ?",
                (mood_score, risk_level, session_id),
            )

            # naive approach: append only the most recent assistant/user turn if new
            # We detect newness by comparing count; good enough for local-first MVP.
            existing_count = conn.execute(
                "SELECT COUNT(*) AS c FROM messages WHERE session_id = ?",
                (session_id,),
            ).fetchone()["c"]
            new_messages = state.get("messages", [])[existing_count:]

            for msg in new_messages:
                conn.execute(
                    "INSERT INTO messages(session_id, role, content, agent, timestamp) VALUES(?, ?, ?, ?, ?)",
                    (
                        session_id,
                        msg.get("role"),
                        msg.get("content"),
                        msg.get("agent"),
                        _now_iso(),
                    ),
                )

    def add_mood_log(self, session_id: str, score: int) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO mood_logs(session_id, score, logged_at) VALUES(?, ?, ?)",
                (session_id, int(score), _now_iso()),
            )


class MongoStore(BaseStore):
    def __init__(self, mongo_uri: str):
        self.client = MongoClient(mongo_uri)
        self.db = self.client.get_database("mindbridge")
        self.sessions = self.db.get_collection("sessions")
        self.messages = self.db.get_collection("messages")
        self.mood_logs = self.db.get_collection("mood_logs")
        self.sessions.create_index("created_at")
        self.messages.create_index([("session_id", 1), ("created_at", 1)])

    def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        self.sessions.insert_one(
            {
                "_id": session_id,
                "created_at": _now_iso(),
                "mood_score": None,
                "risk_level": "low",
            }
        )
        return session_id

    def list_sessions(self, limit: int = 50) -> list[dict]:
        docs = list(self.sessions.find({}, limit=limit).sort("created_at", -1))
        return [
            {
                "id": d["_id"],
                "created_at": d["created_at"],
                "mood_score": d.get("mood_score"),
                "risk_level": d.get("risk_level", "low"),
            }
            for d in docs
        ]

    def get_state(self, session_id: str) -> dict:
        s = self.sessions.find_one({"_id": session_id})
        if not s:
            self.sessions.insert_one(
                {
                    "_id": session_id,
                    "created_at": _now_iso(),
                    "mood_score": None,
                    "risk_level": "low",
                }
            )
            s = {"mood_score": None, "risk_level": "low"}

        msgs = list(self.messages.find({"session_id": session_id}).sort("created_at", 1))
        messages = [
            {
                "role": m["role"],
                "content": m["content"],
                **({"agent": m["agent"]} if m.get("agent") else {}),
            }
            for m in msgs
        ]

        return {
            "messages": messages,
            "active_agent": "orchestrator",
            "mood_score": s.get("mood_score"),
            "risk_level": s.get("risk_level", "low"),
            "session_id": session_id,
            "_is_new_session": len(messages) == 0,
        }

    def save_state(self, state: dict) -> None:
        session_id = state["session_id"]
        mood_score = state.get("mood_score")
        risk_level = state.get("risk_level") or "low"

        self.sessions.update_one(
            {"_id": session_id},
            {"$set": {"mood_score": mood_score, "risk_level": risk_level}},
            upsert=True,
        )

        # append-only (assumes in-order calls per session)
        existing_count = self.messages.count_documents({"session_id": session_id})
        new_messages = state.get("messages", [])[existing_count:]
        if new_messages:
            self.messages.insert_many(
                [
                    {
                        "session_id": session_id,
                        "role": m.get("role"),
                        "content": m.get("content"),
                        "agent": m.get("agent"),
                        "created_at": _now_iso(),
                    }
                    for m in new_messages
                ]
            )

    def add_mood_log(self, session_id: str, score: int) -> None:
        self.mood_logs.insert_one(
            {"session_id": session_id, "score": int(score), "created_at": _now_iso()}
        )


_STORE: Optional[BaseStore] = None


def db_factory() -> BaseStore:
    global _STORE
    if _STORE is not None:
        return _STORE

    mongo_uri = os.getenv("MONGO_URI", "").strip()
    if mongo_uri:
        _STORE = MongoStore(mongo_uri)
    else:
        _STORE = SQLiteStore()
    return _STORE

