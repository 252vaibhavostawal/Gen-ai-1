from datetime import datetime, timezone
from app.extensions import db

class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    email = db.Column(db.String(120), nullable=True)
    batch = db.Column(db.String(80), nullable=False, default="Default Batch", index=True)
    profile_image = db.Column(db.String(255), nullable=True)
    enrollment_status = db.Column(db.String(20), nullable=False, default="active")  # 'active', 'inactive'
    consent_given = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    attendance_records = db.relationship("AttendanceRecord", back_populates="student", lazy="dynamic", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "name": self.name,
            "email": self.email,
            "batch": self.batch,
            "profile_image": self.profile_image,
            "enrollment_status": self.enrollment_status,
            "consent_given": self.consent_given,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
