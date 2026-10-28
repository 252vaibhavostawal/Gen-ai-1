from datetime import datetime, timezone
from app.extensions import db

class ClassSession(db.Model):
    __tablename__ = "class_sessions"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=True, index=True)
    instructor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    
    date = db.Column(db.Date, nullable=False, default=lambda: datetime.now(timezone.utc).date())
    start_time = db.Column(db.DateTime, nullable=True)
    end_time = db.Column(db.DateTime, nullable=True)
    expected_duration_minutes = db.Column(db.Integer, default=60, nullable=False)
    
    # Input sources: 'webcam', 'video_file', 'synthetic'
    input_source_type = db.Column(db.String(30), default="webcam", nullable=False)
    video_file_path = db.Column(db.String(255), nullable=True)
    audio_file_path = db.Column(db.String(255), nullable=True)
    
    # Session state: 'created', 'running', 'paused', 'stopped', 'finalized'
    status = db.Column(db.String(30), default="created", nullable=False, index=True)
    
    objectives = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    finalized_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    course = db.relationship("Course", back_populates="sessions")
    instructor = db.relationship("User", foreign_keys=[instructor_id])
    attendance_records = db.relationship("AttendanceRecord", back_populates="session", lazy="dynamic", cascade="all, delete-orphan")
    engagement_windows = db.relationship("EngagementWindow", back_populates="session", lazy="dynamic", cascade="all, delete-orphan")
    audio_windows = db.relationship("AudioActivityWindow", back_populates="session", lazy="dynamic", cascade="all, delete-orphan")
    fusion_results = db.relationship("FusionResult", back_populates="session", lazy="dynamic", cascade="all, delete-orphan")
    suggestions = db.relationship("TeachingSuggestion", back_populates="session", lazy="dynamic", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "course_id": self.course_id,
            "course_name": self.course.name if self.course else None,
            "instructor_id": self.instructor_id,
            "date": self.date.isoformat() if self.date else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "expected_duration_minutes": self.expected_duration_minutes,
            "input_source_type": self.input_source_type,
            "video_file_path": self.video_file_path,
            "audio_file_path": self.audio_file_path,
            "status": self.status,
            "objectives": self.objectives,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "finalized_at": self.finalized_at.isoformat() if self.finalized_at else None,
        }
