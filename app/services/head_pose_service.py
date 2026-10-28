import math
from typing import Dict, Tuple, Optional, List

try:
    import numpy as np
except ImportError:
    np = None

try:
    import cv2
except ImportError:
    cv2 = None

class HeadPoseService:
    """Estimates head pose orientation (yaw, pitch, roll) from facial landmarks or geometry."""
    
    # 3D generic facial landmark coordinates in mm
    MODEL_POINTS_6 = None
    if np is not None:
        MODEL_POINTS_6 = np.array([
            (0.0, 0.0, 0.0),          # Nose tip
            (0.0, -330.0, -65.0),     # Chin
            (-225.0, 170.0, -135.0),  # Left eye outer corner
            (225.0, 170.0, -135.0),   # Right eye outer corner
            (-150.0, -150.0, -125.0), # Left mouth corner
            (150.0, -150.0, -125.0)   # Right mouth corner
        ], dtype=np.float64)

    def __init__(self, forward_yaw_thresh: float = 25.0, forward_pitch_thresh: float = 20.0):
        self.forward_yaw_thresh = forward_yaw_thresh
        self.forward_pitch_thresh = forward_pitch_thresh

    def estimate_pose(
        self,
        image_shape: Tuple[int, int],
        landmarks: Optional[Dict[str, Tuple[float, float]]] = None,
        bbox: Optional[List[int]] = None,
    ) -> Dict:
        """
        Estimate yaw, pitch, roll in degrees and forward-facing indicator.
        landmarks dict keys: 'nose', 'chin', 'left_eye', 'right_eye', 'left_mouth', 'right_mouth'
        """
        height, width = image_shape[:2]
        
        # 1. Try OpenCV solvePnP if 6 keypoints and cv2 available
        if cv2 is not None and np is not None and landmarks and len(landmarks) >= 6:
            try:
                image_points = np.array([
                    landmarks["nose"],
                    landmarks["chin"],
                    landmarks["left_eye"],
                    landmarks["right_eye"],
                    landmarks["left_mouth"],
                    landmarks["right_mouth"]
                ], dtype=np.float64)

                focal_length = width
                center = (width / 2.0, height / 2.0)
                camera_matrix = np.array([
                    [focal_length, 0, center[0]],
                    [0, focal_length, center[1]],
                    [0, 0, 1]
                ], dtype=np.float64)
                dist_coeffs = np.zeros((4, 1))

                success, rvec, tvec = cv2.solvePnP(
                    self.MODEL_POINTS_6,
                    image_points,
                    camera_matrix,
                    dist_coeffs,
                    flags=cv2.SOLVEPNP_ITERATIVE
                )

                if success:
                    rmat, _ = cv2.Rodrigues(rvec)
                    # Extract Euler angles from rotation matrix
                    sy = math.sqrt(rmat[0, 0] ** 2 + rmat[1, 0] ** 2)
                    singular = sy < 1e-6
                    if not singular:
                        pitch = math.atan2(rmat[2, 1], rmat[2, 2])
                        yaw = math.atan2(-rmat[2, 0], sy)
                        roll = math.atan2(rmat[1, 0], rmat[0, 0])
                    else:
                        pitch = math.atan2(-rmat[1, 2], rmat[1, 1])
                        yaw = math.atan2(-rmat[2, 0], sy)
                        roll = 0

                    yaw_deg = float(math.degrees(yaw))
                    pitch_deg = float(math.degrees(pitch))
                    roll_deg = float(math.degrees(roll))

                    # Normalize angles to [-90, 90] facing camera coordinate system
                    if pitch_deg > 90.0:
                        pitch_deg = pitch_deg - 180.0
                    elif pitch_deg < -90.0:
                        pitch_deg = pitch_deg + 180.0

                    if abs(roll_deg) > 90.0:
                        roll_deg = roll_deg - 180.0 if roll_deg > 0 else roll_deg + 180.0

                    is_forward = (abs(yaw_deg) <= self.forward_yaw_thresh and abs(pitch_deg) <= self.forward_pitch_thresh)
                    return {
                        "yaw": yaw_deg,
                        "pitch": pitch_deg,
                        "roll": roll_deg,
                        "is_forward": is_forward,
                        "confidence": 0.90,
                        "method": "solvePnP",
                    }
            except Exception:
                pass

        # 2. Geometric fallback using 2D landmarks (eye-nose symmetry)
        if landmarks and "nose" in landmarks and "left_eye" in landmarks and "right_eye" in landmarks:
            le = landmarks["left_eye"]
            re = landmarks["right_eye"]
            nose = landmarks["nose"]

            eye_dist = math.sqrt((re[0] - le[0]) ** 2 + (re[1] - le[1]) ** 2)
            if eye_dist > 1.0:
                mid_x = (le[0] + re[0]) / 2.0
                nose_offset_x = nose[0] - mid_x
                # Approximate yaw from nose displacement relative to eye width
                yaw_deg = (nose_offset_x / (eye_dist * 0.5)) * 45.0
                yaw_deg = max(-90.0, min(90.0, yaw_deg))

                # Approximate roll from eye tilt angle
                dy = re[1] - le[1]
                dx = re[0] - le[0]
                roll_deg = math.degrees(math.atan2(dy, dx))

                # Approximate pitch from nose vertical position relative to eyes
                mid_y = (le[1] + re[1]) / 2.0
                nose_offset_y = nose[1] - mid_y
                pitch_deg = ((nose_offset_y / eye_dist) - 0.7) * 40.0
                pitch_deg = max(-60.0, min(60.0, pitch_deg))

                is_forward = (abs(yaw_deg) <= self.forward_yaw_thresh and abs(pitch_deg) <= self.forward_pitch_thresh)
                return {
                    "yaw": yaw_deg,
                    "pitch": pitch_deg,
                    "roll": roll_deg,
                    "is_forward": is_forward,
                    "confidence": 0.75,
                    "method": "landmark_geometry",
                }

        # 3. Bounding box heuristic fallback
        if bbox:
            w, h = bbox[2], bbox[3]
            aspect = w / max(1.0, float(h))
            # Standard face aspect ratio is approx 0.75 - 0.85
            yaw_est = (aspect - 0.80) * 50.0
            return {
                "yaw": float(yaw_est),
                "pitch": 0.0,
                "roll": 0.0,
                "is_forward": abs(yaw_est) <= self.forward_yaw_thresh,
                "confidence": 0.40,
                "method": "bbox_heuristic",
            }

        return {
            "yaw": 0.0,
            "pitch": 0.0,
            "roll": 0.0,
            "is_forward": True,
            "confidence": 0.20,
            "method": "default",
        }

head_pose_service = HeadPoseService()
