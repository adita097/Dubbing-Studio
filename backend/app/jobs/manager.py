import asyncio
import uuid
from datetime import datetime
from typing import Dict, Optional, Callable, Awaitable
from app.core.config import settings
from app.schemas.jobs import JobResponse, JobStatus, JobType


class JobManager:
    def __init__(self):
        self._jobs: Dict[str, JobResponse] = {}
        self._semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_JOBS)

    def create_job(self, project_id: str, task_type: JobType) -> JobResponse:
        job_id = str(uuid.uuid4())
        job = JobResponse(
            job_id=job_id,
            project_id=project_id,
            task_type=task_type,
            status=JobStatus.QUEUED,
            progress=0.0,
            message=f"Job queued for {task_type.value}",
            created_at=datetime.utcnow()
        )
        self._jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> Optional[JobResponse]:
        return self._jobs.get(job_id)

    def update_job(
        self,
        job_id: str,
        status: Optional[JobStatus] = None,
        progress: Optional[float] = None,
        message: Optional[str] = None,
        error: Optional[str] = None
    ) -> Optional[JobResponse]:
        job = self._jobs.get(job_id)
        if not job:
            return None

        if status is not None:
            job.status = status
            if status in (JobStatus.COMPLETED, JobStatus.FAILED):
                job.completed_at = datetime.utcnow()
        if progress is not None:
            job.progress = min(100.0, max(0.0, progress))
        if message is not None:
            job.message = message
        if error is not None:
            job.error = error

        return job

    async def run_async_task(
        self,
        job_id: str,
        coro_func: Callable[[JobResponse], Awaitable[None]]
    ):
        """Executes task under concurrency semaphore."""
        async with self._semaphore:
            job = self.get_job(job_id)
            if not job:
                return

            self.update_job(job_id, status=JobStatus.PROCESSING, progress=10.0, message="Processing started")
            try:
                await coro_func(job)
                self.update_job(job_id, status=JobStatus.COMPLETED, progress=100.0, message="Completed successfully")
            except Exception as e:
                self.update_job(job_id, status=JobStatus.FAILED, error=str(e), message="Task execution failed")


job_manager = JobManager()
