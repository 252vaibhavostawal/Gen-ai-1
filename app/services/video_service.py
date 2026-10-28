import os
import time
import math
from typing import Optional, Generator, Tuple

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import numpy as np
except ImportError:
    np = None

class VideoIngestionService:
    """Manages video capture from webcams, prerecorded video files, and synthetic test generators."""

    def __init__(self, target_width: int = 640, target_height: int = 480, target_fps: int = 10):
        self.target_width = target_width
        self.target_height = target_height
        self.target_fps = target_fps
        self.cap = None
        self.is_active = False
        self.is_paused = False
        self.source_type = "webcam"
        self.source_path = None
        self.frame_count = 0
        self.start_time = 0.0

    def open_source(self, source_type: str = "webcam", file_path: Optional[str] = None) -> bool:
        """Initialize video capture stream."""
        self.stop()
        self.source_type = source_type
        self.source_path = file_path
        self.frame_count = 0
        self.start_time = time.time()
        self.is_paused = False

        if source_type == "video_file" and file_path:
            if not os.path.exists(file_path):
                return False
            if cv2 is not None:
                self.cap = cv2.VideoCapture(file_path)
                if not self.cap.isOpened():
                    self.cap = None
                    return False
                self.is_active = True
                return True

        elif source_type == "webcam":
            if cv2 is not None:
                # Try default camera index 0
                self.cap = cv2.VideoCapture(0)
                if self.cap.isOpened():
                    self.is_active = True
                    return True
                # If physical webcam cannot be opened, fallback to synthetic
                self.cap = None

        # Fallback to synthetic stream (e.g. headless server, unit tests, or missing camera)
        self.source_type = "synthetic"
        self.is_active = True
        return True

    def read_frame(self) -> Tuple[bool, Optional["np.ndarray"], float]:
        """
        Read the next processed frame.
        Returns: (success, frame_bgr, elapsed_seconds)
        """
        if not self.is_active:
            return False, None, 0.0

        if self.is_paused:
            time.sleep(1.0 / self.target_fps)
            return True, None, time.time() - self.start_time

        elapsed = time.time() - self.start_time

        # Read from hardware camera or video file if opened
        if self.cap is not None and cv2 is not None:
            ret, frame = self.cap.read()
            if not ret:
                # Video file reached end or camera disconnected
                if self.source_type == "video_file":
                    # Loop video or signal end
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = self.cap.read()
                    if not ret:
                        return False, None, elapsed
                else:
                    return False, None, elapsed

            # Resize for optimal processing performance
            frame = cv2.resize(frame, (self.target_width, self.target_height))
            self.frame_count += 1
            return True, frame, elapsed

        # Synthetic generator fallback (drawing simulated students in a classroom)
        self.frame_count += 1
        frame = self._generate_synthetic_frame(elapsed)
        time.sleep(1.0 / self.target_fps)
        return True, frame, elapsed

    def _generate_synthetic_frame(self, elapsed: float) -> Optional["np.ndarray"]:
        """Generate a realistic test frame with mock attendees for offline testing and demos."""
        if np is None:
            return None

        # Clean background (classroom wall/board)
        frame = np.full((self.target_height, self.target_width, 3), (240, 240, 242), dtype=np.uint8)

        if cv2 is not None:
            # Draw instructor board
            cv2.rectangle(frame, (40, 20), (self.target_width - 40, 100), (45, 60, 50), -1)
            cv2.putText(
                frame,
                "Offline Multimodal Classroom Monitor",
                (60, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
            )
            
            # Draw synthetic attendees (two seats)
            # Student 1 (centered left)
            s1_x = 160 + int(math.sin(elapsed * 1.5) * 8)
            s1_y = 260
            cv2.circle(frame, (s1_x, s1_y), 45, (210, 180, 140), -1)  # Head
            cv2.ellipse(frame, (s1_x, s1_y + 110), (70, 70), 0, 0, 180, (70, 130, 180), -1)  # Torso
            cv2.circle(frame, (s1_x - 15, s1_y - 8), 5, (50, 50, 50), -1)  # Left eye
            cv2.circle(frame, (s1_x + 15, s1_y - 8), 5, (50, 50, 50), -1)  # Right eye

            # Student 2 (centered right, arrives or stays)
            s2_x = 440 + int(math.cos(elapsed * 1.2) * 5)
            s2_y = 270
            cv2.circle(frame, (s2_x, s2_y), 45, (190, 160, 130), -1)
            cv2.ellipse(frame, (s2_x, s2_y + 110), (70, 70), 0, 0, 180, (60, 179, 113), -1)
            cv2.circle(frame, (s2_x - 15, s2_y - 8), 5, (50, 50, 50), -1)
            cv2.circle(frame, (s2_x + 15, s2_y - 8), 5, (50, 50, 50), -1)

            # Draw timestamp badge
            timestamp_str = f"T+{int(elapsed)}s | Frame #{self.frame_count}"
            cv2.putText(frame, timestamp_str, (self.target_width - 220, self.target_height - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (80, 80, 80), 1)

        return frame

    def encode_jpeg(self, frame: "np.ndarray") -> Optional[bytes]:
        """Convert BGR numpy image frame to JPEG byte buffer."""
        if cv2 is None or frame is None:
            return None
        ret, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        return buf.tobytes() if ret else None

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

    def stop(self):
        self.is_active = False
        self.is_paused = False
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None

video_service = VideoIngestionService()
