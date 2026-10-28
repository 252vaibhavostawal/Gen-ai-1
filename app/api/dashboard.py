from datetime import datetime, timezone
from flask import jsonify
from app.api import api_bp
from app.extensions import db
from app.models.student import Student
from app.models.session import ClassSession
from app.models.attendance import AttendanceRecord
from app.models.analytics import FusionResult
from app.models.suggestion import TeachingSuggestion

@api_bp.route("/dashboard/summary", methods=["GET"])
def dashboard_summary():
    """Retrieve top-level operational metrics and recent session activity."""
    total_students = Student.query.count()
    active_students = Student.query.filter_by(enrollment_status="active").count()
    total_sessions = ClassSession.query.count()
    
    # Active running session check
    running_session = ClassSession.query.filter_by(status="running").first()
    
    # Overall attendance statistics across all completed sessions
    all_records = AttendanceRecord.query.all()
    present_total = sum(1 for r in all_records if r.attendance_status == "PRESENT")
    late_total = sum(1 for r in all_records if r.attendance_status == "LATE" or r.is_late)
    absent_total = sum(1 for r in all_records if r.attendance_status == "ABSENT")
    total_attended = present_total + late_total
    
    overall_att_pct = (
        round((total_attended / float(len(all_records))) * 100.0, 1)
        if len(all_records) > 0
        else 0.0
    )

    # Average observable engagement indicator
    fusions = FusionResult.query.all()
    valid_scores = [f.fused_score for f in fusions if f.fused_score is not None]
    avg_engagement = round(sum(valid_scores) / len(valid_scores), 1) if valid_scores else 0.0

    # Recent sessions
    recent_sessions = [
        s.to_dict()
        for s in ClassSession.query.order_by(ClassSession.created_at.desc()).limit(5).all()
    ]

    # Recent pedagogical suggestions
    recent_suggestions = [
        s.to_dict()
        for s in TeachingSuggestion.query.order_by(TeachingSuggestion.created_at.desc()).limit(3).all()
    ]

    return jsonify({
        "metrics": {
            "total_registered_students": total_students,
            "active_students": active_students,
            "total_classes_conducted": total_sessions,
            "current_session": running_session.to_dict() if running_session else None,
            "overall_attendance_percentage": overall_att_pct,
            "total_present": present_total,
            "total_late": late_total,
            "total_absent": absent_total,
            "average_engagement_score": avg_engagement,
            "offline_status": "ONLINE_LOCAL",
        },
        "recent_sessions": recent_sessions,
        "recent_suggestions": recent_suggestions,
    }), 200
