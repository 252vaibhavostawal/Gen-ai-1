import re
from datetime import datetime
from typing import Dict, Any, List, Tuple

def validate_student_data(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate student creation / update input."""
    errors = []
    student_id = str(data.get("student_id", "")).strip()
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip()
    
    if not student_id:
        errors.append("Student ID / Roll Number is required.")
    elif len(student_id) > 50:
        errors.append("Student ID must be under 50 characters.")
        
    if not name:
        errors.append("Student Name is required.")
    elif len(name) > 120:
        errors.append("Student Name must be under 120 characters.")
        
    if email:
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            errors.append("Invalid email address format.")
            
    return (len(errors) == 0, errors)

def validate_session_data(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate class session creation input."""
    errors = []
    title = str(data.get("title", "")).strip()
    duration = data.get("expected_duration_minutes", 60)
    source_type = data.get("input_source_type", "webcam")
    
    if not title:
        errors.append("Session title is required.")
        
    try:
        duration_int = int(duration)
        if duration_int <= 0 or duration_int > 600:
            errors.append("Expected duration must be between 1 and 600 minutes.")
    except (ValueError, TypeError):
        errors.append("Duration must be a valid integer.")
        
    if source_type not in ["webcam", "video_file", "synthetic"]:
        errors.append("Invalid input source type.")
        
    return (len(errors) == 0, errors)

def validate_attendance_override(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate instructor attendance manual correction."""
    errors = []
    status = data.get("attendance_status", "")
    allowed = ["PRESENT", "ABSENT", "LATE", "UNCONFIRMED", "DEPARTED_EARLY"]
    if status not in allowed:
        errors.append(f"Invalid attendance status. Allowed: {', '.join(allowed)}")
    return (len(errors) == 0, errors)
