import os
import json
import re
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from app.core.config import settings
from app.schemas.project import Project, ProjectListItem


def sanitize_filename(name: str) -> str:
    """Sanitize filename to prevent path traversal and unsafe characters."""
    # Strip any directory components
    name = Path(name).name
    # Replace unsafe characters
    clean = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', name)
    # Ensure it's not empty or just dots
    if not clean or clean.replace('.', '') == '':
        return "unnamed_file"
    return clean


class LocalStorage:
    def __init__(self):
        self.projects_dir = settings.projects_path
        self.uploads_dir = settings.uploads_path
        self.voiceover_dir = settings.voiceover_path
        self.output_dir = settings.output_path

    def _safe_project_file(self, project_id: str) -> Path:
        safe_id = sanitize_filename(project_id)
        path = (self.projects_dir / f"{safe_id}.json").resolve()
        # Verify no path traversal
        if not path.is_relative_to(self.projects_dir.resolve()):
            raise ValueError("Invalid project ID path")
        return path

    def save_project(self, project: Project) -> Project:
        project.updated_at = datetime.utcnow()
        file_path = self._safe_project_file(project.id)
        # Serialize with Pydantic v2 model_dump_json
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(project.model_dump_json(indent=2))
        return project

    def get_project(self, project_id: str) -> Optional[Project]:
        try:
            file_path = self._safe_project_file(project_id)
            if not file_path.exists():
                return None
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return Project.model_validate(data)
        except Exception:
            return None

    def list_projects(self) -> List[ProjectListItem]:
        projects: List[ProjectListItem] = []
        for file in self.projects_dir.glob("*.json"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                p = Project.model_validate(data)
                projects.append(ProjectListItem(
                    id=p.id,
                    original_filename=p.original_filename,
                    source_language=p.source_language,
                    target_language=p.target_language,
                    status=p.status,
                    subtitle_source=p.subtitle_source,
                    duration_seconds=p.duration_seconds,
                    segments_count=len(p.segments),
                    created_at=p.created_at,
                    updated_at=p.updated_at
                ))
            except Exception:
                continue
        # Sort by updated_at descending
        projects.sort(key=lambda x: x.updated_at, reverse=True)
        return projects

    def delete_project(self, project_id: str) -> bool:
        project = self.get_project(project_id)
        if not project:
            return False

        # Remove video if exists
        if project.video_path:
            vp = Path(project.video_path)
            if vp.exists() and vp.is_relative_to(self.uploads_dir.resolve()):
                try:
                    vp.unlink()
                except OSError:
                    pass

        # Remove voiceover if exists
        if project.voiceover_asset:
            ap = Path(project.voiceover_asset)
            if ap.exists() and ap.is_relative_to(self.voiceover_dir.resolve()):
                try:
                    ap.unlink()
                except OSError:
                    pass

        # Remove output if exists
        if project.output_asset:
            op = Path(project.output_asset)
            if op.exists() and op.is_relative_to(self.output_dir.resolve()):
                try:
                    op.unlink()
                except OSError:
                    pass

        # Remove project file
        file_path = self._safe_project_file(project_id)
        if file_path.exists():
            file_path.unlink()

        return True

    def get_upload_path(self, project_id: str, original_filename: str) -> Path:
        safe_id = sanitize_filename(project_id)
        safe_name = sanitize_filename(original_filename)
        return self.uploads_dir / f"{safe_id}_{safe_name}"

    def get_voiceover_path(self, project_id: str, ext: str = "mp3") -> Path:
        safe_id = sanitize_filename(project_id)
        return self.voiceover_dir / f"{safe_id}_voiceover.{ext}"

    def get_segment_voiceover_path(self, project_id: str, segment_id: int, ext: str = "mp3") -> Path:
        safe_id = sanitize_filename(project_id)
        return self.voiceover_dir / f"{safe_id}_seg_{segment_id}.{ext}"

    def get_output_path(self, project_id: str, ext: str = "mp4") -> Path:
        safe_id = sanitize_filename(project_id)
        return self.output_dir / f"{safe_id}_dubbed.{ext}"


storage = LocalStorage()
