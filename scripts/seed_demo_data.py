#!/usr/bin/env python
"""
Seed script to populate rich demonstration data for instructors and evaluators.
Creates sample courses, students, completed sessions, fusion analytics, and reports.
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from app.extensions import db
from app.models.course import Course
from app.models.student import Student
from app.models.session import ClassSession
from app.models.attendance import AttendanceRecord
from app.models.analytics import FusionResult
from app.models.suggestion import TeachingSuggestion
from app.services.suggestion_service import suggestion_agent
from app.services.report_service import report_service

def seed_demo_data():
    app = create_app("development")
    with app.app_context():
        print("Seeding demonstration data...")

        # 1. Course
        course = Course.query.filter_by(code="CS501").first()
        if not course:
            course = Course(
                code="CS501",
                name="Multimodal AI & Real-Time Computer Vision",
                department="Computer Science",
                semester="Fall 2026",
                description="Advanced engineering of offline-first perceptual AI systems.",
            )
            db.session.add(course)
            db.session.commit()

        # 2. Students
        students_data = [
            ("STU101", "Maya Lin", "maya@example.edu", "AI-Batch-A"),
            ("STU102", "Ethan Wright", "ethan@example.edu", "AI-Batch-A"),
            ("STU103", "Priya Sharma", "priya@example.edu", "AI-Batch-A"),
            ("STU104", "Lucas Vance", "lucas@example.edu", "AI-Batch-A"),
            ("STU105", "Chloe Bennett", "chloe@example.edu", "AI-Batch-A"),
        ]

        created_students = []
        for sid, name, email, batch in students_data:
            st = Student.query.filter_by(student_id=sid).first()
            if not st:
                st = Student(student_id=sid, name=name, email=email, batch=batch, consent_given=True)
                db.session.add(st)
                db.session.commit()
            created_students.append(st)

        # 3. Completed Class Session
        session_title = "Demo Session: Real-Time Multimodal Telemetry"
        sess = ClassSession.query.filter_by(title=session_title).first()
        if not sess:
            now = datetime.now(timezone.utc)
            start_dt = now - timedelta(minutes=45)
            end_dt = now - timedelta(minutes=5)

            sess = ClassSession(
                title=session_title,
                course_id=course.id,
                date=start_dt.date(),
                start_time=start_dt,
                end_time=end_dt,
                expected_duration_minutes=40,
                input_source_type="synthetic",
                status="finalized",
                objectives="Demonstrate sustained presence attendance state machines and multimodal fusion.",
                finalized_at=end_dt,
            )
            db.session.add(sess)
            db.session.commit()

            # 4. Attendance Records
            # 3 Present, 1 Late, 1 Unconfirmed
            att_records = [
                AttendanceRecord(
                    session_id=sess.id,
                    student_id=created_students[0].id,
                    anonymous_track_id=1,
                    first_observed_at=start_dt + timedelta(seconds=10),
                    confirmed_at=start_dt + timedelta(seconds=45),
                    last_observed_at=end_dt,
                    accumulated_duration=2300.0,
                    attendance_status="PRESENT",
                    is_late=False,
                    verification_method="AUTOMATIC_SUSTAINED",
                ),
                AttendanceRecord(
                    session_id=sess.id,
                    student_id=created_students[1].id,
                    anonymous_track_id=2,
                    first_observed_at=start_dt + timedelta(seconds=15),
                    confirmed_at=start_dt + timedelta(seconds=50),
                    last_observed_at=end_dt,
                    accumulated_duration=2250.0,
                    attendance_status="PRESENT",
                    is_late=False,
                    verification_method="AUTOMATIC_SUSTAINED",
                ),
                AttendanceRecord(
                    session_id=sess.id,
                    student_id=created_students[2].id,
                    anonymous_track_id=3,
                    first_observed_at=start_dt + timedelta(minutes=14),
                    confirmed_at=start_dt + timedelta(minutes=15),
                    last_observed_at=end_dt,
                    accumulated_duration=1500.0,
                    attendance_status="LATE",
                    is_late=True,
                    verification_method="AUTOMATIC_SUSTAINED",
                    manual_correction_note="Arrived 14 mins into lecture",
                ),
                AttendanceRecord(
                    session_id=sess.id,
                    student_id=None,
                    anonymous_track_id=4,
                    first_observed_at=start_dt + timedelta(minutes=5),
                    confirmed_at=None,
                    last_observed_at=start_dt + timedelta(minutes=5, seconds=20),
                    accumulated_duration=18.0,
                    attendance_status="UNCONFIRMED",
                    is_late=False,
                    verification_method="ANONYMOUS_TRACK",
                ),
            ]
            db.session.add_all(att_records)

            # 5. Fusion Timeline (12 fifteen-second intervals)
            fusions = []
            for i in range(12):
                w_start = i * 15.0
                w_end = (i + 1) * 15.0
                # First half high interaction, second half lecture focus
                if i < 6:
                    v_score = 75.0 + (i % 3) * 4.0
                    a_score = 65.0 + (i % 2) * 10.0
                else:
                    v_score = 60.0 - (i % 2) * 5.0
                    a_score = 30.0 + (i % 2) * 8.0

                fused = round(v_score * 0.70 + a_score * 0.30, 2)
                fr = FusionResult(
                    session_id=sess.id,
                    window_start=w_start,
                    window_end=w_end,
                    visual_score=v_score,
                    audio_score=a_score,
                    fused_score=fused,
                    visual_weight=0.70,
                    audio_weight=0.30,
                    confidence=0.92,
                    status="CONFIDENT",
                )
                fr.set_explanation({
                    "visual_pts": v_score,
                    "audio_pts": a_score,
                    "note": f"Interval #{i+1} telemetry",
                })
                fusions.append(fr)
            db.session.add_all(fusions)

            # 6. Teaching Suggestions
            db.session.commit()
            f_history = [f.to_dict() for f in fusions]
            att_stats = {
                "total_registered": 5,
                "total_tracked": 4,
                "present_count": 2,
                "late_count": 1,
                "attendance_percentage": 60.0,
            }
            sug_res = suggestion_agent.generate_suggestions(
                session_id=sess.id,
                session_duration_minutes=40.0,
                attendance_stats=att_stats,
                fusion_history=f_history,
                objectives="Introduce real-time multimodal fusion.",
            )
            suggestion_agent.save_suggestion_to_db(sess.id, sug_res, 2400.0)

            # 7. Pre-generate printable PDF report
            pdf_path = report_service.generate_session_pdf_report(sess.id)
            print(f"Generated sample PDF report: {pdf_path}")

        print("Demonstration data seeded successfully!")

if __name__ == "__main__":
    seed_demo_data()
