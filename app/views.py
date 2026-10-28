from flask import Blueprint, render_template, abort, Response, current_app
from app.extensions import db
from app.models.session import ClassSession
from app.models.student import Student
from app.models.course import Course
from app.models.attendance import AttendanceRecord
from app.models.analytics import FusionResult
from app.models.suggestion import TeachingSuggestion
from app.models.settings import PrivacySetting
from app.services.attendance_service import attendance_service
from app.services.session_service import session_coordinator

views_bp = Blueprint("main", __name__)

@views_bp.route("/")
def dashboard_view():
    return render_template("index.html")

@views_bp.route("/students")
def students_view():
    students = Student.query.order_by(Student.name.asc()).all()
    batches = db.session.query(Student.batch).distinct().all()
    batch_list = [b[0] for b in batches if b[0]]
    return render_template("students.html", students=students, batches=batch_list)

@views_bp.route("/sessions")
def sessions_view():
    sessions = ClassSession.query.order_by(ClassSession.created_at.desc()).all()
    courses = Course.query.all()
    return render_template("sessions.html", sessions=sessions, courses=courses)

@views_bp.route("/sessions/<int:session_id>")
def session_detail_view(session_id: int):
    session = db.session.get(ClassSession, session_id)
    if not session:
        abort(404)
    stats = attendance_service.calculate_session_attendance_stats(session_id)
    records = AttendanceRecord.query.filter_by(session_id=session_id).all()
    suggestions = TeachingSuggestion.query.filter_by(session_id=session_id).all()
    return render_template(
        "session_detail.html",
        session=session,
        stats=stats,
        records=records,
        suggestions=suggestions,
    )

@views_bp.route("/live/<int:session_id>")
def live_monitor_view(session_id: int):
    session = db.session.get(ClassSession, session_id)
    if not session:
        abort(404)
    students = Student.query.filter_by(enrollment_status="active").all()
    return render_template("live_monitor.html", session=session, students=students)

@views_bp.route("/attendance/<int:session_id>")
def attendance_view(session_id: int):
    session = db.session.get(ClassSession, session_id)
    if not session:
        abort(404)
    records = AttendanceRecord.query.filter_by(session_id=session_id).all()
    stats = attendance_service.calculate_session_attendance_stats(session_id)
    students = Student.query.filter_by(enrollment_status="active").all()
    return render_template("attendance.html", session=session, records=records, stats=stats, students=students)

@views_bp.route("/engagement/<int:session_id>")
def engagement_view(session_id: int):
    session = db.session.get(ClassSession, session_id)
    if not session:
        abort(404)
    fusions = FusionResult.query.filter_by(session_id=session_id).order_by(FusionResult.window_start.asc()).all()
    return render_template("engagement.html", session=session, fusions=fusions)

@views_bp.route("/suggestions/<int:session_id>")
def suggestions_view(session_id: int):
    session = db.session.get(ClassSession, session_id)
    if not session:
        abort(404)
    suggestions = TeachingSuggestion.query.filter_by(session_id=session_id).order_by(TeachingSuggestion.created_at.desc()).all()
    return render_template("suggestions.html", session=session, suggestions=suggestions)

@views_bp.route("/reports")
def reports_view():
    sessions = ClassSession.query.order_by(ClassSession.created_at.desc()).all()
    return render_template("reports.html", sessions=sessions)

@views_bp.route("/settings")
def settings_view():
    settings = PrivacySetting.get_settings()
    return render_template("settings.html", settings=settings)

@views_bp.route("/video_feed/<int:session_id>")
def video_feed(session_id: int):
    """Stream MJPEG frames from the active runner."""
    runner = session_coordinator.runners.get(session_id)
    if not runner:
        # Return fallback static frame
        return Response(b"", mimetype="multipart/x-mixed-replace; boundary=frame")

    def generate_mjpeg():
        while runner and runner.is_alive():
            has_frame, frame, _ = runner.video_service.read_frame()
            if has_frame and frame is not None:
                jpg_bytes = runner.video_service.encode_jpeg(frame)
                if jpg_bytes:
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n\r\n" + jpg_bytes + b"\r\n"
                    )
            time.sleep(0.1)

    import time
    return Response(generate_mjpeg(), mimetype="multipart/x-mixed-replace; boundary=frame")
