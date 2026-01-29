"""
Application Constants Configuration
"""

from typing import Dict, List, Literal


# Quality Mode Configuration
QUALITY_MODES: Dict[str, Dict] = {
    "fast": {
        # Preview settings
        "preview_size": "1280*720",
        "preview_seeds": 1,
        # Final settings
        "final_size": "1920*1080",
        # Validation
        "validation_strictness": "loose",
        "narration_compression": "aggressive",
        "max_narration_length": 30,
        # Generation
        "max_shots": 3,
        "min_shot_duration_s": 2,
        "max_shot_duration_s": 10,
        # Other
        "enable_auto_fix": True,
        "timeout_multiplier": 0.8,
    },
    "balanced": {
        # Preview settings
        "preview_size": "1280*720",
        "preview_seeds": 2,
        # Final settings
        "final_size": "1920*1080",
        # Validation
        "validation_strictness": "standard",
        "narration_compression": "standard",
        "max_narration_length": 50,
        # Generation
        "max_shots": 6,
        "min_shot_duration_s": 2,
        "max_shot_duration_s": 12,
        # Other
        "enable_auto_fix": True,
        "timeout_multiplier": 1.0,
    },
    "high": {
        # Preview settings
        "preview_size": "1280*720",
        "preview_seeds": 3,
        # Final settings
        "final_size": "1920*1080",
        # Validation
        "validation_strictness": "strict",
        "narration_compression": "minimal",
        "max_narration_length": 80,
        # Generation
        "max_shots": 8,
        "min_shot_duration_s": 2,
        "max_shot_duration_s": 15,
        # Other
        "enable_auto_fix": False,
        "timeout_multiplier": 1.5,
    },
}

# Validation Strictness Levels
VALIDATION_STRICTNESS_LEVELS = {
    "loose": {
        "duration_tolerance_percent": 20,
        "allow_minor_violations": True,
        "auto_fix_attempts": 3,
        "require_medical_compliance": True,
        "enforce_subtitle_policy": "soft",
    },
    "standard": {
        "duration_tolerance_percent": 10,
        "allow_minor_violations": False,
        "auto_fix_attempts": 1,
        "require_medical_compliance": True,
        "enforce_subtitle_policy": "standard",
    },
    "strict": {
        "duration_tolerance_percent": 5,
        "allow_minor_violations": False,
        "auto_fix_attempts": 0,
        "require_medical_compliance": True,
        "enforce_subtitle_policy": "strict",
    },
}

# Narration Compression Levels
NARRATION_COMPRESSION_LEVELS = {
    "aggressive": {
        "target_reduction_percent": 40,
        "preserve_keywords": True,
        "simplify_language": True,
    },
    "standard": {
        "target_reduction_percent": 20,
        "preserve_keywords": True,
        "simplify_language": False,
    },
    "minimal": {
        "target_reduction_percent": 5,
        "preserve_keywords": True,
        "simplify_language": False,
    },
}

# Rate Limiting Configuration
RATE_LIMIT_PER_MIN: int = 10
RATE_LIMIT_BURST: int = 10
RATE_LIMIT_WINDOW_S: int = 60
MAX_CONCURRENT_JOBS_PER_IP: int = 5

# Language Support
SUPPORTED_LANGUAGES: List[str] = ["zh-CN", "en-US", "ja-JP"]
AUTO_TRANSLATE: bool = True

# Job Constraints
MIN_DURATION_S: int = 2
MAX_DURATION_S: int = 15
MIN_SHOT_DURATION_S: int = 2
MAX_SHOT_DURATION_S: int = 15

# Supported Resolutions
SUPPORTED_RESOLUTIONS: List[str] = ["1280x720", "1920x1080"]

# Watermark Options
WATERMARK_OPTIONS: List[str] = ["none", "soft", "hard"]

# Subtitle Policy Options
SUBTITLE_POLICY_OPTIONS: List[str] = ["none", "allowed", "auto"]

# Job Timeout
JOB_TIMEOUT_MINUTES: int = 20

# Retry Configuration
MAX_RETRY_ATTEMPTS: int = 3
RETRY_INITIAL_DELAY_S: int = 2
RETRY_MAX_DELAY_S: int = 20

# FFmpeg Configuration
FFMPEG_VIDEO_CODEC: str = "libx264"
FFMPEG_AUDIO_CODEC: str = "mp3"
FFMPEG_VIDEO_BITRATE: str = "2M"
FFMPEG_AUDIO_BITRATE: str = "192k"

# Storage Retention
JOB_RETENTION_DAYS: int = 30
