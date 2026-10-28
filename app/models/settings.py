from datetime import datetime, timezone
from app.extensions import db

class PrivacySetting(db.Model):
    __tablename__ = "privacy_settings"

    id = db.Column(db.Integer, primary_key=True)
    retain_raw_video = db.Column(db.Boolean, default=False, nullable=False)
    retain_raw_audio = db.Column(db.Boolean, default=False, nullable=False)
    enable_transcription = db.Column(db.Boolean, default=False, nullable=False)
    data_retention_days = db.Column(db.Integer, default=90, nullable=False)
    consent_required = db.Column(db.Boolean, default=True, nullable=False)
    allow_export = db.Column(db.Boolean, default=True, nullable=False)
    blur_unidentified_faces = db.Column(db.Boolean, default=False, nullable=False)
    
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    @classmethod
    def get_settings(cls):
        settings = cls.query.first()
        if not settings:
            settings = cls()
            db.session.add(settings)
            db.session.commit()
        return settings

    def to_dict(self):
        return {
            "id": self.id,
            "retain_raw_video": self.retain_raw_video,
            "retain_raw_audio": self.retain_raw_audio,
            "enable_transcription": self.enable_transcription,
            "data_retention_days": self.data_retention_days,
            "consent_required": self.consent_required,
            "allow_export": self.allow_export,
            "blur_unidentified_faces": self.blur_unidentified_faces,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
