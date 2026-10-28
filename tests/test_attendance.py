import pytest
from app.services.attendance_service import TrackAttendanceState, AttendanceService
from app.models.attendance import AttendanceRecord
from app.models.student import Student
from app.extensions import db

def test_attendance_state_machine_transition():
    state = TrackAttendanceState(
        track_id=1,
        first_seen=0.0,
        sustained_required=5.0,
        min_coverage=0.60,
        grace_period=2.0,
        late_threshold_seconds=100.0,
    )
    assert state.status == "UNCONFIRMED"
    assert state.confirmed_at is None

    # Step through 4 seconds (accumulated = 4s < 5s required)
    for t in [1.0, 2.0, 3.0, 4.0]:
        state.update_presence(current_time=t, frame_delta=1.0)
        assert state.status == "UNCONFIRMED"

    # 5th second satisfies requirement
    status = state.update_presence(current_time=5.0, frame_delta=1.0)
    assert status == "PRESENT"
    assert state.confirmed_at == 5.0
    assert not state.is_late

def test_late_arrival_state():
    state = TrackAttendanceState(
        track_id=2,
        first_seen=120.0,
        sustained_required=3.0,
        min_coverage=0.60,
        grace_period=2.0,
        late_threshold_seconds=100.0,  # late if > 100s
    )
    state.update_presence(current_time=121.0, frame_delta=1.0)
    state.update_presence(current_time=122.0, frame_delta=1.0)
    status = state.update_presence(current_time=123.0, frame_delta=1.0)

    assert status == "LATE"
    assert state.is_late

def test_manual_override_audit(app, sample_session):
    with app.app_context():
        # Create an attendance record
        record = AttendanceRecord(
            session_id=sample_session,
            anonymous_track_id=99,
            attendance_status="UNCONFIRMED",
        )
        db.session.add(record)
        db.session.commit()
        rec_id = record.id

        service = AttendanceService()
        updated = service.manual_override(rec_id, "PRESENT", "Verified in person by instructor")
        assert updated is not None
        assert updated.attendance_status == "PRESENT"
        assert updated.verification_method == "MANUAL_INSTRUCTOR"
        assert "Verified in person" in updated.manual_correction_note

def test_attendance_percentage_calculation(app, sample_session):
    with app.app_context():
        # Add 3 students
        s1 = Student(student_id="ST1", name="Student 1")
        s2 = Student(student_id="ST2", name="Student 2")
        s3 = Student(student_id="ST3", name="Student 3")
        s4 = Student(student_id="ST4", name="Student 4")
        db.session.add_all([s1, s2, s3, s4])
        db.session.commit()

        # Add 2 present, 1 late, 1 absent record
        r1 = AttendanceRecord(session_id=sample_session, student_id=s1.id, anonymous_track_id=1, attendance_status="PRESENT")
        r2 = AttendanceRecord(session_id=sample_session, student_id=s2.id, anonymous_track_id=2, attendance_status="PRESENT")
        r3 = AttendanceRecord(session_id=sample_session, student_id=s3.id, anonymous_track_id=3, attendance_status="LATE", is_late=True)
        r4 = AttendanceRecord(session_id=sample_session, student_id=s4.id, anonymous_track_id=4, attendance_status="ABSENT")
        db.session.add_all([r1, r2, r3, r4])
        db.session.commit()

        stats = AttendanceService.calculate_session_attendance_stats(sample_session)
        # Total registered active students = 4 (+ baseline 5 seeded = 9, or check active query)
        total_reg = stats["total_registered"]
        # Present + Late = 3
        expected_pct = round((3 / float(total_reg)) * 100.0, 1)
        assert stats["present_count"] == 2
        assert stats["late_count"] == 1
        assert stats["absent_count"] == 1
        assert stats["attendance_percentage"] == expected_pct
