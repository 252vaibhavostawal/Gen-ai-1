import json
from datetime import datetime, timezone
from app.extensions import db

class AttendanceRecord(db.Model):
    __tablename__ = "attendance_records"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("class_sessions.id"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=True, index=True)
    anonymous_track_id = db.Column(db.Integer, nullable=False, index=True)
    
    first_observed_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    confirmed_at = db.Column(db.DateTime, nullable=True)
    last_observed_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    accumulated_duration = db.Column(db.Float, default=0.0, nullable=False)  # in seconds
    
    # Status: 'UNCONFIRMED', 'PRESENT', 'ABSENT', 'LATE', 'DEPARTED_EARLY', 'MANUALLY_OVERRIDDEN'
    attendance_status = db.Column(db.String(30), default="UNCONFIRMED", nullable=False, index=True)
    is_late = db.Column(db.Boolean, default=False, nullable=False)
    
    # Verification method: 'AUTOMATIC_SUSTAINED', 'MANUAL_INSTRUCTOR', 'ANONYMOUS_UNVERIFIED'
    verification_method = db.Column(db.String(40), default="AUTOMATIC_SUSTAINED", nullable=False)
    manual_correction_note = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    session = db.relationship("ClassSession", back_populates="attendance_records")
    student = db.relationship("Student", back_populates="attendance_records")

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "student_id": self.student_id,
            "student_name": self.student.name if self.student else "Anonymous Track #" + str(self.anonymous_track_id),
            "student_roll": self.student.student_id if self.student else None,
            "anonymous_track_id": self.anonymous_track_id,
            "first_observed_at": self.first_observed_at.isoformat() if self.first_observed_at else None,
            "confirmed_at": self.confirmed_at.isoformat() if self.confirmed_at else None,
            "last_observed_at": self.last_observed_at.isoformat() if self.last_observed_at else None,
            "accumulated_duration": round(self.accumulated_duration, 2),
            "attendance_status": self.attendance_status,
            "is_late": self.is_late,
            "verification_method": self.verification_method,
            "manual_correction_note": self.manual_correction_note,
        }


class TrackObservation(db.Model):
    """Raw track observation snapshots for audit and tracking continuity."""
    __tablename__ = "track_observations"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("class_sessions.id"), nullable=False, index=True)
    track_id = db.Column(db.Integer, nullable=False, index=True)
    timestamp = db.Column(db.Float, nullable=False, index=True)  # session elapsed seconds
    
    # Bounding box JSON: [x, y, w, h]
    bbox_json = db.Column(db.String(120), nullable=False)
    confidence = db.Column(db.Float, default=1.0, nullable=False)
    head_pose_yaw = db.Column(db.Float, nullable=True)
    head_pose_pitch = db.Column(db.Float, nullable=True)
    head_pose_roll = db.Column(db.Float, nullable=True)

    def get_bbox(self):
        return json.loads(self.bbox_json) if self.bbox_json else []

    def set_bbox(self, bbox):
        self.bbox_json = json.dumps(bbox)
