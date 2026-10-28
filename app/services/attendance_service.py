from datetime import datetime, timezone
from typing import Dict, Optional, List, Tuple
from app.extensions import db
from app.models.attendance import AttendanceRecord
from app.models.session import ClassSession
from app.models.student import Student
from app.models.audit import AuditLog
from app.utils.security import log_audit_event

class TrackAttendanceState:
    """In-memory state machine tracker for an anonymous track in an active session."""
    def __init__(
        self,
        track_id: int,
        first_seen: float,
        sustained_required: float = 30.0,
        min_coverage: float = 0.60,
        grace_period: float = 10.0,
        late_threshold_seconds: float = 600.0,
    ):
        self.track_id = track_id
        self.first_seen = first_seen
        self.last_seen = first_seen
        self.accumulated_duration = 0.0
        self.status = "UNCONFIRMED"
        self.is_late = False
        self.confirmed_at: Optional[float] = None
        self.last_frame_time = first_seen
        
        # Configuration
        self.sustained_required = sustained_required
        self.min_coverage = min_coverage
        self.grace_period = grace_period
        self.late_threshold_seconds = late_threshold_seconds
        
        # Associated student ID once mapped by instructor
        self.student_id: Optional[int] = None
        self.verification_method = "AUTOMATIC_SUSTAINED"
        self.manual_override = False

    def update_presence(self, current_time: float, frame_delta: float = 0.1) -> str:
        """
        Feed observation at current_time.
        Returns the current attendance status.
        """
        if self.manual_override:
            return self.status

        # Accumulate observed duration
        self.accumulated_duration += frame_delta
        self.last_seen = current_time

        # Check sustained presence rule if unconfirmed
        if self.status == "UNCONFIRMED":
            span = max(0.001, current_time - self.first_seen)
            coverage = self.accumulated_duration / span
            
            if self.accumulated_duration >= self.sustained_required and coverage >= self.min_coverage:
                self.confirmed_at = current_time
                if current_time >= self.late_threshold_seconds:
                    self.status = "LATE"
                    self.is_late = True
                else:
                    self.status = "PRESENT"
                    self.is_late = False

        return self.status

    def check_absence_timeout(self, current_time: float, timeout_seconds: float = 30.0) -> bool:
        """Check if track has been inactive beyond timeout."""
        return (current_time - self.last_seen) > timeout_seconds


class AttendanceService:
    """Manages attendance state machines, database persistence, and instructor corrections."""
    
    def __init__(self):
        # session_id -> {track_id: TrackAttendanceState}
        self.active_session_states: Dict[int, Dict[int, TrackAttendanceState]] = {}

    def get_or_create_session_states(self, session_id: int) -> Dict[int, TrackAttendanceState]:
        if session_id not in self.active_session_states:
            self.active_session_states[session_id] = {}
        return self.active_session_states[session_id]

    def process_tracks(
        self,
        session_id: int,
        tracks: List,
        current_time: float,
        frame_delta: float,
        sustained_seconds: float = 30.0,
        min_coverage: float = 0.60,
        grace_period: float = 10.0,
        late_threshold_seconds: float = 600.0,
    ) -> List[Dict]:
        """Update attendance state machines with current frame tracks."""
        states = self.get_or_create_session_states(session_id)
        current_track_ids = set()

        results = []
        for trk in tracks:
            tid = trk.track_id
            current_track_ids.add(tid)
            if tid not in states:
                states[tid] = TrackAttendanceState(
                    track_id=tid,
                    first_seen=current_time,
                    sustained_required=sustained_seconds,
                    min_coverage=min_coverage,
                    grace_period=grace_period,
                    late_threshold_seconds=late_threshold_seconds,
                )
            
            state = states[tid]
            new_status = state.update_presence(current_time, frame_delta=frame_delta)
            
            results.append({
                "track_id": tid,
                "status": new_status,
                "is_late": state.is_late,
                "accumulated_duration": round(state.accumulated_duration, 2),
                "first_seen": round(state.first_seen, 2),
                "last_seen": round(state.last_seen, 2),
                "confirmed_at": round(state.confirmed_at, 2) if state.confirmed_at else None,
            })

        return results

    def sync_to_database(self, session_id: int, session_start_dt: datetime) -> None:
        """Persist or update attendance records in SQLite database."""
        states = self.active_session_states.get(session_id, {})
        for tid, state in states.items():
            record = AttendanceRecord.query.filter_by(
                session_id=session_id,
                anonymous_track_id=tid,
            ).first()

            now_utc = datetime.now(timezone.utc)
            first_dt = datetime.fromtimestamp(session_start_dt.timestamp() + state.first_seen, tz=timezone.utc)
            last_dt = datetime.fromtimestamp(session_start_dt.timestamp() + state.last_seen, tz=timezone.utc)
            conf_dt = (
                datetime.fromtimestamp(session_start_dt.timestamp() + state.confirmed_at, tz=timezone.utc)
                if state.confirmed_at
                else None
            )

            if not record:
                record = AttendanceRecord(
                    session_id=session_id,
                    student_id=state.student_id,
                    anonymous_track_id=tid,
                    first_observed_at=first_dt,
                    confirmed_at=conf_dt,
                    last_observed_at=last_dt,
                    accumulated_duration=state.accumulated_duration,
                    attendance_status=state.status,
                    is_late=state.is_late,
                    verification_method=state.verification_method,
                )
                db.session.add(record)
            else:
                record.last_observed_at = last_dt
                record.accumulated_duration = state.accumulated_duration
                if not record.manual_correction_note:
                    record.attendance_status = state.status
                    record.is_late = state.is_late
                    record.confirmed_at = conf_dt
                if state.student_id:
                    record.student_id = state.student_id

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()

    def map_track_to_student(self, session_id: int, track_id: int, student_id: int, instructor_note: Optional[str] = None) -> bool:
        """Map an anonymous track to a verified student record with consent verification."""
        states = self.active_session_states.get(session_id, {})
        if track_id in states:
            states[track_id].student_id = student_id
            states[track_id].verification_method = "MANUAL_INSTRUCTOR"

        record = AttendanceRecord.query.filter_by(session_id=session_id, anonymous_track_id=track_id).first()
        if record:
            record.student_id = student_id
            record.verification_method = "MANUAL_INSTRUCTOR"
            if instructor_note:
                record.manual_correction_note = (record.manual_correction_note or "") + f" | Mapped: {instructor_note}"
            db.session.commit()
            log_audit_event("MAP_STUDENT", "attendance", record.id, f"Mapped track #{track_id} to student #{student_id}")
            return True
        return False

    def manual_override(self, record_id: int, new_status: str, note: str) -> Optional[AttendanceRecord]:
        """Allow instructor to manually correct or override attendance with full audit trail."""
        record = db.session.get(AttendanceRecord, record_id)
        if not record:
            return None

        old_status = record.attendance_status
        record.attendance_status = new_status
        record.is_late = (new_status == "LATE")
        record.verification_method = "MANUAL_INSTRUCTOR"
        record.manual_correction_note = note
        record.updated_at = datetime.now(timezone.utc)

        # Update in-memory state if active
        states = self.active_session_states.get(record.session_id, {})
        if record.anonymous_track_id in states:
            states[record.anonymous_track_id].status = new_status
            states[record.anonymous_track_id].is_late = record.is_late
            states[record.anonymous_track_id].manual_override = True

        db.session.commit()
        log_audit_event(
            "ATTENDANCE_OVERRIDE",
            "attendance",
            record.id,
            f"Overrode status from {old_status} to {new_status}. Reason: {note}",
        )
        return record

    @staticmethod
    def calculate_session_attendance_stats(session_id: int) -> Dict:
        """
        Calculate attendance breakdown and percentage with explicit formula:
        Attendance % = (Present + Late) / Total Enrolled (or Total Tracked if no roster) * 100
        """
        records = AttendanceRecord.query.filter_by(session_id=session_id).all()
        present_count = sum(1 for r in records if r.attendance_status == "PRESENT")
        late_count = sum(1 for r in records if r.attendance_status == "LATE" or r.is_late)
        unconfirmed_count = sum(1 for r in records if r.attendance_status == "UNCONFIRMED")
        absent_count = sum(1 for r in records if r.attendance_status == "ABSENT")
        total_tracked = len(records)
        
        # Check registered students in course or active roster
        sess = db.session.get(ClassSession, session_id)
        total_registered = Student.query.filter_by(enrollment_status="active").count()
        denominator = total_registered if total_registered > 0 else total_tracked
        
        att_pct = round(((present_count + late_count) / denominator * 100.0), 1) if denominator > 0 else 0.0

        return {
            "total_registered": total_registered,
            "total_tracked": total_tracked,
            "present_count": present_count,
            "late_count": late_count,
            "absent_count": absent_count,
            "unconfirmed_count": unconfirmed_count,
            "attendance_percentage": att_pct,
            "calculation_formula": "((Present + Late) / Total Registered) * 100" if total_registered > 0 else "((Present + Late) / Total Tracked) * 100",
        }

attendance_service = AttendanceService()
