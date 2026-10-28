import math
from typing import List, Dict, Tuple, Optional

class MovementService:
    """Analyzes physical movement, micro-movements, inactivity, and visual data quality."""
    
    def __init__(self, movement_inactive_threshold: float = 6.0):
        # threshold in pixels/sec below which movement is classified as stationary
        self.movement_inactive_threshold = movement_inactive_threshold

    def calculate_window_metrics(
        self,
        history: List[Tuple[float, Tuple[float, float], List[int]]],
        window_start: float,
        window_end: float,
        expected_fps: float = 10.0,
    ) -> Dict:
        """
        Analyze a track's history inside [window_start, window_end].
        history item: (timestamp, (cx, cy), [x, y, w, h])
        """
        window_points = [
            pt for pt in history
            if window_start <= pt[0] <= window_end
        ]

        window_duration = max(0.001, window_end - window_start)
        
        # If no or too few points observed during window
        if len(window_points) < 2:
            return {
                "valid_duration": 0.0,
                "movement_score": 0.0,
                "movement_variability": 0.0,
                "inactivity_duration": 0.0,
                "visibility_ratio": 0.0,
                "confidence_score": 0.0,
                "quality_status": "INSUFFICIENT_DATA",
            }

        # Calculate frame-to-frame displacement
        displacements = []
        inactive_time = 0.0
        valid_duration = window_points[-1][0] - window_points[0][0]

        for i in range(1, len(window_points)):
            t_prev, c_prev, b_prev = window_points[i - 1]
            t_curr, c_curr, b_curr = window_points[i]
            
            dt = max(0.001, t_curr - t_prev)
            dist = math.sqrt((c_curr[0] - c_prev[0]) ** 2 + (c_curr[1] - c_prev[1]) ** 2)
            velocity = dist / dt  # pixels per second
            displacements.append(velocity)
            
            if velocity < self.movement_inactive_threshold:
                inactive_time += dt

        # Mean movement velocity
        mean_movement = sum(displacements) / len(displacements) if displacements else 0.0
        
        # Movement variability (standard deviation)
        if len(displacements) > 1:
            variance = sum((d - mean_movement) ** 2 for d in displacements) / (len(displacements) - 1)
            variability = math.sqrt(variance)
        else:
            variability = 0.0

        # Visibility ratio: observed frames / expected frames in window
        expected_frames = max(1.0, window_duration * expected_fps)
        visibility_ratio = min(1.0, len(window_points) / expected_frames)

        # Quality status assessment
        if visibility_ratio >= 0.70:
            quality_status = "NORMAL"
            confidence = 0.95
        elif visibility_ratio >= 0.35:
            quality_status = "OCCLUDED_OR_PARTIAL"
            confidence = 0.65
        else:
            quality_status = "POOR_VISIBILITY"
            confidence = 0.30

        return {
            "valid_duration": round(valid_duration, 2),
            "movement_score": round(mean_movement, 3),
            "movement_variability": round(variability, 3),
            "inactivity_duration": round(inactive_time, 2),
            "visibility_ratio": round(visibility_ratio, 3),
            "confidence_score": round(confidence, 3),
            "quality_status": quality_status,
        }

movement_service = MovementService()
