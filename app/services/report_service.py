import os
import csv
import io
from datetime import datetime, timezone
from typing import Dict, List, Optional
from flask import current_app
from app.extensions import db
from app.models.session import ClassSession
from app.models.attendance import AttendanceRecord
from app.models.analytics import EngagementWindow, AudioActivityWindow, FusionResult
from app.models.suggestion import TeachingSuggestion
from app.models.student import Student

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

class ReportService:
    """Generates comprehensive CSV and printable PDF reports for classroom sessions and attendance."""

    def __init__(self, reports_dir: Optional[str] = None):
        self.reports_dir = reports_dir

    def _get_reports_dir(self) -> str:
        if self.reports_dir:
            return self.reports_dir
        if current_app and "REPORTS_DIR" in current_app.config:
            d = str(current_app.config["REPORTS_DIR"])
        else:
            d = os.path.join(os.getcwd(), "reports")
        os.makedirs(d, exist_ok=True)
        return d

    def generate_session_attendance_csv(self, session_id: int) -> str:
        """Export session attendance records to a CSV string."""
        session = db.session.get(ClassSession, session_id)
        records = AttendanceRecord.query.filter_by(session_id=session_id).all()

        output = io.StringIO()
        writer = csv.writer(output)

        # Header metadata
        writer.writerow(["# Multimodal Attendance & Engagement Agent - Attendance Report"])
        writer.writerow(["# Session Title", session.title if session else "N/A"])
        writer.writerow(["# Date", session.date.isoformat() if session and session.date else "N/A"])
        writer.writerow(["# Generated At (UTC)", datetime.now(timezone.utc).isoformat()])
        writer.writerow([])

        # Table columns
        writer.writerow([
            "Record ID",
            "Track ID",
            "Student Roll / ID",
            "Student Name",
            "Status",
            "First Observed",
            "Confirmed At",
            "Last Observed",
            "Observed Duration (sec)",
            "Late Arrival",
            "Verification Method",
            "Manual Notes",
        ])

        for r in records:
            writer.writerow([
                r.id,
                r.anonymous_track_id,
                r.student.student_id if r.student else "Unassigned",
                r.student.name if r.student else f"Anonymous #{r.anonymous_track_id}",
                r.attendance_status,
                r.first_observed_at.strftime("%H:%M:%S") if r.first_observed_at else "N/A",
                r.confirmed_at.strftime("%H:%M:%S") if r.confirmed_at else "N/A",
                r.last_observed_at.strftime("%H:%M:%S") if r.last_observed_at else "N/A",
                round(r.accumulated_duration, 1),
                "YES" if r.is_late else "NO",
                r.verification_method,
                r.manual_correction_note or "",
            ])

        return output.getvalue()

    def generate_engagement_timeline_csv(self, session_id: int) -> str:
        """Export fusion analytics timeline to a CSV string."""
        session = db.session.get(ClassSession, session_id)
        fusions = FusionResult.query.filter_by(session_id=session_id).order_by(FusionResult.window_start).all()

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(["# Multimodal Attendance & Engagement Agent - Engagement Timeline"])
        writer.writerow(["# Session Title", session.title if session else "N/A"])
        writer.writerow(["# Generated At (UTC)", datetime.now(timezone.utc).isoformat()])
        writer.writerow([])

        writer.writerow([
            "Window Start (s)",
            "Window End (s)",
            "Visual Indicator (0-100)",
            "Audio Indicator (0-100)",
            "Fused Indicator (0-100)",
            "Visual Weight",
            "Audio Weight",
            "Confidence",
            "Modality Status",
        ])

        for f in fusions:
            writer.writerow([
                round(f.window_start, 1),
                round(f.window_end, 1),
                f.visual_score if f.visual_score is not None else "N/A",
                f.audio_score if f.audio_score is not None else "N/A",
                f.fused_score if f.fused_score is not None else "N/A",
                round(f.visual_weight, 2),
                round(f.audio_weight, 2),
                round(f.confidence, 2),
                f.status,
            ])

        return output.getvalue()

    def generate_session_pdf_report(self, session_id: int) -> str:
        """Generate a professional printable PDF report using ReportLab."""
        session = db.session.get(ClassSession, session_id)
        records = AttendanceRecord.query.filter_by(session_id=session_id).all()
        fusions = FusionResult.query.filter_by(session_id=session_id).order_by(FusionResult.window_start).all()
        suggestions = TeachingSuggestion.query.filter_by(session_id=session_id).all()

        filename = f"report_session_{session_id}_{int(datetime.now(timezone.utc).timestamp())}.pdf"
        filepath = os.path.join(self._get_reports_dir(), filename)

        doc = SimpleDocTemplate(
            filepath,
            pagesize=letter,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#1e293b"),
            spaceAfter=10,
        )
        heading_style = ParagraphStyle(
            "SectionHeading",
            parent=styles["Heading2"],
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#0f766e"),
            spaceBefore=14,
            spaceAfter=6,
        )
        body_style = styles["Normal"]
        disclaimer_style = ParagraphStyle(
            "Disclaimer",
            parent=styles["Italic"],
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#64748b"),
        )

        story = []

        # Title
        story.append(Paragraph("Session Attendance & Multimodal Report", title_style))
        session_title = session.title if session else f"Session #{session_id}"
        session_date = session.date.strftime("%Y-%m-%d") if session and session.date else "N/A"
        course_name = session.course.name if session and session.course else "Independent Session"

        meta_data = [
            [Paragraph(f"<b>Session:</b> {session_title}", body_style), Paragraph(f"<b>Date:</b> {session_date}", body_style)],
            [Paragraph(f"<b>Course:</b> {course_name}", body_style), Paragraph(f"<b>Status:</b> {session.status.upper() if session else 'N/A'}", body_style)],
            [Paragraph(f"<b>Report Generated:</b> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}", body_style), Paragraph(f"<b>Duration:</b> {session.expected_duration_minutes if session else 60} mins", body_style)],
        ]
        meta_table = Table(meta_data, colWidths=[260, 260])
        meta_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("PADDING", (0, 0), (-1, -1), 6),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 14))

        # Attendance Section
        story.append(Paragraph("1. Attendance Summary", heading_style))
        present_cnt = sum(1 for r in records if r.attendance_status == "PRESENT")
        late_cnt = sum(1 for r in records if r.attendance_status == "LATE" or r.is_late)
        total_tracked = len(records)
        att_pct = round(((present_cnt + late_cnt) / max(1, total_tracked)) * 100, 1)

        summary_p = f"Total Attendees Tracked: <b>{total_tracked}</b> | Present: <b>{present_cnt}</b> | Late: <b>{late_cnt}</b> | Attendance Rate: <b>{att_pct}%</b> (Formula: <code>(Present + Late) / Total Tracked * 100</code>)"
        story.append(Paragraph(summary_p, body_style))
        story.append(Spacer(1, 6))

        # Attendance Table
        att_rows = [["Track ID", "Student Name", "Roll / ID", "Status", "Duration (s)", "Late?"]]
        for r in records[:15]:  # top 15 records in PDF
            att_rows.append([
                str(r.anonymous_track_id),
                r.student.name if r.student else f"Track #{r.anonymous_track_id}",
                r.student.student_id if r.student else "-",
                r.attendance_status,
                str(round(r.accumulated_duration, 1)),
                "YES" if r.is_late else "NO",
            ])
        if len(records) == 0:
            att_rows.append(["-", "No attendance records recorded", "-", "-", "-", "-"])

        att_table = Table(att_rows, colWidths=[55, 160, 95, 85, 75, 50])
        att_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f766e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("ALIGN", (1, 1), (1, -1), "LEFT"),
        ]))
        story.append(att_table)
        story.append(Spacer(1, 14))

        # Teaching Suggestions Section
        story.append(Paragraph("2. AI Pedagogical Suggestions & Evidence", heading_style))
        if suggestions:
            latest_sug = suggestions[-1]
            story.append(Paragraph(f"<b>Observed Pattern:</b> {latest_sug.pattern_summary}", body_style))
            story.append(Spacer(1, 4))
            for item in latest_sug.get_suggestions():
                story.append(Paragraph(f"• {item}", body_style))
            story.append(Spacer(1, 4))
            story.append(Paragraph(f"<b>Confidence:</b> {latest_sug.confidence_level} — <i>{latest_sug.confidence_explanation or ''}</i>", body_style))
        else:
            story.append(Paragraph("No automated teaching suggestions were generated for this session.", body_style))
        story.append(Spacer(1, 14))

        # Privacy and Methodological Disclaimer
        story.append(Paragraph("3. Methodological & Privacy Note", heading_style))
        disclaimer_text = (
            "NOTICE: This system runs offline. Observed indicators (head pose, movement, acoustic activity) "
            "measure physical environmental signals only. They must never be interpreted as definitive measures of "
            "student comprehension, attention, or academic ability. No raw recordings are uploaded to external cloud services."
        )
        story.append(Paragraph(disclaimer_text, disclaimer_style))

        doc.build(story)
        return filepath

report_service = ReportService()
