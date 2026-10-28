from datetime import datetime, timezone, timedelta
from flask import request, jsonify
from app.api import api_bp
from app.extensions import db
from app.models.settings import PrivacySetting
from app.models.audit import AuditLog
from app.models.analytics import EngagementWindow, AudioActivityWindow, FusionResult
from app.utils.security import log_audit_event

@api_bp.route("/settings/privacy", methods=["GET"])
def get_privacy_settings():
    """Retrieve system privacy, retention, and consent configuration."""
    settings = PrivacySetting.get_settings()
    return jsonify({"settings": settings.to_dict()}), 200

@api_bp.route("/settings/privacy", methods=["POST"])
def update_privacy_settings():
    """Update privacy settings and policies."""
    settings = PrivacySetting.get_settings()
    data = request.get_json() or {}

    if "retain_raw_video" in data:
        settings.retain_raw_video = bool(data["retain_raw_video"])
    if "retain_raw_audio" in data:
        settings.retain_raw_audio = bool(data["retain_raw_audio"])
    if "enable_transcription" in data:
        settings.enable_transcription = bool(data["enable_transcription"])
    if "data_retention_days" in data:
        settings.data_retention_days = max(1, int(data["data_retention_days"]))
    if "consent_required" in data:
        settings.consent_required = bool(data["consent_required"])
    if "allow_export" in data:
        settings.allow_export = bool(data["allow_export"])
    if "blur_unidentified_faces" in data:
        settings.blur_unidentified_faces = bool(data["blur_unidentified_faces"])

    settings.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    log_audit_event("UPDATE_PRIVACY_SETTINGS", "settings", settings.id, "Updated privacy configuration")

    return jsonify({
        "message": "Privacy settings updated successfully",
        "settings": settings.to_dict(),
    }), 200

@api_bp.route("/settings/purge_data", methods=["POST"])
def purge_old_data():
    """Purge granular window data older than retention period."""
    settings = PrivacySetting.get_settings()
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=settings.data_retention_days)

    purged_fusions = FusionResult.query.filter(FusionResult.created_at < cutoff_date).delete()
    purged_engagements = EngagementWindow.query.filter(EngagementWindow.created_at < cutoff_date).delete()
    purged_audio = AudioActivityWindow.query.filter(AudioActivityWindow.created_at < cutoff_date).delete()

    db.session.commit()
    log_audit_event("PURGE_DATA", "data_retention", None, f"Purged older records beyond {settings.data_retention_days} days")

    return jsonify({
        "message": f"Purged historical data older than {settings.data_retention_days} days",
        "purged_records": {
            "fusion_windows": purged_fusions,
            "engagement_windows": purged_engagements,
            "audio_windows": purged_audio,
        },
    }), 200

@api_bp.route("/settings/audit_logs", methods=["GET"])
def get_audit_logs():
    """Retrieve compliance and instructor action audit logs."""
    limit = int(request.args.get("limit", 50))
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return jsonify({
        "count": len(logs),
        "audit_logs": [l.to_dict() for l in logs],
    }), 200
