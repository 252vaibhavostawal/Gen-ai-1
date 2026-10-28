from flask import jsonify, request
from app.api import api_bp
from app.extensions import db
from app.models.session import ClassSession
from app.models.suggestion import TeachingSuggestion
from app.services.attendance_service import attendance_service
from app.services.suggestion_service import suggestion_agent

@api_bp.route("/sessions/<int:session_id>/suggestions", methods=["GET"])
def get_session_suggestions(session_id: int):
    """Retrieve all AI teaching suggestions generated for a session."""
    session = db.session.get(ClassSession, session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    suggestions = TeachingSuggestion.query.filter_by(session_id=session_id).order_by(TeachingSuggestion.created_at.desc()).all()
    return jsonify({
        "session_id": session_id,
        "count": len(suggestions),
        "suggestions": [s.to_dict() for s in suggestions],
    }), 200

@api_bp.route("/sessions/<int:session_id>/suggestions/generate", methods=["POST"])
def generate_session_suggestions(session_id: int):
    """Generate pedagogical suggestions on demand for a session."""
    session = db.session.get(ClassSession, session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    data = request.get_json() or {}
    prefer_llm = data.get("prefer_llm", False)

    att_stats = attendance_service.calculate_session_attendance_stats(session_id)
    fusions = [f.to_dict() for f in session.fusion_results.all()]
    duration = float(session.expected_duration_minutes)

    result = suggestion_agent.generate_suggestions(
        session_id=session_id,
        session_duration_minutes=duration,
        attendance_stats=att_stats,
        fusion_history=fusions,
        objectives=session.objectives,
        prefer_llm=prefer_llm,
    )

    saved = suggestion_agent.save_suggestion_to_db(session_id, result, duration * 60.0)

    return jsonify({
        "message": "Teaching suggestions generated successfully",
        "suggestion": saved.to_dict(),
    }), 201
