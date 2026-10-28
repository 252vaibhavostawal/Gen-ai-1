import time
import pytest
from app.extensions import db
from app.models.session import ClassSession
from app.models.attendance import AttendanceRecord
from app.services.session_service import session_coordinator
from app.services.report_service import ReportService, report_service

def test_full_session_lifecycle(app, sample_course, tmp_path):
    with app.app_context():
        # 1. Create a session
        session = ClassSession(
            title="End-to-End Multimodal Integration Test",
            course_id=sample_course,
            expected_duration_minutes=30,
            input_source_type="synthetic",
            objectives="Verify end-to-end vision, audio, fusion, and suggestion pipeline.",
        )
        db.session.add(session)
        db.session.commit()
        session_id = session.id

        # 2. Start session runner
        started = session_coordinator.start_session(session_id, app)
        assert started is True
        assert session_id in session_coordinator.runners

        # Allow background processing thread to ingest synthetic frames and update tracks
        time.sleep(2.5)

        # 3. Pause and Resume
        paused = session_coordinator.pause_session(session_id)
        assert paused is True
        time.sleep(0.5)

        resumed = session_coordinator.resume_session(session_id)
        assert resumed is True
        time.sleep(1.0)

        # 4. Finalize Session (stops runner, calculates statistics, produces teaching suggestions)
        finalized = session_coordinator.finalize_session(session_id, app)
        assert "error" not in finalized
        assert finalized["session"]["status"] == "finalized"
        assert "suggestions" in finalized
        assert len(finalized["suggestions"]["actionable_suggestions"]) >= 1

        # 5. Export Reports
        csv_att = report_service.generate_session_attendance_csv(session_id)
        assert len(csv_att) > 50

        csv_eng = report_service.generate_engagement_timeline_csv(session_id)
        assert "Engagement Timeline" in csv_eng

        rep_service = ReportService(reports_dir=str(tmp_path))
        pdf_path = rep_service.generate_session_pdf_report(session_id)
        assert pdf_path.endswith(".pdf")
