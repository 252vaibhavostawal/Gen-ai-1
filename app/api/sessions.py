import os
from datetime import datetime, timezone
from flask import request, jsonify, current_app
from app.api import api_bp
from app.extensions import db
from app.models.session import ClassSession
from app.services.session_service import session_coordinator
from app.utils.validators import validate_session_data
from app.utils.security import sanitize_filename, log_audit_event

@api_bp.route("/sessions", methods=["GET"])
def list_sessions():
    """List classroom sessions."""
    sessions = ClassSession.query.order_by(ClassSession.created_at.desc()).all()
    return jsonify({
        "count": len(sessions),
        "sessions": [s.to_dict() for s in sessions],
    }), 200

@api_bp.route("/sessions", methods=["POST"])
def create_session():
    """Create a new classroom session."""
    data = request.get_json() or {}
    is_valid, errors = validate_session_data(data)
    if not is_valid:
        return jsonify({"errors": errors}), 400

    session = ClassSession(
        title=data["title"],
        course_id=data.get("course_id"),
        expected_duration_minutes=int(data.get("expected_duration_minutes", 60)),
        input_source_type=data.get("input_source_type", "webcam"),
        video_file_path=data.get("video_file_path"),
        audio_file_path=data.get("audio_file_path"),
        objectives=data.get("objectives"),
        status="created",
    )
    db.session.add(session)
    db.session.commit()
    log_audit_event("CREATE_SESSION", "session", session.id, f"Created session '{session.title}'")

    return jsonify({"message": "Session created", "session": session.to_dict()}), 201

@api_bp.route("/sessions/<int:session_id>", methods=["GET"])
def get_session(session_id: int):
    """Retrieve full details of a specific session."""
    session = db.session.get(ClassSession, session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    return jsonify({"session": session.to_dict()}), 200

@api_bp.route("/sessions/<int:session_id>/start", methods=["POST"])
def start_session(session_id: int):
    """Start live or pre-recorded processing for a session."""
    session = db.session.get(ClassSession, session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    started = session_coordinator.start_session(session_id, current_app._get_current_object())
    if started:
        return jsonify({"message": "Session started", "status": "running"}), 200
    return jsonify({"error": "Failed to start session runner"}), 500

@api_bp.route("/sessions/<int:session_id>/pause", methods=["POST"])
def pause_session(session_id: int):
    """Pause live processing."""
    paused = session_coordinator.pause_session(session_id)
    if paused:
        return jsonify({"message": "Session paused", "status": "paused"}), 200
    return jsonify({"error": "Session is not running"}), 400

@api_bp.route("/sessions/<int:session_id>/resume", methods=["POST"])
def resume_session(session_id: int):
    """Resume paused processing."""
    resumed = session_coordinator.resume_session(session_id)
    if resumed:
        return jsonify({"message": "Session resumed", "status": "running"}), 200
    return jsonify({"error": "Session is not paused"}), 400

@api_bp.route("/sessions/<int:session_id>/stop", methods=["POST"])
def stop_session(session_id: int):
    """Stop processing."""
    stopped = session_coordinator.stop_session(session_id)
    return jsonify({"message": "Session stopped", "status": "stopped"}), 200

@api_bp.route("/sessions/<int:session_id>/finalize", methods=["POST"])
def finalize_session(session_id: int):
    """Finalize session and calculate overall analytics and recommendations."""
    result = session_coordinator.finalize_session(session_id, current_app._get_current_object())
    if "error" in result:
        return jsonify(result), 404
    return jsonify(result), 200

@api_bp.route("/sessions/upload_media", methods=["POST"])
def upload_media():
    """Safely upload a local video or audio recording for offline processing."""
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Empty filename"}), 400

    clean_name = sanitize_filename(file.filename)
    upload_folder = current_app.config.get("UPLOAD_DIR") or os.path.join(os.getcwd(), "uploads")
    os.makedirs(upload_folder, exist_ok=True)
    
    dest_path = os.path.join(upload_folder, f"{int(datetime.now(timezone.utc).timestamp())}_{clean_name}")
    file.save(dest_path)

    log_audit_event("UPLOAD_MEDIA", "media", None, f"Uploaded local media {clean_name}")
    return jsonify({
        "message": "File uploaded successfully",
        "file_path": dest_path,
        "filename": clean_name,
    }), 201
