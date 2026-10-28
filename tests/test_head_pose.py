import pytest
from app.services.head_pose_service import HeadPoseService

def test_head_pose_forward_landmarks():
    service = HeadPoseService(forward_yaw_thresh=25.0, forward_pitch_thresh=20.0)
    
    # Perfectly symmetrical centered facial landmarks
    landmarks = {
        "nose": (320.0, 260.0),
        "chin": (320.0, 360.0),
        "left_eye": (270.0, 210.0),
        "right_eye": (370.0, 210.0),
        "left_mouth": (290.0, 310.0),
        "right_mouth": (350.0, 310.0),
    }

    pose = service.estimate_pose((480, 640), landmarks=landmarks)
    assert abs(pose["yaw"]) <= 25.0
    assert pose["is_forward"] is True
    assert pose["confidence"] > 0.5

def test_head_pose_turned_landmarks():
    service = HeadPoseService(forward_yaw_thresh=25.0, forward_pitch_thresh=20.0)
    
    # Head turned strongly to the side (nose shifted right past right eye)
    landmarks = {
        "nose": (380.0, 260.0),
        "chin": (360.0, 360.0),
        "left_eye": (270.0, 210.0),
        "right_eye": (350.0, 210.0),
        "left_mouth": (300.0, 310.0),
        "right_mouth": (360.0, 310.0),
    }

    pose = service.estimate_pose((480, 640), landmarks=landmarks)
    assert abs(pose["yaw"]) > 25.0
    assert pose["is_forward"] is False
