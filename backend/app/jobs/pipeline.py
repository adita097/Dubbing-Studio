import asyncio
from pathlib import Path
from app.jobs.manager import job_manager
from app.schemas.jobs import JobResponse, JobStatus
from app.schemas.project import ProjectStatus, AudioMode
from app.storage.local_storage import storage
from app.services.translation_service import translation_service
from app.services.speech_service import speech_service
from app.services.export_service import export_service


async def execute_translation_job(job: JobResponse, project_id: str, target_lang: str, source_lang: str):
    project = storage.get_project(project_id)
    if not project:
        raise ValueError(f"Project {project_id} not found.")

    if not project.segments:
        raise ValueError("Project contains no subtitle or transcript segments to translate.")

    project.status = ProjectStatus.TRANSLATING
    project.target_language = target_lang
    project.source_language = source_lang
    storage.save_project(project)

    job_manager.update_job(job.job_id, progress=30.0, message="Translating segments with AI...")

    # Call translation service
    translated_segments = await translation_service.translate_segments(
        segments=project.segments,
        source_language=source_lang,
        target_language=target_lang
    )

    job_manager.update_job(job.job_id, progress=85.0, message="Saving translated transcript...")

    project.segments = translated_segments
    project.status = ProjectStatus.TRANSLATED
    project.error_message = None
    storage.save_project(project)


async def execute_voiceover_job(job: JobResponse, project_id: str, voice_id: str):
    project = storage.get_project(project_id)
    if not project:
        raise ValueError(f"Project {project_id} not found.")

    if not project.segments:
        raise ValueError("No transcript segments found to generate voiceover.")

    project.status = ProjectStatus.GENERATING_VOICEOVER
    project.voice_id = voice_id
    storage.save_project(project)

    job_manager.update_job(job.job_id, progress=25.0, message="Synthesizing audio for transcript segments...")

    # Call speech service
    updated_segs, voiceover_path, meta = await speech_service.generate_voiceover_for_project(
        project_id=project.id,
        segments=project.segments,
        voice_id=voice_id,
        target_language=project.target_language
    )

    job_manager.update_job(job.job_id, progress=90.0, message="Assembling audio track...")

    project.segments = updated_segs
    project.voiceover_asset = str(voiceover_path.resolve())
    project.status = ProjectStatus.VOICEOVER_READY
    if meta.get("timing_warnings"):
        project.error_message = "; ".join(meta["timing_warnings"])
    else:
        project.error_message = None

    storage.save_project(project)


async def execute_export_job(
    job: JobResponse,
    project_id: str,
    audio_mode: AudioMode,
    mix_volume: float
):
    project = storage.get_project(project_id)
    if not project:
        raise ValueError(f"Project {project_id} not found.")

    if not project.video_path or not Path(project.video_path).exists():
        raise ValueError("Video source file missing.")

    if not project.voiceover_asset or not Path(project.voiceover_asset).exists():
        raise ValueError("Generated voiceover asset missing. Please generate voiceover first.")

    project.status = ProjectStatus.EXPORTING
    project.audio_mode = audio_mode
    project.mix_original_volume = mix_volume
    storage.save_project(project)

    job_manager.update_job(job.job_id, progress=30.0, message="Composing video and audio with FFmpeg...")

    output_path = storage.get_output_path(project.id)
    export_service.export_video(
        video_input=Path(project.video_path),
        voiceover_input=Path(project.voiceover_asset),
        output_path=output_path,
        audio_mode=audio_mode,
        mix_original_volume=mix_volume
    )

    job_manager.update_job(job.job_id, progress=95.0, message="Validating exported MP4 container...")

    project.output_asset = str(output_path.resolve())
    project.status = ProjectStatus.COMPLETED
    project.error_message = None
    storage.save_project(project)
