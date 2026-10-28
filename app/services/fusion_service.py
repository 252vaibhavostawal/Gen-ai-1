from typing import Dict, Optional, Tuple

class MultimodalFusionService:
    """Combines synchronized visual and acoustic observations over time intervals."""

    def __init__(self, default_visual_weight: float = 0.70, default_audio_weight: float = 0.30):
        self.default_visual_weight = default_visual_weight
        self.default_audio_weight = default_audio_weight

    def normalize_visual_features(self, visual_data: Optional[Dict]) -> Tuple[Optional[float], float, Dict]:
        """
        Normalize visual indicators to [0, 100] scale.
        Returns: (normalized_score, confidence, subcomponents)
        """
        if not visual_data or visual_data.get("quality_status") == "INSUFFICIENT_DATA":
            return None, 0.0, {"reason": "No usable visual observation"}

        forward_ratio = visual_data.get("forward_facing_ratio", 1.0)
        movement = visual_data.get("movement_score", 10.0)
        inactivity = visual_data.get("inactivity_duration", 0.0)
        visibility = visual_data.get("visibility_ratio", 1.0)
        base_confidence = visual_data.get("confidence_score", 0.8)

        # Forward orientation sub-score (0 to 50 pts)
        orientation_score = forward_ratio * 50.0

        # Physical activity sub-score (0 to 50 pts)
        # Moderate micro-movement (6 - 35 px/sec) is typical of active note-taking / listening
        if movement < 3.0:
            # Extended complete inactivity
            movement_sub = max(10.0, 30.0 - (inactivity * 1.5))
        elif movement <= 45.0:
            # Natural attentive movement
            movement_sub = 45.0
        else:
            # High sudden displacement
            movement_sub = 35.0

        raw_visual = orientation_score + movement_sub
        # Modulate by visibility
        normalized_visual = min(100.0, max(0.0, raw_visual * (0.5 + 0.5 * visibility)))
        confidence = base_confidence * visibility

        subcomponents = {
            "forward_orientation_pts": round(orientation_score, 1),
            "movement_activity_pts": round(movement_sub, 1),
            "visibility_ratio": round(visibility, 2),
            "raw_visual_score": round(raw_visual, 1),
        }

        return round(normalized_visual, 2), round(confidence, 3), subcomponents

    def normalize_audio_features(self, audio_data: Optional[Dict], window_duration: float = 15.0) -> Tuple[Optional[float], float, Dict]:
        """
        Normalize classroom audio interaction indicators to [0, 100] scale.
        Returns: (normalized_score, confidence, subcomponents)
        """
        if not audio_data or audio_data.get("audio_quality_status") in ("INSUFFICIENT_DATA", "MUTED_OR_SILENT"):
            return None, 0.0, {"reason": "Audio muted, absent, or insufficient"}

        speech_sec = audio_data.get("speech_duration", 0.0)
        segments = audio_data.get("speech_segments_count", 0)
        quality = audio_data.get("audio_quality_status", "NORMAL")
        base_confidence = audio_data.get("confidence_score", 0.9)

        duration = max(1.0, window_duration)
        speech_ratio = min(1.0, speech_sec / duration)

        # Speech duration component (0 to 60 pts)
        # A healthy interactive classroom has periodic verbal exchanges
        speech_pts = speech_ratio * 60.0

        # Conversational dynamics component (0 to 40 pts)
        # Multiple back-and-forth segments indicate discussion/Q&A
        interaction_pts = min(40.0, segments * 10.0)

        raw_audio = speech_pts + interaction_pts
        confidence = base_confidence
        if quality != "NORMAL":
            confidence *= 0.70

        subcomponents = {
            "speech_ratio": round(speech_ratio, 2),
            "speech_duration_pts": round(speech_pts, 1),
            "interaction_exchange_pts": round(interaction_pts, 1),
            "speech_segments": segments,
            "quality_status": quality,
        }

        return min(100.0, max(0.0, round(raw_audio, 2))), round(confidence, 3), subcomponents

    def fuse(
        self,
        visual_data: Optional[Dict],
        audio_data: Optional[Dict],
        window_duration: float = 15.0,
        custom_visual_weight: Optional[float] = None,
        custom_audio_weight: Optional[float] = None,
    ) -> Dict:
        """
        Produce fused multimodal engagement indicators with transparent explanation.
        """
        v_score, v_conf, v_details = self.normalize_visual_features(visual_data)
        a_score, a_conf, a_details = self.normalize_audio_features(audio_data, window_duration)

        v_weight = custom_visual_weight if custom_visual_weight is not None else self.default_visual_weight
        a_weight = custom_audio_weight if custom_audio_weight is not None else self.default_audio_weight

        # Case 1: Both modalities available with valid signals
        if v_score is not None and a_score is not None:
            total_weight = v_weight + a_weight
            norm_v_w = v_weight / total_weight if total_weight > 0 else 0.7
            norm_a_w = a_weight / total_weight if total_weight > 0 else 0.3

            fused_score = (v_score * norm_v_w) + (a_score * norm_a_w)
            fused_confidence = (v_conf * norm_v_w) + (a_conf * norm_a_w)
            status = "CONFIDENT"
            explanation = {
                "status": status,
                "note": "Combined visual posture/movement and classroom audio interaction.",
                "visual_breakdown": v_details,
                "audio_breakdown": a_details,
            }

        # Case 2: Visual only available
        elif v_score is not None and a_score is None:
            norm_v_w = 1.0
            norm_a_w = 0.0
            fused_score = v_score
            fused_confidence = v_conf * 0.90  # slightly lower due to missing modality
            status = "VISUAL_ONLY"
            explanation = {
                "status": status,
                "note": "Acoustic modality missing or quiet; indicator computed solely from visual orientation and movement.",
                "visual_breakdown": v_details,
                "audio_breakdown": a_details,
            }

        # Case 3: Audio only available
        elif v_score is None and a_score is not None:
            norm_v_w = 0.0
            norm_a_w = 1.0
            fused_score = a_score
            fused_confidence = a_conf * 0.85
            status = "AUDIO_ONLY"
            explanation = {
                "status": status,
                "note": "Visual modality obstructed or unavailable; indicator computed solely from classroom verbal exchanges.",
                "visual_breakdown": v_details,
                "audio_breakdown": a_details,
            }

        # Case 4: Neither modality usable
        else:
            norm_v_w = 0.0
            norm_a_w = 0.0
            fused_score = None
            fused_confidence = 0.0
            status = "INSUFFICIENT_DATA"
            explanation = {
                "status": status,
                "note": "Neither visual nor acoustic observations meet minimum quality criteria.",
                "visual_breakdown": v_details,
                "audio_breakdown": a_details,
            }

        return {
            "visual_score": v_score,
            "audio_score": a_score,
            "fused_score": round(fused_score, 2) if fused_score is not None else None,
            "visual_weight": round(norm_v_w, 2),
            "audio_weight": round(norm_a_w, 2),
            "confidence": round(fused_confidence, 3),
            "status": status,
            "explanation": explanation,
            "pedagogical_disclaimer": "Observed indicators reflect physical orientation and audio activity only, not comprehension or mental engagement.",
        }

fusion_service = MultimodalFusionService()
