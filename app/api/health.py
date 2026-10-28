from datetime import datetime, timezone
from flask import jsonify, current_app
from app.api import api_bp
from app.services.suggestion_service import suggestion_agent

@api_bp.route("/health", methods=["GET"])
def health_check():
    """System health and offline capability verification."""
    ollama_ready = suggestion_agent.check_ollama_availability()
    return jsonify({
        "status": "healthy",
        "app_name": "Multimodal Attendance & Engagement Agent",
        "mode": "offline-first",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "capabilities": {
            "computer_vision": True,
            "audio_processing": True,
            "deterministic_suggestions": True,
            "optional_local_ollama": ollama_ready,
            "sqlite_storage": True,
            "pdf_generation": True,
        },
    }), 200
