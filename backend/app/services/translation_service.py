from typing import List, Optional
from app.core.config import settings
from app.schemas.subtitle import SubtitleSegment
from app.providers.translation.base import BaseTranslationProvider
from app.providers.translation.mock_provider import MockTranslationProvider
from app.providers.translation.openai_provider import OpenAITranslationProvider


class TranslationService:
    def __init__(self, provider: Optional[BaseTranslationProvider] = None):
        self._provider = provider

    def get_provider(self) -> BaseTranslationProvider:
        if self._provider:
            return self._provider

        if settings.MOCK_AI_MODE or settings.TRANSLATION_PROVIDER.lower() == "mock":
            return MockTranslationProvider()

        api_key = settings.TRANSLATION_API_KEY or settings.OPENAI_API_KEY
        if not api_key:
            raise ValueError("No API key configured for translation provider. Enable MOCK_AI_MODE or set OPENAI_API_KEY.")
        return OpenAITranslationProvider(api_key=api_key)

    async def translate_segments(
        self,
        segments: List[SubtitleSegment],
        source_language: str,
        target_language: str
    ) -> List[SubtitleSegment]:
        if not segments:
            return []
        provider = self.get_provider()
        return await provider.translate(segments, source_language, target_language)


translation_service = TranslationService()
