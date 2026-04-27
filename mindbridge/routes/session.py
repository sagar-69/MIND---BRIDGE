from __future__ import annotations

from flask import Blueprint, jsonify, request

from db.session_store import db_factory

session_bp = Blueprint("session", __name__, url_prefix="/session")


@session_bp.post("/new")
def new_session():
    session_id = db_factory().create_session()
    return jsonify({"session_id": session_id})


@session_bp.get("/list")
def list_sessions():
    limit = int(request.args.get("limit", "50"))
    sessions = db_factory().list_sessions(limit=limit)
    return jsonify({"sessions": sessions})


@session_bp.get("/<session_id>/history")
def history(session_id: str):
    state = db_factory().get_state(session_id)
    return jsonify(
        {
            "messages": state.get("messages", []),
            "mood_score": state.get("mood_score"),
            "risk_level": state.get("risk_level", "low"),
            "session_id": session_id,
        }
    )


@session_bp.post("/<session_id>/mood")
def mood_log(session_id: str):
    body = request.get_json(force=True, silent=True) or {}
    score = int(body.get("score", 0))
    db_factory().add_mood_log(session_id, score)
    return jsonify({"ok": True})

