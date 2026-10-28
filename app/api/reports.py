import os
from flask import jsonify, Response, send_file, request, current_app
from app.api import api_bp
from app.extensions import db
from app.models.session import ClassSession
from app.services.report_service import report_service
from app.utils.security import log_audit_event

@api_bp.route("/reports/attendance/<int:session_id>", methods=["GET"])
def download_attendance_csv(session_id: int):
    """Download session attendance log in CSV format."""
    session = db.session.get(ClassSession, session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    csv_content = report_service.generate_session_attendance_csv(session_id)
    log_audit_event("EXPORT_REPORT_CSV", "session", session_id, "Exported attendance CSV")
    
    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=attendance_session_{session_id}.csv"}
    )

@api_bp.route("/reports/engagement/<int:session_id>", methods=["GET"])
def download_engagement_csv(session_id: int):
    """Download multimodal engagement timeline in CSV format."""
    session = db.session.get(ClassSession, session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    csv_content = report_service.generate_engagement_timeline_csv(session_id)
    log_audit_event("EXPORT_ENGAGEMENT_CSV", "session", session_id, "Exported engagement timeline CSV")
    
    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=engagement_session_{session_id}.csv"}
    )

@api_bp.route("/reports/pdf/<int:session_id>", methods=["GET"])
def download_pdf_report(session_id: int):
    """Generate and download complete printable PDF report."""
    session = db.session.get(ClassSession, session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    try:
        pdf_path = report_service.generate_session_pdf_report(session_id)
        log_audit_event("EXPORT_REPORT_PDF", "session", session_id, "Generated PDF report")
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=os.path.basename(pdf_path),
            mimetype="application/pdf",
        )
    except Exception as e:
        return jsonify({"error": f"Failed to generate PDF report: {str(e)}"}), 500
