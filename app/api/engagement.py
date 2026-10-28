from flask import jsonify, request
from app.api import api_bp
from app.extensions import db
from app.models.session import ClassSession
from app.models.analytics import FusionResult, EngagementWindow, AudioActivityWindow

@api_bp.route("/sessions/<int:session_id>/engagement", methods=["GET"])
def get_session_engagement(session_id: int):
    """Retrieve synchronized multimodal engagement timeline, audio, and visual trends."""
    session = db.session.get(ClassSession, session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    fusions = FusionResult.query.filter_by(session_id=session_id).order_by(FusionResult.window_start.asc()).all()
    
    # Calculate overall averages
    valid_scores = [f.fused_score for f in fusions if f.fused_score is not None]
    avg_fused = round(sum(valid_scores) / len(valid_scores), 1) if valid_scores else None

    visual_scores = [f.visual_score for f in fusions if f.visual_score is not None]
    avg_visual = round(sum(visual_scores) / len(visual_scores), 1) if visual_scores else None

    audio_scores = [f.audio_score for f in fusions if f.audio_score is not None]
    avg_audio = round(sum(audio_scores) / len(audio_scores), 1) if audio_scores else None

    return jsonify({
        "session_id": session_id,
        "summary": {
            "total_windows": len(fusions),
            "average_fused_score": avg_fused,
            "average_visual_score": avg_visual,
            "average_audio_score": avg_audio,
            "disclaimer": "Scores represent observable physical motion, head orientation, and acoustic activity. They do not measure attention, comprehension, or internal mental state.",
        },
        "timeline": [f.to_dict() for f in fusions],
    }), 200
