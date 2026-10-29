from fastapi import APIRouter
from app.core.config import settings
from app.providers.translation.base import SUPPORTED_LANGUAGES
from app.providers.speech.base import VOICE_OPTIONS

router = APIRouter(tags=["Health"])


@router.get("/health")
def get_health():
    return {
        "status": "ok",
        "mock_mode": settings.MOCK_AI_MODE,
        "translation_provider": settings.TRANSLATION_PROVIDER,
        "speech_provider": settings.SPEECH_PROVIDER,
        "supported_languages": SUPPORTED_LANGUAGES,
        "voice_options": VOICE_OPTIONS,
    }
