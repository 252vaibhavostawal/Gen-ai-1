import json
from datetime import datetime, timezone
from app.extensions import db

class TeachingSuggestion(db.Model):
    """Explainable AI-assisted and rule-based pedagogical insights for instructors."""
    __tablename__ = "teaching_suggestions"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("class_sessions.id"), nullable=False, index=True)
    
    timestamp = db.Column(db.Float, nullable=False)  # session elapsed seconds
    pattern_summary = db.Column(db.Text, nullable=False)
    
    # List of actionable recommendations serialized as JSON
    actionable_suggestions_json = db.Column(db.Text, nullable=False)
    
    # Supporting multimodal evidence and metrics serialized as JSON
    evidence_json = db.Column(db.Text, nullable=False)
    
    # Confidence or evidence quality explanation
    confidence_level = db.Column(db.String(20), default="MEDIUM", nullable=False)  # 'HIGH', 'MEDIUM', 'LOW'
    confidence_explanation = db.Column(db.Text, nullable=True)
    limitations_note = db.Column(db.Text, nullable=True)
    
    # Source engine: 'deterministic' or 'ollama'
    source_engine = db.Column(db.String(30), default="deterministic", nullable=False)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    session = db.relationship("ClassSession", back_populates="suggestions")

    def get_suggestions(self):
        return json.loads(self.actionable_suggestions_json) if self.actionable_suggestions_json else []

    def set_suggestions(self, suggestions_list):
        self.actionable_suggestions_json = json.dumps(suggestions_list)

    def get_evidence(self):
        return json.loads(self.evidence_json) if self.evidence_json else {}

    def set_evidence(self, evidence_dict):
        self.evidence_json = json.dumps(evidence_dict)

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "timestamp": round(self.timestamp, 2),
            "pattern_summary": self.pattern_summary,
            "actionable_suggestions": self.get_suggestions(),
            "evidence": self.get_evidence(),
            "confidence_level": self.confidence_level,
            "confidence_explanation": self.confidence_explanation,
            "limitations_note": self.limitations_note,
            "source_engine": self.source_engine,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
