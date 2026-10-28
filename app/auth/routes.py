from datetime import datetime, timezone
from flask import request, jsonify, session, render_template, redirect, url_for
from app.auth import auth_bp
from app.extensions import db
from app.models.user import User
from app.utils.security import log_audit_event

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        data = request.get_json() if request.is_json else request.form
        username = data.get("username", "").strip()
        password = data.get("password", "")

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session["user_id"] = user.id
            session["username"] = user.username
            session["role"] = user.role
            user.last_login = datetime.now(timezone.utc)
            db.session.commit()
            log_audit_event("LOGIN_SUCCESS", "user", user.id, f"User {username} logged in")

            if request.is_json:
                return jsonify({"message": "Login successful", "user": user.to_dict()}), 200
            return redirect(url_for("main.dashboard_view"))

        log_audit_event("LOGIN_FAILED", "user", None, f"Failed login attempt for {username}")
        if request.is_json:
            return jsonify({"error": "Invalid username or password"}), 401
        return render_template("login.html", error="Invalid username or password")

    return render_template("login.html")

@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    user_id = session.get("user_id")
    if user_id:
        log_audit_event("LOGOUT", "user", user_id, "User logged out")
    session.clear()
    if request.is_json:
        return jsonify({"message": "Logged out"}), 200
    return redirect(url_for("auth.login"))

@auth_bp.route("/me", methods=["GET"])
def current_user_info():
    user_id = session.get("user_id")
    if not user_id:
        # Default instructor in local mode
        return jsonify({
            "authenticated": False,
            "user": {"username": "Instructor", "role": "instructor", "is_local": True}
        }), 200
    user = db.session.get(User, user_id)
    return jsonify({
        "authenticated": True,
        "user": user.to_dict() if user else None
    }), 200
