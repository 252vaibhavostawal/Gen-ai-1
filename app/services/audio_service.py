import math
import wave
import io
from typing import Dict, List, Optional, Tuple

try:
    import numpy as np
except ImportError:
    np = None

try:
    import sounddevice as sd
except ImportError:
    sd = None

class AudioService:
    """Classroom audio activity analysis and voice activity detection (VAD)."""

    def __init__(
        self,
        sample_rate: int = 16000,
        vad_energy_threshold: float = 0.02,
        zcr_speech_threshold: float = 0.05,
    ):
        self.sample_rate = sample_rate
        self.vad_energy_threshold = vad_energy_threshold
        self.zcr_speech_threshold = zcr_speech_threshold
        self.is_recording = False
        self._stream = None

    def compute_frame_features(self, audio_chunk: "np.ndarray") -> Dict:
        """
        Extract acoustic features from a 1D float/int numpy audio chunk.
        """
        if np is None or audio_chunk is None or len(audio_chunk) == 0:
            return {
                "rms_energy": 0.0,
                "zcr": 0.0,
                "is_speech": False,
                "is_clipping": False,
            }

        # Normalize to float [-1.0, 1.0] if integer format
        if np.issubdtype(audio_chunk.dtype, np.integer):
            max_val = float(np.iinfo(audio_chunk.dtype).max)
            samples = audio_chunk.astype(np.float32) / max_val
        else:
            samples = audio_chunk.astype(np.float32)

        # RMS Energy
        mean_sq = np.mean(samples ** 2)
        rms = float(math.sqrt(max(0.0, mean_sq)))

        # Zero Crossing Rate (ZCR)
        signs = np.sign(samples)
        signs[signs == 0] = -1
        zcr = float(np.mean(np.abs(signs[1:] - signs[:-1])) / 2.0)

        # Clipping detection
        peak = float(np.max(np.abs(samples)))
        is_clipping = peak >= 0.99

        # Voice Activity Decision (energy above ambient noise floor and moderate ZCR typical of human vocal formants)
        is_speech = (rms >= self.vad_energy_threshold) and (zcr >= 0.01) and (zcr <= 0.40)

        return {
            "rms_energy": rms,
            "peak_energy": peak,
            "zcr": zcr,
            "is_speech": is_speech,
            "is_clipping": is_clipping,
        }

    def analyze_audio_segment(self, audio_data: "np.ndarray", sample_rate: int = 16000) -> Dict:
        """
        Analyze a multi-second audio window and produce aggregated metrics.
        """
        if np is None or audio_data is None or len(audio_data) == 0:
            return {
                "speech_duration": 0.0,
                "silence_duration": 0.0,
                "speech_segments_count": 0,
                "mean_energy": 0.0,
                "peak_energy": 0.0,
                "audio_quality_status": "INSUFFICIENT_DATA",
                "confidence_score": 0.0,
            }

        duration_sec = len(audio_data) / float(sample_rate)
        # Frame size: 30ms chunks
        frame_len = int(sample_rate * 0.030)
        if frame_len <= 0:
            frame_len = len(audio_data)

        num_frames = len(audio_data) // frame_len
        if num_frames == 0:
            num_frames = 1
            frames = [audio_data]
        else:
            frames = [audio_data[i * frame_len : (i + 1) * frame_len] for i in range(num_frames)]

        speech_frames = 0
        clipping_frames = 0
        total_rms = 0.0
        peak_rms = 0.0
        segments_count = 0
        in_speech_segment = False

        for f in frames:
            feat = self.compute_frame_features(f)
            total_rms += feat["rms_energy"]
            if feat["rms_energy"] > peak_rms:
                peak_rms = feat["rms_energy"]
            if feat["is_clipping"]:
                clipping_frames += 1
            if feat["is_speech"]:
                speech_frames += 1
                if not in_speech_segment:
                    segments_count += 1
                    in_speech_segment = True
            else:
                in_speech_segment = False

        frame_duration = duration_sec / float(num_frames)
        speech_duration = speech_frames * frame_duration
        silence_duration = max(0.0, duration_sec - speech_duration)
        mean_energy = total_rms / float(num_frames)

        # Determine audio quality indicator
        if mean_energy < 0.001:
            quality = "MUTED_OR_SILENT"
            confidence = 0.50
        elif (clipping_frames / float(num_frames)) > 0.05:
            quality = "CLIPPING_DISTORTION"
            confidence = 0.70
        else:
            quality = "NORMAL"
            confidence = 0.95

        return {
            "speech_duration": round(speech_duration, 2),
            "silence_duration": round(silence_duration, 2),
            "speech_segments_count": segments_count,
            "mean_energy": round(mean_energy, 4),
            "peak_energy": round(peak_rms, 4),
            "audio_quality_status": quality,
            "confidence_score": round(confidence, 3),
        }

    def decode_wav_file(self, wav_path: str) -> Tuple[Optional["np.ndarray"], int]:
        """Read a local recorded WAV audio file offline without external tools."""
        if np is None:
            return None, 16000
        try:
            with wave.open(wav_path, "rb") as wf:
                n_channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                framerate = wf.getframerate()
                n_frames = wf.getnframes()
                raw_bytes = wf.readframes(n_frames)

                if sampwidth == 2:
                    dtype = np.int16
                elif sampwidth == 4:
                    dtype = np.int32
                else:
                    dtype = np.uint8

                data = np.frombuffer(raw_bytes, dtype=dtype)
                if n_channels > 1:
                    data = data.reshape(-1, n_channels)
                    # Convert to mono by averaging channels
                    data = np.mean(data, axis=1)

                return data, framerate
        except Exception:
            return None, 16000

audio_service = AudioService()
