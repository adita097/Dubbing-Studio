from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.schemas.subtitle import SubtitleSegment


class SubtitleSource(str, Enum):
    SRT = "srt"
    VTT = "vtt"
    PASTE = "paste"
    EMBEDDED = "embedded"


class ProjectStatus(str, Enum):
    CREATED = "created"
    TRANSLATING = "translating"
    TRANSLATED = "translated"
    GENERATING_VOICEOVER = "generating_voiceover"
    VOICEOVER_READY = "voiceover_ready"
    EXPORTING = "exporting"
    COMPLETED = "completed"
    FAILED = "failed"


class AudioMode(str, Enum):
    REPLACE = "replace"
    MIX = "mix"


class EmbeddedSubtitleStream(BaseModel):
    index: int
    codec_name: str
    language: Optional[str] = "und"
    title: Optional[str] = None


class ProjectBase(BaseModel):
    source_language: str = Field(default="en", description="Source language code, e.g. 'en', 'ko'")
    target_language: str = Field(default="es", description="Target language code, e.g. 'es', 'hi'")
    audio_mode: AudioMode = Field(default=AudioMode.REPLACE)
    mix_original_volume: float = Field(default=0.15, ge=0.0, le=1.0)
    voice_id: str = Field(default="alloy")


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    source_language: Optional[str] = None
    target_language: Optional[str] = None
    audio_mode: Optional[AudioMode] = None
    mix_original_volume: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    voice_id: Optional[str] = None


class Project(ProjectBase):
    id: str
    original_filename: str
    video_path: Optional[str] = None
    duration_seconds: Optional[float] = None
    video_width: Optional[int] = None
    video_height: Optional[int] = None
    has_audio: bool = True
    embedded_subtitles: List[EmbeddedSubtitleStream] = Field(default_factory=list)
    subtitle_source: Optional[SubtitleSource] = None
    status: ProjectStatus = ProjectStatus.CREATED
    segments: List[SubtitleSegment] = Field(default_factory=list)
    voiceover_asset: Optional[str] = None
    output_asset: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    error_message: Optional[str] = None


class ProjectResponse(Project):
    pass


class ProjectListItem(BaseModel):
    id: str
    original_filename: str
    source_language: str
    target_language: str
    status: ProjectStatus
    subtitle_source: Optional[SubtitleSource] = None
    duration_seconds: Optional[float] = None
    segments_count: int = 0
    created_at: datetime
    updated_at: datetime
