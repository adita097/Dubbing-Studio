import uuid
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from fastapi.responses import FileResponse

from app.core.config import settings
from app.storage.local_storage import storage, sanitize_filename
from app.schemas.project import (
    Project,
    ProjectResponse,
    ProjectListItem,
    ProjectUpdate,
    ProjectStatus,
    AudioMode
)
from app.services.media_service import media_service

router = APIRouter(prefix="/projects", tags=["Projects"])

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv"}


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    video: UploadFile = File(...),
    source_language: str = Form("en"),
    target_language: str = Form("es"),
    voice_id: str = Form("alloy"),
    audio_mode: AudioMode = Form(AudioMode.REPLACE),
    mix_original_volume: float = Form(0.15)
):
    ext = Path(video.filename or "").suffix.lower()
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported video format: '{ext}'. Allowed: {', '.join(ALLOWED_VIDEO_EXTENSIONS)}"
        )

    project_id = str(uuid.uuid4())
    upload_dest = storage.get_upload_path(project_id, video.filename or "video.mp4")
    upload_dest.parent.mkdir(parents=True, exist_ok=True)

    # Stream write with size limit checking
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    total_written = 0

    with open(upload_dest, "wb") as f:
        while chunk := await video.read(1024 * 1024):
            total_written += len(chunk)
            if total_written > max_bytes:
                upload_dest.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Video exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB."
                )
            f.write(chunk)

    # Inspect media properties with ffprobe
    media_info = media_service.inspect_media(upload_dest)
    dur = media_info.get("duration_seconds", 0.0)
    if dur > settings.MAX_VIDEO_DURATION_SECONDS:
        upload_dest.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Video duration ({dur:.1f}s) exceeds maximum allowed duration ({settings.MAX_VIDEO_DURATION_SECONDS}s)."
        )

    project = Project(
        id=project_id,
        original_filename=sanitize_filename(video.filename or "video.mp4"),
        video_path=str(upload_dest.resolve()),
        duration_seconds=dur,
        video_width=media_info.get("video_width"),
        video_height=media_info.get("video_height"),
        has_audio=media_info.get("has_audio", True),
        embedded_subtitles=media_info.get("embedded_subtitles", []),
        source_language=source_language,
        target_language=target_language,
        voice_id=voice_id,
        audio_mode=audio_mode,
        mix_original_volume=mix_original_volume,
        status=ProjectStatus.CREATED
    )

    storage.save_project(project)
    return project


@router.get("", response_model=List[ProjectListItem])
def list_projects():
    return storage.list_projects()


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str):
    project = storage.get_project(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: str, payload: ProjectUpdate):
    project = storage.get_project(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if payload.source_language is not None:
        project.source_language = payload.source_language
    if payload.target_language is not None:
        project.target_language = payload.target_language
    if payload.audio_mode is not None:
        project.audio_mode = payload.audio_mode
    if payload.mix_original_volume is not None:
        project.mix_original_volume = payload.mix_original_volume
    if payload.voice_id is not None:
        project.voice_id = payload.voice_id

    storage.save_project(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_200_OK)
def delete_project(project_id: str):
    deleted = storage.delete_project(project_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return {"message": "Project deleted successfully", "id": project_id}


@router.get("/{project_id}/video")
def get_project_video(project_id: str):
    project = storage.get_project(project_id)
    if not project or not project.video_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

    path = Path(project.video_path)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video file missing on disk")

    media_type = "video/mp4"
    if path.suffix.lower() == ".webm":
        media_type = "video/webm"
    elif path.suffix.lower() == ".mov":
        media_type = "video/quicktime"

    return FileResponse(path, media_type=media_type)
