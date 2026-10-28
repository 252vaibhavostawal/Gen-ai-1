import os
import pytest
from app.services.report_service import ReportService
from app.models.attendance import AttendanceRecord
from app.models.analytics import FusionResult
from app.models.suggestion import TeachingSuggestion
from app.extensions import db

def test_attendance_csv_export(app, sample_session):
    with app.app_context():
        record = AttendanceRecord(
            session_id=sample_session,
            anonymous_track_id=10,
            attendance_status="PRESENT",
            accumulated_duration=45.2,
        )
        db.session.add(record)
        db.session.commit()

        service = ReportService()
        csv_out = service.generate_session_attendance_csv(sample_session)
        assert "Multimodal Attendance & Engagement Agent" in csv_out
        assert "Track ID" in csv_out
        assert "PRESENT" in csv_out
        assert "10" in csv_out

def test_engagement_csv_export(app, sample_session):
    with app.app_context():
        fr = FusionResult(
            session_id=sample_session,
            window_start=0.0,
            window_end=15.0,
            visual_score=75.0,
            audio_score=60.0,
            fused_score=70.5,
            visual_weight=0.7,
            audio_weight=0.3,
            confidence=0.9,
            status="CONFIDENT",
        )
        db.session.add(fr)
        db.session.commit()

        service = ReportService()
        csv_out = service.generate_engagement_timeline_csv(sample_session)
        assert "Engagement Timeline" in csv_out
        assert "70.5" in csv_out
        assert "CONFIDENT" in csv_out

def test_pdf_report_generation(app, sample_session, tmp_path):
    with app.app_context():
        record = AttendanceRecord(
            session_id=sample_session,
            anonymous_track_id=12,
            attendance_status="PRESENT",
            accumulated_duration=120.0,
        )
        sug = TeachingSuggestion(
            session_id=sample_session,
            timestamp=60.0,
            pattern_summary="Active participation throughout.",
            actionable_suggestions_json='["Continue formative checks."]',
            evidence_json='{"trend_delta": 2.5}',
            confidence_level="HIGH",
        )
        db.session.add_all([record, sug])
        db.session.commit()

        service = ReportService(reports_dir=str(tmp_path))
        pdf_file = service.generate_session_pdf_report(sample_session)
        assert os.path.exists(pdf_file)
        assert os.path.getsize(pdf_file) > 1000  # PDF generated with content
