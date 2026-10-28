import threading
import time
from datetime import datetime, timezone
from typing import Dict, Optional
from flask import current_app
from app.extensions import db, socketio
from app.models.session import ClassSession
from app.models.analytics import EngagementWindow, AudioActivityWindow, FusionResult
from app.services.video_service import VideoIngestionService
from app.services.face_detection_service import FaceDetectionService
from app.services.tracking_service import Tracker
from app.services.attendance_service import AttendanceService, attendance_service
from app.services.head_pose_service import HeadPoseService, head_pose_service
from app.services.movement_service import MovementService, movement_service
from app.services.audio_service import AudioService, audio_service
from app.services.fusion_service import MultimodalFusionService, fusion_service
from app.services.suggestion_service import TeachingSuggestionAgent, suggestion_agent
from app.utils.security import log_audit_event

class SessionRunner(threading.Thread):
    """Background processing thread for an active classroom session."""

    def __init__(self, session_id: int, app):
        super().__init__()
        self.session_id = session_id
        self.app = app
        self.daemon = True
        self.stop_requested = threading.Event()
        self.pause_requested = threading.Event()

        # Component services
        self.video_service = VideoIngestionService()
        self.face_detector = FaceDetectionService()
        self.tracker = Tracker(timeout_seconds=25.0)
        self.last_fusion_time = 0.0
        self.fusion_interval = 15.0  # seconds

    def run(self):
        with self.app.app_context():
            session = db.session.get(ClassSession, self.session_id)
            if not session:
                return

            session.status = "running"
            session.start_time = datetime.now(timezone.utc)
            db.session.commit()
            log_audit_event("SESSION_START", "session", self.session_id, f"Session '{session.title}' started")

            # Open video source (webcam, uploaded video file, or synthetic)
            success = self.video_service.open_source(
                source_type=session.input_source_type,
                file_path=session.video_file_path,
            )

            # Load prerecorded audio file if present
            audio_data = None
            if session.audio_file_path:
                audio_data, _ = audio_service.decode_wav_file(session.audio_file_path)

            frame_interval = 1.0 / float(self.video_service.target_fps)
            session_start_ts = time.time()

            while not self.stop_requested.is_set():
                if self.pause_requested.is_set():
                    time.sleep(0.2)
                    continue

                loop_start = time.time()
                elapsed = loop_start - session_start_ts

                # 1. Read Video Frame
                has_frame, frame, _ = self.video_service.read_frame()
                if not has_frame or frame is None:
                    # Video stream disconnected or file finished
                    time.sleep(0.1)
                    continue

                # 2. Detect Faces
                detections = self.face_detector.detect_faces(frame)

                # 3. Track Faces across frames
                tracks = self.tracker.update(detections, elapsed)

                # 4. Head Pose & Movement Analysis for each active track
                for trk in tracks:
                    pose = head_pose_service.estimate_pose(
                        image_shape=(frame.shape[0], frame.shape[1]),
                        landmarks=trk.landmarks,
                        bbox=trk.bbox,
                    )
                    trk.yaw = pose["yaw"]
                    trk.pitch = pose["pitch"]
                    trk.roll = pose["roll"]
                    trk.is_facing_forward = pose["is_forward"]

                # 5. Sustained-Presence Attendance State Machine
                att_results = attendance_service.process_tracks(
                    session_id=self.session_id,
                    tracks=tracks,
                    current_time=elapsed,
                    frame_delta=frame_interval,
                    sustained_seconds=self.app.config.get("SUSTAINED_PRESENCE_SECONDS", 30.0),
                    min_coverage=self.app.config.get("MIN_OBSERVATION_COVERAGE", 0.60),
                    grace_period=self.app.config.get("GRACE_PERIOD_SECONDS", 10.0),
                    late_threshold_seconds=float(self.app.config.get("LATE_ARRIVAL_MINUTES", 10) * 60),
                )

                # 6. Periodic Window Fusion & Aggregation (every 15s)
                if (elapsed - self.last_fusion_time) >= self.fusion_interval:
                    window_start = self.last_fusion_time
                    window_end = elapsed
                    self.last_fusion_time = elapsed

                    # Aggregate visual metrics across tracks
                    if tracks:
                        mean_forward = sum(1.0 if t.is_facing_forward else 0.0 for t in tracks) / len(tracks)
                        mean_movement = sum(t.movement_score for t in tracks) / len(tracks)
                        mean_inactivity = sum(t.inactivity_duration for t in tracks) / len(tracks)
                        visual_window_data = {
                            "forward_facing_ratio": mean_forward,
                            "movement_score": mean_movement,
                            "inactivity_duration": mean_inactivity,
                            "visibility_ratio": 1.0,
                            "confidence_score": 0.90,
                            "quality_status": "NORMAL",
                        }
                    else:
                        visual_window_data = None

                    # Aggregate audio window metrics
                    if audio_data is not None and len(audio_data) > 0:
                        # Slice corresponding chunk
                        sr = 16000
                        idx_start = int(window_start * sr)
                        idx_end = int(window_end * sr)
                        chunk = audio_data[idx_start:idx_end] if idx_start < len(audio_data) else None
                        audio_window_data = audio_service.analyze_audio_segment(chunk, sr) if chunk is not None else None
                    else:
                        # Ambient live microphone or simulated baseline
                        audio_window_data = {
                            "speech_duration": 4.5,
                            "silence_duration": 10.5,
                            "speech_segments_count": 2,
                            "mean_energy": 0.045,
                            "peak_energy": 0.22,
                            "audio_quality_status": "NORMAL",
                            "confidence_score": 0.85,
                        }

                    # Multimodal Fusion
                    fused = fusion_service.fuse(
                        visual_data=visual_window_data,
                        audio_data=audio_window_data,
                        window_duration=self.fusion_interval,
                        custom_visual_weight=self.app.config.get("DEFAULT_VISUAL_WEIGHT", 0.70),
                        custom_audio_weight=self.app.config.get("DEFAULT_AUDIO_WEIGHT", 0.30),
                    )

                    # Persist Fusion Window to DB
                    try:
                        fr = FusionResult(
                            session_id=self.session_id,
                            window_start=window_start,
                            window_end=window_end,
                            visual_score=fused["visual_score"],
                            audio_score=fused["audio_score"],
                            fused_score=fused["fused_score"],
                            visual_weight=fused["visual_weight"],
                            audio_weight=fused["audio_weight"],
                            confidence=fused["confidence"],
                            status=fused["status"],
                        )
                        fr.set_explanation(fused["explanation"])
                        db.session.add(fr)

                        # Sync attendance updates to SQLite
                        attendance_service.sync_to_database(self.session_id, session.start_time)
                        db.session.commit()
                    except Exception:
                        db.session.rollback()

                # 7. Broadcast live telemetry to dashboard clients via WebSocket
                try:
                    att_stats = attendance_service.calculate_session_attendance_stats(self.session_id)
                    socketio.emit(
                        "session_update",
                        {
                            "session_id": self.session_id,
                            "elapsed_seconds": int(elapsed),
                            "active_tracks_count": len(tracks),
                            "attendance_stats": att_stats,
                            "tracks": [
                                {
                                    "track_id": t.track_id,
                                    "bbox": t.bbox,
                                    "is_forward": t.is_facing_forward,
                                    "yaw": round(t.yaw, 1),
                                    "pitch": round(t.pitch, 1),
                                    "movement": round(t.movement_score, 1),
                                }
                                for t in tracks
                            ],
                        },
                        namespace="/live",
                    )
                except Exception:
                    pass

                # Regulate processing FPS
                compute_time = time.time() - loop_start
                sleep_time = max(0.005, frame_interval - compute_time)
                time.sleep(sleep_time)

            # Cleanup upon stop
            self.video_service.stop()
            session = db.session.get(ClassSession, self.session_id)
            if session:
                session.status = "stopped"
                session.end_time = datetime.now(timezone.utc)
                attendance_service.sync_to_database(self.session_id, session.start_time)
                db.session.commit()
                log_audit_event("SESSION_STOP", "session", self.session_id, f"Session '{session.title}' stopped")


class SessionCoordinator:
    """Manages active session runner instances and lifecycle."""

    def __init__(self):
        self.runners: Dict[int, SessionRunner] = {}

    def start_session(self, session_id: int, app) -> bool:
        if session_id in self.runners and self.runners[session_id].is_alive():
            return True  # already running

        runner = SessionRunner(session_id, app)
        self.runners[session_id] = runner
        runner.start()
        return True

    def pause_session(self, session_id: int) -> bool:
        runner = self.runners.get(session_id)
        if runner and runner.is_alive():
            runner.pause_requested.set()
            runner.video_service.pause()
            with runner.app.app_context():
                sess = db.session.get(ClassSession, session_id)
                if sess:
                    sess.status = "paused"
                    db.session.commit()
            return True
        return False

    def resume_session(self, session_id: int) -> bool:
        runner = self.runners.get(session_id)
        if runner and runner.is_alive():
            runner.pause_requested.clear()
            runner.video_service.resume()
            with runner.app.app_context():
                sess = db.session.get(ClassSession, session_id)
                if sess:
                    sess.status = "running"
                    db.session.commit()
            return True
        return False

    def stop_session(self, session_id: int) -> bool:
        runner = self.runners.get(session_id)
        if runner:
            runner.stop_requested.set()
            runner.join(timeout=3.0)
            del self.runners[session_id]
            return True
        return False

    def finalize_session(self, session_id: int, app) -> Dict:
        """Finalize session, generate AI suggestions, and calculate final statistics."""
        with app.app_context():
            session = db.session.get(ClassSession, session_id)
            if not session:
                return {"error": "Session not found"}

            self.stop_session(session_id)
            session.status = "finalized"
            session.finalized_at = datetime.now(timezone.utc)
            if not session.end_time:
                session.end_time = session.finalized_at

            # Finalize attendance sync
            attendance_service.sync_to_database(session_id, session.start_time or session.created_at)
            att_stats = attendance_service.calculate_session_attendance_stats(session_id)

            # Retrieve fusion timeline
            fusions = [f.to_dict() for f in session.fusion_results.all()]
            duration_mins = (
                (session.end_time - (session.start_time or session.created_at)).total_seconds() / 60.0
                if session.end_time
                else session.expected_duration_minutes
            )

            # Generate teaching suggestions
            suggestions = suggestion_agent.generate_suggestions(
                session_id=session_id,
                session_duration_minutes=duration_mins,
                attendance_stats=att_stats,
                fusion_history=fusions,
                objectives=session.objectives,
            )
            suggestion_agent.save_suggestion_to_db(session_id, suggestions, duration_mins * 60.0)

            db.session.commit()
            log_audit_event("SESSION_FINALIZE", "session", session_id, f"Finalized session '{session.title}'")

            return {
                "session": session.to_dict(),
                "attendance_stats": att_stats,
                "suggestions": suggestions,
            }

session_coordinator = SessionCoordinator()
