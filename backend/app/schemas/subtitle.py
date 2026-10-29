from typing import Optional, List
from pydantic import BaseModel, Field, model_validator


def format_ms(ms: Optional[int]) -> str:
    """Formats milliseconds into HH:MM:SS.mmm or MM:SS.mmm string."""
    if ms is None:
        return "--:--"
    total_seconds = ms // 1000
    remainder_ms = ms % 1000
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{remainder_ms:03d}"
    return f"{minutes:02d}:{seconds:02d}.{remainder_ms:03d}"


class SubtitleSegment(BaseModel):
    id: int
    start_time_ms: Optional[int] = Field(default=None, description="Start timestamp in milliseconds, null if untimed")
    end_time_ms: Optional[int] = Field(default=None, description="End timestamp in milliseconds, null if untimed")
    original_text: str = Field(..., min_length=1, description="Original subtitle or transcript segment text")
    translated_text: Optional[str] = Field(default=None, description="Translated text for voiceover")
    audio_asset: Optional[str] = Field(default=None, description="Relative path or identifier of generated audio for this segment")

    @model_validator(mode="after")
    def validate_timestamps(self):
        if self.start_time_ms is not None:
            if self.start_time_ms < 0:
                raise ValueError(f"Segment {self.id}: start_time_ms cannot be negative")
            if self.end_time_ms is not None:
                if self.end_time_ms < self.start_time_ms:
                    raise ValueError(f"Segment {self.id}: end_time_ms ({self.end_time_ms}) must be >= start_time_ms ({self.start_time_ms})")
        return self

    @property
    def is_timed(self) -> bool:
        return self.start_time_ms is not None and self.end_time_ms is not None

    @property
    def duration_ms(self) -> Optional[int]:
        if self.is_timed and self.end_time_ms is not None and self.start_time_ms is not None:
            return self.end_time_ms - self.start_time_ms
        return None

    @property
    def start_time_str(self) -> str:
        return format_ms(self.start_time_ms)

    @property
    def end_time_str(self) -> str:
        return format_ms(self.end_time_ms)


class TranscriptUpdateRequest(BaseModel):
    segments: List[SubtitleSegment]


class PasteTranscriptRequest(BaseModel):
    transcript_text: str = Field(..., min_length=1)
    split_mode: str = Field(default="paragraph", description="'paragraph', 'line', or 'sentence'")


class ExtractSubtitleRequest(BaseModel):
    stream_index: int = Field(default=0, description="FFmpeg subtitle stream index to extract")
