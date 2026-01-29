"""
Application Settings Configuration
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Literal
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # API Keys
    # DashScope API Key for Wan2.6-t2v video generation
    dashscope_api_key: str = Field(default="", env="DASHSCOPE_API_KEY")

    # ModelScope API Key for Qwen LLM (using OpenAI-compatible endpoint)
    modelscope_api_key: str = Field(default="", env="MODELSCOPE_API_KEY")

    # ModelScope API endpoint
    modelscope_base_url: str = Field(
        default="https://api-inference.modelscope.cn/v1",
        env="MODELSCOPE_BASE_URL"
    )

    # LLM Model (ModelScope model ID)
    qwen_model: str = Field(
        default="Qwen/Qwen3-235B-A22B-Instruct-2507",
        env="QWEN_MODEL"
    )

    # Embeddings
    embedding_model: str = Field(
        default="text-embedding-v2",
        env="EMBEDDING_MODEL"
    )

    template_match_min_confidence: float = Field(
        default=0.5,
        env="TEMPLATE_MATCH_MIN_CONFIDENCE"
    )

    # Database
    database_url: str = Field(default="sqlite:///./data/jobs.db", env="DATABASE_URL")

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")

    # Static Storage
    static_root: str = Field(default="/var/lib/prism/static", env="STATIC_ROOT")
    static_video_subdir: str = Field(default="vedios", env="STATIC_VIDEO_SUBDIR")
    static_audio_subdir: str = Field(default="audio", env="STATIC_AUDIO_SUBDIR")
    static_metadata_subdir: str = Field(default="metadata", env="STATIC_METADATA_SUBDIR")
    static_video_dir: str = ""
    static_audio_dir: str = ""
    static_metadata_dir: str = ""
    static_url_prefix: str = "/static"

    # FFmpeg
    ffmpeg_path: str = Field(default="ffmpeg", env="FFMPEG_PATH")

    # Application
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO", env="LOG_LEVEL"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize static directory paths
        self.static_video_dir = os.path.join(self.static_root, self.static_video_subdir)
        self.static_audio_dir = os.path.join(self.static_root, self.static_audio_subdir)
        self.static_metadata_dir = os.path.join(self.static_root, self.static_metadata_subdir)

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
