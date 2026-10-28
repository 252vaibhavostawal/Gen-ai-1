import json
from datetime import datetime, timezone
from app.extensions import db

class EngagementWindow(db.Model):
    """Visual engagement observations summarized over fixed time windows (e.g. 15s or 30s)."""
    __tablename__ = "engagement_windows"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("class_sessions.id"), nullable=False, index=True)
    track_id = db.Column(db.Integer, nullable=True, index=True)
    
    window_start = db.Column(db.Float, nullable=False)  # seconds from session start
    window_end = db.Column(db.Float, nullable=False)
    valid_duration = db.Column(db.Float, nullable=False)
    
    # Head Pose Indicators
    head_pose_yaw = db.Column(db.Float, nullable=True)     # degrees
    head_pose_pitch = db.Column(db.Float, nullable=True)   # degrees
    head_pose_roll = db.Column(db.Float, nullable=True)    # degrees
    forward_facing_ratio = db.Column(db.Float, default=1.0, nullable=False)  # [0, 1]
    
    # Movement & Inactivity Indicators
    movement_score = db.Column(db.Float, default=0.0, nullable=False)        # pixel delta/frame
    movement_variability = db.Column(db.Float, default=0.0, nullable=False)
    inactivity_duration = db.Column(db.Float, default=0.0, nullable=False)   # seconds
    
    # Visibility and Quality Confidence
    visibility_ratio = db.Column(db.Float, default=1.0, nullable=False)      # [0, 1]
    confidence_score = db.Column(db.Float, default=1.0, nullable=False)      # [0, 1]
    quality_status = db.Column(db.String(30), default="NORMAL", nullable=False)  # 'NORMAL', 'POOR_LIGHTING', 'OCCLUDED', 'INSUFFICIENT_DATA'
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    session = db.relationship("ClassSession", back_populates="engagement_windows")

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "track_id": self.track_id,
            "window_start": round(self.window_start, 2),
            "window_end": round(self.window_end, 2),
            "valid_duration": round(self.valid_duration, 2),
            "head_pose_yaw": round(self.head_pose_yaw, 2) if self.head_pose_yaw is not None else None,
            "head_pose_pitch": round(self.head_pose_pitch, 2) if self.head_pose_pitch is not None else None,
            "head_pose_roll": round(self.head_pose_roll, 2) if self.head_pose_roll is not None else None,
            "forward_facing_ratio": round(self.forward_facing_ratio, 3),
            "movement_score": round(self.movement_score, 3),
            "movement_variability": round(self.movement_variability, 3),
            "inactivity_duration": round(self.inactivity_duration, 2),
            "visibility_ratio": round(self.visibility_ratio, 3),
            "confidence_score": round(self.confidence_score, 3),
            "quality_status": self.quality_status,
        }


class AudioActivityWindow(db.Model):
    """Classroom audio environment measurements summarized over fixed time windows."""
    __tablename__ = "audio_activity_windows"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("class_sessions.id"), nullable=False, index=True)
    
    window_start = db.Column(db.Float, nullable=False)
    window_end = db.Column(db.Float, nullable=False)
    
    speech_duration = db.Column(db.Float, default=0.0, nullable=False)       # seconds
    silence_duration = db.Column(db.Float, default=0.0, nullable=False)      # seconds
    speech_segments_count = db.Column(db.Integer, default=0, nullable=False)
    mean_energy = db.Column(db.Float, default=0.0, nullable=False)           # RMS dB or linear
    peak_energy = db.Column(db.Float, default=0.0, nullable=False)
    
    audio_quality_status = db.Column(db.String(30), default="NORMAL", nullable=False)  # 'NORMAL', 'MUTED', 'HIGH_NOISE', 'CLIPPING', 'INSUFFICIENT_DATA'
    confidence_score = db.Column(db.Float, default=1.0, nullable=False)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    session = db.relationship("ClassSession", back_populates="audio_windows")

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "window_start": round(self.window_start, 2),
            "window_end": round(self.window_end, 2),
            "speech_duration": round(self.speech_duration, 2),
            "silence_duration": round(self.silence_duration, 2),
            "speech_segments_count": self.speech_segments_count,
            "mean_energy": round(self.mean_energy, 4),
            "peak_energy": round(self.peak_energy, 4),
            "audio_quality_status": self.audio_quality_status,
            "confidence_score": round(self.confidence_score, 3),
        }


class FusionResult(db.Model):
    """Synchronized visual and acoustic feature fusion over intervals."""
    __tablename__ = "fusion_results"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("class_sessions.id"), nullable=False, index=True)
    
    window_start = db.Column(db.Float, nullable=False, index=True)
    window_end = db.Column(db.Float, nullable=False)
    
    # Normalized component indicators [0, 100]
    visual_score = db.Column(db.Float, nullable=True)
    audio_score = db.Column(db.Float, nullable=True)
    fused_score = db.Column(db.Float, nullable=True)
    
    visual_weight = db.Column(db.Float, default=0.70, nullable=False)
    audio_weight = db.Column(db.Float, default=0.30, nullable=False)
    confidence = db.Column(db.Float, default=1.0, nullable=False)
    
    # Status: 'CONFIDENT', 'VISUAL_ONLY', 'AUDIO_ONLY', 'INSUFFICIENT_DATA'
    status = db.Column(db.String(30), default="CONFIDENT", nullable=False)
    
    # Explainable indicator details in JSON
    explanation_json = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    session = db.relationship("ClassSession", back_populates="fusion_results")

    def get_explanation(self):
        return json.loads(self.explanation_json) if self.explanation_json else {}

    def set_explanation(self, data):
        self.explanation_json = json.dumps(data)

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "window_start": round(self.window_start, 2),
            "window_end": round(self.window_end, 2),
            "visual_score": round(self.visual_score, 2) if self.visual_score is not None else None,
            "audio_score": round(self.audio_score, 2) if self.audio_score is not None else None,
            "fused_score": round(self.fused_score, 2) if self.fused_score is not None else None,
            "visual_weight": round(self.visual_weight, 2),
            "audio_weight": round(self.audio_weight, 2),
            "confidence": round(self.confidence, 3),
            "status": self.status,
            "explanation": self.get_explanation(),
        }
