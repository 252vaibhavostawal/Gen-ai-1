from flask import request, jsonify
from app.api import api_bp
from app.extensions import db
from app.models.attendance import AttendanceRecord
from app.models.session import ClassSession
from app.services.attendance_service import attendance_service
from app.utils.validators import validate_attendance_override

@api_bp.route("/sessions/<int:session_id>/attendance", methods=["GET"])
def get_session_attendance(session_id: int):
    """Retrieve timestamped attendance records and stats for a session."""
    session = db.session.get(ClassSession, session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    records = AttendanceRecord.query.filter_by(session_id=session_id).order_by(AttendanceRecord.first_observed_at.asc()).all()
    stats = attendance_service.calculate_session_attendance_stats(session_id)

    return jsonify({
        "session_id": session_id,
        "statistics": stats,
        "records": [r.to_dict() for r in records],
    }), 200

@api_bp.route("/attendance/<int:record_id>/override", methods=["POST"])
def override_attendance_record(record_id: int):
    """Instructor manual attendance override with audit trail."""
    data = request.get_json() or {}
    is_valid, errors = validate_attendance_override(data)
    if not is_valid:
        return jsonify({"errors": errors}), 400

    new_status = data["attendance_status"]
    note = data.get("note", "Manual instructor adjustment")

    updated = attendance_service.manual_override(record_id, new_status, note)
    if not updated:
        return jsonify({"error": "Attendance record not found"}), 404

    return jsonify({
        "message": "Attendance record overridden successfully",
        "record": updated.to_dict(),
    }), 200

@api_bp.route("/sessions/<int:session_id>/map_track", methods=["POST"])
def map_track_to_student(session_id: int):
    """Map anonymous track ID to a registered student."""
    data = request.get_json() or {}
    track_id = data.get("track_id")
    student_id = data.get("student_id")
    note = data.get("note", "Mapped by instructor")

    if not track_id or not student_id:
        return jsonify({"error": "Both track_id and student_id are required"}), 400

    success = attendance_service.map_track_to_student(session_id, int(track_id), int(student_id), note)
    if success:
        return jsonify({"message": f"Track #{track_id} mapped to student #{student_id}"}), 200
    return jsonify({"error": "Failed to map track. Verify track exists in session."}), 404
