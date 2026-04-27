from __future__ import annotations

from flask import Blueprint, jsonify

from llm.ollama_client import ping

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health():
    return jsonify({"status": "ok" if ping() else "ollama_offline"})

