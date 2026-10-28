import math
from typing import List, Dict, Tuple, Optional

class Track:
    """Represents a single tracked individual across video frames."""
    def __init__(self, track_id: int, bbox: List[int], timestamp: float, confidence: float = 1.0, landmarks: Optional[Dict] = None):
        self.track_id = track_id
        self.bbox = list(bbox)  # [x, y, w, h]
        self.centroid = (bbox[0] + bbox[2] / 2.0, bbox[1] + bbox[3] / 2.0)
        self.first_seen = timestamp
        self.last_seen = timestamp
        self.confidence = confidence
        self.landmarks = landmarks or {}
        
        # Continuity and motion metrics
        self.hits = 1
        self.misses = 0
        self.total_detected_frames = 1
        self.history = [(timestamp, self.centroid, self.bbox)]
        
        # Pose and movement metrics cache
        self.yaw = 0.0
        self.pitch = 0.0
        self.roll = 0.0
        self.is_facing_forward = True
        self.movement_score = 0.0
        self.inactivity_duration = 0.0
        self.last_movement_time = timestamp

    def update(self, bbox: List[int], timestamp: float, confidence: float = 1.0, landmarks: Optional[Dict] = None):
        prev_centroid = self.centroid
        self.bbox = list(bbox)
        self.centroid = (bbox[0] + bbox[2] / 2.0, bbox[1] + bbox[3] / 2.0)
        
        dt = max(0.001, timestamp - self.last_seen)
        dist = math.sqrt((self.centroid[0] - prev_centroid[0]) ** 2 + (self.centroid[1] - prev_centroid[1]) ** 2)
        instant_movement = dist / dt  # pixels / second
        
        # Exponential smoothing for movement
        self.movement_score = 0.7 * self.movement_score + 0.3 * instant_movement
        
        # Inactivity tracking: movement threshold of ~8 pixels/sec
        if instant_movement > 8.0:
            self.last_movement_time = timestamp
            self.inactivity_duration = 0.0
        else:
            self.inactivity_duration = timestamp - self.last_movement_time

        self.last_seen = timestamp
        self.confidence = confidence
        if landmarks:
            self.landmarks = landmarks
            
        self.hits += 1
        self.misses = 0
        self.total_detected_frames += 1
        self.history.append((timestamp, self.centroid, self.bbox))
        if len(self.history) > 60:
            self.history.pop(0)

    def mark_missed(self, timestamp: float):
        self.misses += 1


class Tracker:
    """Session-scoped Multi-Object Tracker using IoU and Centroid distance."""
    def __init__(self, max_distance: float = 85.0, min_iou: float = 0.25, timeout_seconds: float = 25.0):
        self.next_track_id = 1
        self.tracks: Dict[int, Track] = {}
        self.max_distance = max_distance
        self.min_iou = min_iou
        self.timeout_seconds = timeout_seconds

    def _compute_iou(self, boxA: List[int], boxB: List[int]) -> float:
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[0] + boxA[2], boxB[0] + boxB[2])
        yB = min(boxA[1] + boxA[3], boxB[1] + boxB[3])

        inter_width = max(0, xB - xA)
        inter_height = max(0, yB - yA)
        inter_area = inter_width * inter_height

        boxAArea = boxA[2] * boxA[3]
        boxBArea = boxB[2] * boxB[3]
        union_area = float(boxAArea + boxBArea - inter_area)
        if union_area <= 0:
            return 0.0
        return inter_area / union_area

    def _compute_distance(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)

    def update(self, detections: List[Dict], current_timestamp: float) -> List[Track]:
        """
        Update tracker with new detections in the current frame.
        detections format: [{'bbox': [x, y, w, h], 'confidence': 0.95, 'landmarks': {...}}, ...]
        """
        # If no active tracks, register all detections
        if not self.tracks:
            for det in detections:
                t = Track(
                    track_id=self.next_track_id,
                    bbox=det["bbox"],
                    timestamp=current_timestamp,
                    confidence=det.get("confidence", 1.0),
                    landmarks=det.get("landmarks"),
                )
                self.tracks[self.next_track_id] = t
                self.next_track_id += 1
            return list(self.tracks.values())

        track_ids = list(self.tracks.keys())
        active_tracks = [self.tracks[tid] for tid in track_ids]

        # Compute cost / affinity matrix using IoU + Centroid distance
        matches = []
        unmatched_detections = set(range(len(detections)))
        unmatched_tracks = set(track_ids)

        # Greedily match by highest IoU or closest centroid
        candidates = []
        for d_idx, det in enumerate(detections):
            det_box = det["bbox"]
            det_centroid = (det_box[0] + det_box[2] / 2.0, det_box[1] + det_box[3] / 2.0)
            for tid in track_ids:
                trk = self.tracks[tid]
                iou = self._compute_iou(trk.bbox, det_box)
                dist = self._compute_distance(trk.centroid, det_centroid)
                candidates.append((iou, -dist, d_idx, tid))

        # Sort candidates by highest IoU, then smallest distance
        candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)

        for iou, neg_dist, d_idx, tid in candidates:
            dist = -neg_dist
            if d_idx in unmatched_detections and tid in unmatched_tracks:
                # Accept match if IoU is above min threshold or distance is within bounds
                if iou >= self.min_iou or dist <= self.max_distance:
                    matches.append((tid, d_idx))
                    unmatched_detections.remove(d_idx)
                    unmatched_tracks.remove(tid)

        # Update matched tracks
        for tid, d_idx in matches:
            det = detections[d_idx]
            self.tracks[tid].update(
                bbox=det["bbox"],
                timestamp=current_timestamp,
                confidence=det.get("confidence", 1.0),
                landmarks=det.get("landmarks"),
            )

        # Handle unmatched existing tracks
        for tid in unmatched_tracks:
            self.tracks[tid].mark_missed(current_timestamp)

        # Register new tracks for unmatched detections
        for d_idx in unmatched_detections:
            det = detections[d_idx]
            t = Track(
                track_id=self.next_track_id,
                bbox=det["bbox"],
                timestamp=current_timestamp,
                confidence=det.get("confidence", 1.0),
                landmarks=det.get("landmarks"),
            )
            self.tracks[self.next_track_id] = t
            self.next_track_id += 1

        # Expire tracks that exceeded timeout
        expired_ids = [
            tid for tid, trk in self.tracks.items()
            if (current_timestamp - trk.last_seen) > self.timeout_seconds
        ]
        for tid in expired_ids:
            del self.tracks[tid]

        return list(self.tracks.values())
