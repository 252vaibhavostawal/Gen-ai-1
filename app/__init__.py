import os
from flask import Flask
from app.config import config_by_name
from app.extensions import db, socketio
from app.models.user import User
from app.models.settings import PrivacySetting
from app.models.course import Course
from app.models.student import Student

def create_app(config_name: str = "default") -> Flask:
    """Application factory for the Multimodal Attendance & Engagement Agent."""
    app = Flask(__name__)
    config_obj = config_by_name.get(config_name, config_by_name["default"])
    app.config.from_object(config_obj)

    # Ensure required directories exist
    os.makedirs(app.config["INSTANCE_DIR"], exist_ok=True)
    os.makedirs(app.config["UPLOAD_DIR"], exist_ok=True)
    os.makedirs(app.config["REPORTS_DIR"], exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    socketio.init_app(app)

    # Register blueprints
    from app.api import api_bp
    from app.views import views_bp
    from app.auth import auth_bp

    app.register_blueprint(api_bp)
    app.register_blueprint(views_bp)
    app.register_blueprint(auth_bp)

    # Initialize DB & Seed baseline data
    with app.app_context():
        db.create_all()
        _seed_initial_data()

    return app

def _seed_initial_data():
    """Seed initial instructor user, default course, and privacy settings if empty."""
    # Seed default Privacy Settings
    settings = PrivacySetting.query.first()
    if not settings:
        settings = PrivacySetting(
            retain_raw_video=False,
            retain_raw_audio=False,
            enable_transcription=False,
            data_retention_days=90,
            consent_required=True,
            allow_export=True,
        )
        db.session.add(settings)

    # Seed default Instructor user
    instructor = User.query.filter_by(username="instructor").first()
    if not instructor:
        instructor = User(
            username="instructor",
            email="instructor@local.edu",
            full_name="Course Instructor",
            role="instructor",
        )
        instructor.set_password("admin123")
        db.session.add(instructor)

    # Seed default Course
    default_course = Course.query.filter_by(code="CS101").first()
    if not default_course:
        default_course = Course(
            code="CS101",
            name="Introduction to Artificial Intelligence & Computer Science",
            department="Computer Science",
            semester="Fall 2026",
            description="Foundations of modern AI, neural networks, and educational technologies.",
        )
        db.session.add(default_course)

    # Seed sample registered students for testing
    if Student.query.count() == 0:
        sample_students = [
            Student(student_id="STU001", name="Alice Johnson", email="alice@example.edu", batch="CS-2026", consent_given=True),
            Student(student_id="STU002", name="Brian Smith", email="brian@example.edu", batch="CS-2026", consent_given=True),
            Student(student_id="STU003", name="Catherine Zhao", email="catherine@example.edu", batch="CS-2026", consent_given=True),
            Student(student_id="STU004", name="David Patel", email="david@example.edu", batch="CS-2026", consent_given=True),
            Student(student_id="STU005", name="Elena Rostova", email="elena@example.edu", batch="CS-2026", consent_given=True),
        ]
        db.session.bulk_save_objects(sample_students)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
