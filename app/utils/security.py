import os
import re
from functools import wraps
from flask import session, jsonify, request, g
from app.extensions import db
from app.models.audit import AuditLog
from app.models.user import User

def login_required(f):
    """Decorator to require login for protected routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id:
            # For API requests return 401 JSON, for web views could redirect
            if request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required", "code": "UNAUTHORIZED"}), 401
            # In local single-user/development mode, we auto-load or allow default instructor
            return f(*args, **kwargs)
        g.current_user = db.session.get(User, user_id)
        return f(*args, **kwargs)
    return decorated_function

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal attacks."""
    if not filename:
        return "unnamed_file"
    # Remove directory separators and path traversal
    clean = os.path.basename(filename)
    clean = re.sub(r'[^a-zA-Z0-9_.-]', '_', clean)
    clean = re.sub(r'\.{2,}', '.', clean)  # remove repeated dots
    return clean.strip("._") or "file"

def log_audit_event(action: str, target_type: str, target_id: int = None, details: str = None) -> AuditLog:
    """Persist an audit log entry for privacy, compliance, and instructor actions."""
    user_id = session.get("user_id") if session else None
    ip_addr = request.remote_addr if request else "127.0.0.1"
    audit = AuditLog(
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details,
        ip_address=ip_addr,
    )
    db.session.add(audit)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
    return audit
