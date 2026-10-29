from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobType(str, Enum):
    TRANSLATION = "translation"
    VOICEOVER = "voiceover"
    EXPORT = "export"


class JobResponse(BaseModel):
    job_id: str
    project_id: str
    task_type: JobType
    status: JobStatus
    progress: float = Field(default=0.0, ge=0.0, le=100.0)
    message: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
