import pytest
from app.services.tracking_service import Tracker, Track

def test_track_initialization():
    t = Track(track_id=1, bbox=[100, 100, 50, 50], timestamp=0.0)
    assert t.track_id == 1
    assert t.centroid == (125.0, 125.0)
    assert t.hits == 1
    assert t.misses == 0
    assert len(t.history) == 1

def test_track_update_movement():
    t = Track(track_id=1, bbox=[100, 100, 50, 50], timestamp=0.0)
    # Move centroid by 30 pixels over 1.0 second
    t.update(bbox=[130, 100, 50, 50], timestamp=1.0)
    assert t.centroid == (155.0, 125.0)
    assert t.hits == 2
    assert t.movement_score > 0.0

def test_tracker_association():
    tracker = Tracker(max_distance=100.0, min_iou=0.2, timeout_seconds=10.0)
    
    # Frame 0: Detect two faces
    detections_f0 = [
        {"bbox": [50, 50, 60, 60], "confidence": 0.9},
        {"bbox": [200, 200, 60, 60], "confidence": 0.95},
    ]
    tracks = tracker.update(detections_f0, current_timestamp=0.0)
    assert len(tracks) == 2
    t1_id = tracks[0].track_id
    t2_id = tracks[1].track_id
    assert t1_id != t2_id

    # Frame 1: Slight movement
    detections_f1 = [
        {"bbox": [52, 51, 60, 60], "confidence": 0.9},
        {"bbox": [202, 198, 60, 60], "confidence": 0.95},
    ]
    tracks_f1 = tracker.update(detections_f1, current_timestamp=0.1)
    assert len(tracks_f1) == 2
    # Ensure IDs remained stable (no ID switches)
    current_ids = {t.track_id for t in tracks_f1}
    assert t1_id in current_ids
    assert t2_id in current_ids

def test_tracker_timeout_expiration():
    tracker = Tracker(max_distance=100.0, min_iou=0.2, timeout_seconds=5.0)
    detections = [{"bbox": [50, 50, 60, 60], "confidence": 0.9}]
    tracker.update(detections, current_timestamp=0.0)
    assert len(tracker.tracks) == 1

    # Frame after timeout with no detections
    tracker.update([], current_timestamp=6.0)
    assert len(tracker.tracks) == 0
