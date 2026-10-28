import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class Config:
    """Base application configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-offline-secret-key-4e25358d-6593-4832")
    
    # Storage and paths
    INSTANCE_DIR = BASE_DIR / "instance"
    UPLOAD_DIR = BASE_DIR / "uploads"
    REPORTS_DIR = BASE_DIR / "reports"
    LOCAL_MODELS_DIR = BASE_DIR / "local_models"
    
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{INSTANCE_DIR / 'attendance_agent.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Maximum upload size: 500MB for local video files
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024
    
    # Computer Vision & Video Processing
    FRAME_RESIZE_WIDTH = int(os.environ.get("FRAME_RESIZE_WIDTH", 640))
    FRAME_RESIZE_HEIGHT = int(os.environ.get("FRAME_RESIZE_HEIGHT", 480))
    TARGET_FPS = int(os.environ.get("TARGET_FPS", 10))
    
    # Sustained Presence Attendance State Machine Defaults
    DETECTION_CONFIDENCE_THRESHOLD = float(os.environ.get("DETECTION_CONFIDENCE_THRESHOLD", 0.60))
    SUSTAINED_PRESENCE_SECONDS = float(os.environ.get("SUSTAINED_PRESENCE_SECONDS", 30.0))
    MIN_OBSERVATION_COVERAGE = float(os.environ.get("MIN_OBSERVATION_COVERAGE", 0.60))
    GRACE_PERIOD_SECONDS = float(os.environ.get("GRACE_PERIOD_SECONDS", 10.0))
    TRACK_TIMEOUT_SECONDS = float(os.environ.get("TRACK_TIMEOUT_SECONDS", 25.0))
    LATE_ARRIVAL_MINUTES = int(os.environ.get("LATE_ARRIVAL_MINUTES", 10))
    
    # Audio Processing Defaults
    AUDIO_SAMPLE_RATE = int(os.environ.get("AUDIO_SAMPLE_RATE", 16000))
    AUDIO_CHANNELS = int(os.environ.get("AUDIO_CHANNELS", 1))
    AUDIO_FRAME_MS = 30
    AUDIO_WINDOW_SECONDS = float(os.environ.get("AUDIO_WINDOW_SECONDS", 15.0))
    
    # Multimodal Fusion Weights (illustrative defaults, configurable)
    DEFAULT_VISUAL_WEIGHT = 0.70
    DEFAULT_AUDIO_WEIGHT = 0.30
    FUSION_WINDOW_SECONDS = 30.0
    
    # Pluggable Local AI Engine
    OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3:8b")
    USE_LOCAL_LLM = os.environ.get("USE_LOCAL_LLM", "false").lower() in ("true", "1", "yes")
    
    # Privacy Defaults
    RETAIN_RAW_VIDEO = os.environ.get("RETAIN_RAW_VIDEO", "false").lower() in ("true", "1", "yes")
    RETAIN_RAW_AUDIO = os.environ.get("RETAIN_RAW_AUDIO", "false").lower() in ("true", "1", "yes")
    DATA_RETENTION_DAYS = int(os.environ.get("DATA_RETENTION_DAYS", 90))
    ENABLE_OFFLINE_TRANSCRIPTION = False

class DevelopmentConfig(Config):
    DEBUG = True

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SUSTAINED_PRESENCE_SECONDS = 2.0  # Fast testing
    GRACE_PERIOD_SECONDS = 1.0
    FUSION_WINDOW_SECONDS = 2.0

class ProductionConfig(Config):
    DEBUG = False

config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
