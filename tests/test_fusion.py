import pytest
from app.services.fusion_service import MultimodalFusionService

def test_multimodal_fusion_both_modalities():
    fusion = MultimodalFusionService(default_visual_weight=0.70, default_audio_weight=0.30)
    
    visual_data = {
        "forward_facing_ratio": 0.85,
        "movement_score": 15.0,
        "inactivity_duration": 0.0,
        "visibility_ratio": 1.0,
        "confidence_score": 0.95,
        "quality_status": "NORMAL",
    }
    audio_data = {
        "speech_duration": 6.0,
        "silence_duration": 9.0,
        "speech_segments_count": 3,
        "mean_energy": 0.05,
        "audio_quality_status": "NORMAL",
        "confidence_score": 0.90,
    }

    result = fusion.fuse(visual_data, audio_data, window_duration=15.0)

    assert result["status"] == "CONFIDENT"
    assert result["fused_score"] is not None
    assert 0.0 <= result["fused_score"] <= 100.0
    assert result["visual_weight"] == 0.70
    assert result["audio_weight"] == 0.30
    assert result["confidence"] > 0.85

def test_multimodal_fusion_missing_audio_renormalization():
    fusion = MultimodalFusionService(default_visual_weight=0.70, default_audio_weight=0.30)
    
    visual_data = {
        "forward_facing_ratio": 0.80,
        "movement_score": 12.0,
        "inactivity_duration": 0.0,
        "visibility_ratio": 1.0,
        "confidence_score": 0.90,
        "quality_status": "NORMAL",
    }
    # Audio is muted/silent
    audio_data = {
        "speech_duration": 0.0,
        "silence_duration": 15.0,
        "speech_segments_count": 0,
        "audio_quality_status": "MUTED_OR_SILENT",
    }

    result = fusion.fuse(visual_data, audio_data, window_duration=15.0)

    assert result["status"] == "VISUAL_ONLY"
    assert result["fused_score"] == result["visual_score"]
    assert result["visual_weight"] == 1.0
    assert result["audio_weight"] == 0.0

def test_multimodal_fusion_insufficient_data():
    fusion = MultimodalFusionService()
    result = fusion.fuse(None, None, window_duration=15.0)

    assert result["status"] == "INSUFFICIENT_DATA"
    assert result["fused_score"] is None
    assert result["confidence"] == 0.0
