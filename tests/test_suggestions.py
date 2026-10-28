import pytest
from app.services.suggestion_service import TeachingSuggestionAgent

def test_suggestions_declining_interaction():
    agent = TeachingSuggestionAgent()
    
    # 4 windows: high activity in first half, declining in second half
    fusion_history = [
        {"fused_score": 80.0, "visual_score": 80.0, "audio_score": 80.0, "confidence": 0.9},
        {"fused_score": 75.0, "visual_score": 75.0, "audio_score": 75.0, "confidence": 0.9},
        {"fused_score": 45.0, "visual_score": 45.0, "audio_score": 45.0, "confidence": 0.8},
        {"fused_score": 40.0, "visual_score": 40.0, "audio_score": 40.0, "confidence": 0.8},
    ]

    att_stats = {"attendance_percentage": 90.0, "total_tracked": 10, "late_count": 0}
    result = agent.generate_suggestions(
        session_id=1,
        session_duration_minutes=60.0,
        attendance_stats=att_stats,
        fusion_history=fusion_history,
    )

    assert len(result["actionable_suggestions"]) >= 2
    assert "reduction" in result["pattern_summary"].lower() or "notable" in result["pattern_summary"].lower()
    assert result["confidence_level"] in ["HIGH", "MEDIUM"]
    assert "limitations_note" in result
    assert "comprehension" in result["limitations_note"].lower()

def test_suggestions_insufficient_windows():
    agent = TeachingSuggestionAgent()
    result = agent.generate_suggestions(
        session_id=2,
        session_duration_minutes=10.0,
        attendance_stats={},
        fusion_history=[],
    )
    assert result["confidence_level"] == "LOW"
    assert len(result["actionable_suggestions"]) >= 1
