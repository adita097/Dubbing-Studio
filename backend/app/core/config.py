import os
import shutil
from pathlib import Path
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "DubStudio"
    API_V1_PREFIX: str = "/api"
    
    # AI Providers Configuration
    OPENAI_API_KEY: Optional[str] = None
    TRANSLATION_PROVIDER: str = "mock"  # "mock" or "openai"
    TRANSLATION_API_KEY: Optional[str] = None
    
    SPEECH_PROVIDER: str = "mock"  # "mock" or "openai"
    SPEECH_API_KEY: Optional[str] = None
    
    # Mock AI Mode - defaults to True for local zero-cost testing
    MOCK_AI_MODE: bool = True
    
    # Limits & Constraints
    MAX_UPLOAD_SIZE_MB: int = 500
    MAX_VIDEO_DURATION_SECONDS: int = 1800
    MAX_CONCURRENT_JOBS: int = 3
    
    # Storage
    STORAGE_DIR: str = "storage"
    
    # CORS
    FRONTEND_ORIGIN: str = "http://localhost:5173"
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    
    # FFmpeg / FFprobe overrides
    FFMPEG_PATH: Optional[str] = None
    FFPROBE_PATH: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def base_storage_path(self) -> Path:
        p = Path(self.STORAGE_DIR)
        if not p.is_absolute():
            # relative to backend root
            backend_root = Path(__file__).resolve().parent.parent.parent
            p = backend_root / self.STORAGE_DIR
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def uploads_path(self) -> Path:
        p = self.base_storage_path / "uploads"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def voiceover_path(self) -> Path:
        p = self.base_storage_path / "voiceover"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def output_path(self) -> Path:
        p = self.base_storage_path / "output"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def projects_path(self) -> Path:
        p = self.base_storage_path / "projects"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def get_ffmpeg_binary(self) -> str:
        if self.FFMPEG_PATH and Path(self.FFMPEG_PATH).exists():
            return self.FFMPEG_PATH
        sys_ffmpeg = shutil.which("ffmpeg")
        if sys_ffmpeg:
            return sys_ffmpeg
        return "ffmpeg"

    def get_ffprobe_binary(self) -> str:
        if self.FFPROBE_PATH and Path(self.FFPROBE_PATH).exists():
            return self.FFPROBE_PATH
        sys_ffprobe = shutil.which("ffprobe")
        if sys_ffprobe:
            return sys_ffprobe
        return "ffprobe"


settings = Settings()
