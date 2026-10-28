import pytest
import numpy as np
from app.services.audio_service import AudioService

def test_audio_silent_frame():
    service = AudioService()
    silence = np.zeros(16000, dtype=np.float32)
    res = service.analyze_audio_segment(silence, sample_rate=16000)

    assert res["mean_energy"] < 0.001
    assert res["speech_duration"] == 0.0
    assert res["audio_quality_status"] == "MUTED_OR_SILENT"

def test_audio_synthetic_speech_signal():
    service = AudioService(vad_energy_threshold=0.01)
    sr = 16000
    t = np.linspace(0, 1.0, sr, endpoint=False)
    # Generate 300Hz modulated sine wave simulating vocal formant
    speech_signal = 0.25 * np.sin(2 * np.pi * 300 * t).astype(np.float32)
    
    res = service.analyze_audio_segment(speech_signal, sample_rate=sr)
    assert res["mean_energy"] > 0.05
    assert res["speech_duration"] > 0.8
    assert res["speech_segments_count"] >= 1
    assert res["audio_quality_status"] == "NORMAL"

def test_audio_clipping_detection():
    service = AudioService()
    clipped = np.ones(16000, dtype=np.float32)
    res = service.analyze_audio_segment(clipped, sample_rate=16000)
    assert res["audio_quality_status"] == "CLIPPING_DISTORTION"
