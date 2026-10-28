import json
import urllib.request
import urllib.error
from typing import Dict, List, Optional
from app.extensions import db
from app.models.suggestion import TeachingSuggestion
from app.models.session import ClassSession

class TeachingSuggestionAgent:
    """Evidence-based pedagogical recommendation agent with deterministic engine and optional local LLM."""

    def __init__(self, ollama_url: str = "http://localhost:11434", default_model: str = "llama3:8b", use_local_llm: bool = False):
        self.ollama_url = ollama_url
        self.default_model = default_model
        self.use_local_llm = use_local_llm

    def check_ollama_availability(self) -> bool:
        """Check if local Ollama daemon is reachable offline without external network."""
        try:
            req = urllib.request.Request(f"{self.ollama_url}/api/tags", headers={"User-Agent": "MultimodalAgent/1.0"})
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                return resp.status == 200
        except Exception:
            return False

    def generate_suggestions(
        self,
        session_id: int,
        session_duration_minutes: float,
        attendance_stats: Dict,
        fusion_history: List[Dict],
        objectives: Optional[str] = None,
        prefer_llm: bool = False,
    ) -> Dict:
        """
        Analyze observable patterns across the session and generate explainable suggestions.
        """
        # Validate data adequacy
        if not fusion_history or len(fusion_history) == 0:
            return {
                "pattern_summary": "Insufficient observation intervals recorded during the session.",
                "actionable_suggestions": [
                    "Ensure video and audio input streams remain active for at least two complete analysis windows before running analysis."
                ],
                "evidence": {"windows_recorded": 0},
                "confidence_level": "LOW",
                "confidence_explanation": "No valid multimodal data windows were available.",
                "limitations_note": "Recommendations cannot be produced without observable classroom intervals.",
                "source_engine": "deterministic",
            }

        # Calculate chronological metrics
        num_windows = len(fusion_history)
        first_half = fusion_history[: max(1, num_windows // 2)]
        second_half = fusion_history[max(1, num_windows // 2) :]

        avg_first_score = sum(w.get("fused_score") or 50.0 for w in first_half) / len(first_half)
        avg_second_score = sum(w.get("fused_score") or 50.0 for w in second_half) / len(second_half)
        delta_score = avg_second_score - avg_first_score

        # Check audio verbal activity
        audio_scores = [w.get("audio_score") for w in fusion_history if w.get("audio_score") is not None]
        avg_audio = (sum(audio_scores) / len(audio_scores)) if audio_scores else None

        # Check visual orientation
        visual_scores = [w.get("visual_score") for w in fusion_history if w.get("visual_score") is not None]
        avg_visual = (sum(visual_scores) / len(visual_scores)) if visual_scores else None

        # Check missing modalities / confidence
        confidences = [w.get("confidence", 0.5) for w in fusion_history]
        mean_confidence = sum(confidences) / len(confidences) if confidences else 0.5

        # Try optional Local LLM if enabled and requested
        if (self.use_local_llm or prefer_llm) and self.check_ollama_availability():
            llm_result = self._generate_with_ollama(
                session_duration_minutes, attendance_stats, delta_score, avg_visual, avg_audio, objectives
            )
            if llm_result:
                return llm_result

        # Default: Deterministic Rule-Based Pedagogical Engine
        return self._generate_deterministic(
            session_duration_minutes=session_duration_minutes,
            attendance_stats=attendance_stats,
            delta_score=delta_score,
            avg_visual=avg_visual,
            avg_audio=avg_audio,
            mean_confidence=mean_confidence,
            objectives=objectives,
        )

    def _generate_deterministic(
        self,
        session_duration_minutes: float,
        attendance_stats: Dict,
        delta_score: float,
        avg_visual: Optional[float],
        avg_audio: Optional[float],
        mean_confidence: float,
        objectives: Optional[str],
    ) -> Dict:
        """Deterministic, fully explainable rule-based pedagogical suggestion engine."""
        patterns = []
        suggestions = []
        evidence = {
            "session_duration_minutes": round(session_duration_minutes, 1),
            "attendance_percentage": attendance_stats.get("attendance_percentage", 0.0),
            "trend_delta_second_half": round(delta_score, 2),
            "mean_visual_indicator": round(avg_visual, 1) if avg_visual is not None else None,
            "mean_audio_indicator": round(avg_audio, 1) if avg_audio is not None else None,
            "mean_data_confidence": round(mean_confidence, 2),
        }

        # Rule 1: Decline in interaction or movement in later portion of session
        if delta_score < -15.0:
            patterns.append(
                f"Observable movement and acoustic activity exhibited a notable reduction ({abs(round(delta_score, 1))} pts) in the second half."
            )
            suggestions.append(
                "Consider inserting a 3-minute interactive checkpoint, think-pair-share prompt, or concept check halfway through extended lecture blocks."
            )
        elif delta_score > 12.0:
            patterns.append(
                f"Interaction and observable activity increased by {round(delta_score, 1)} pts toward the end of the session."
            )
            suggestions.append(
                "The concluding activities generated active discussion; consider capturing open student questions or assigning a brief wrap-up reflection."
            )
        else:
            patterns.append("Observable activity remained steady across earlier and later classroom segments.")

        # Rule 2: Low acoustic activity throughout
        if avg_audio is not None and avg_audio < 25.0:
            patterns.append("Classroom verbal exchanges were sparse across the recorded duration.")
            suggestions.append(
                "Incorporate targeted open-ended questions or poll student perspectives to foster two-way dialogue."
            )
        elif avg_audio is not None and avg_audio > 65.0:
            patterns.append("High conversational and acoustic density was recorded across multiple segments.")
            suggestions.append(
                "Active collaborative discussion was observed; verify that all student groups had equitable opportunity to contribute."
            )

        # Rule 3: Visual orientation trends
        if avg_visual is not None and avg_visual < 40.0:
            patterns.append("Frequent off-axis head orientation was observed across student tracks.")
            suggestions.append(
                "Check slide contrast, visibility of physical board material, or consider whether students are predominantly referencing independent notes/devices."
            )

        # Rule 4: Punctuality and attendance distribution
        late_pct = 0.0
        tot = attendance_stats.get("total_tracked", 0)
        if tot > 0:
            late_pct = (attendance_stats.get("late_count", 0) / tot) * 100.0
        if late_pct >= 25.0:
            suggestions.append(
                f"Late arrivals accounted for {round(late_pct, 1)}% of attendees. Consider reviewing the opening recap or moving critical administrative announcements to minute 10."
            )

        # Ensure at least two suggestions
        if len(suggestions) < 2:
            suggestions.append("Continue aligning lecture segments with periodic formative feedback questions.")
            suggestions.append("Maintain the current balance of instruction and observation intervals.")

        # Determine confidence level
        if mean_confidence >= 0.75:
            conf_level = "HIGH"
            conf_exp = "Observations are grounded in consistent visual tracking and stable audio capture."
        elif mean_confidence >= 0.45:
            conf_level = "MEDIUM"
            conf_exp = "Observations reflect moderate tracking confidence; some intervals had partial occlusion or ambient noise."
        else:
            conf_level = "LOW"
            conf_exp = "Limited camera visibility or low audio SNR affected feature extraction quality."

        return {
            "pattern_summary": " ".join(patterns),
            "actionable_suggestions": suggestions[:4],
            "evidence": evidence,
            "confidence_level": conf_level,
            "confidence_explanation": conf_exp,
            "limitations_note": "Observed indicators reflect physical orientation and audio metrics only. They do not evaluate student comprehension, internal interest, or individual academic merit.",
            "source_engine": "deterministic",
        }

    def _generate_with_ollama(
        self,
        duration: float,
        attendance: Dict,
        delta: float,
        avg_v: Optional[float],
        avg_a: Optional[float],
        objectives: Optional[str],
    ) -> Optional[Dict]:
        """Call local Ollama instance with structured JSON prompt."""
        prompt = f"""
You are an educational assistant analyzing observable classroom data.
Context:
- Duration: {duration} mins
- Attendance: {attendance.get('attendance_percentage', 0)}%
- Trend Delta: {delta} pts
- Visual Indicator: {avg_v}
- Audio Indicator: {avg_a}
- Objectives: {objectives or 'Standard instructional session'}

Provide a JSON object with:
"pattern_summary": string,
"actionable_suggestions": list of 2-4 concrete suggestions,
"confidence_level": "HIGH" or "MEDIUM" or "LOW",
"confidence_explanation": string,
"limitations_note": string

Do not make assumptions about student emotion or understanding.
"""
        payload = json.dumps({
            "model": self.default_model,
            "prompt": prompt,
            "format": "json",
            "stream": False,
        }).encode("utf-8")

        try:
            req = urllib.request.Request(
                f"{self.ollama_url}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                parsed = json.loads(data.get("response", "{}"))
                if "actionable_suggestions" in parsed:
                    parsed["source_engine"] = f"ollama ({self.default_model})"
                    parsed["evidence"] = {
                        "trend_delta": round(delta, 2),
                        "mean_visual": round(avg_v, 1) if avg_v is not None else None,
                        "mean_audio": round(avg_a, 1) if avg_a is not None else None,
                    }
                    return parsed
        except Exception:
            pass
        return None

    def save_suggestion_to_db(self, session_id: int, suggestion_result: Dict, timestamp: float) -> TeachingSuggestion:
        """Persist suggestion record in database."""
        s = TeachingSuggestion(
            session_id=session_id,
            timestamp=timestamp,
            pattern_summary=suggestion_result["pattern_summary"],
            actionable_suggestions_json=json.dumps(suggestion_result["actionable_suggestions"]),
            evidence_json=json.dumps(suggestion_result.get("evidence", {})),
            confidence_level=suggestion_result.get("confidence_level", "MEDIUM"),
            confidence_explanation=suggestion_result.get("confidence_explanation"),
            limitations_note=suggestion_result.get("limitations_note"),
            source_engine=suggestion_result.get("source_engine", "deterministic"),
        )
        db.session.add(s)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
        return s

suggestion_agent = TeachingSuggestionAgent()
