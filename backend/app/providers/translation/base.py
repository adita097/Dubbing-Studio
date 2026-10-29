from abc import ABC, abstractmethod
from typing import List, Dict
from app.schemas.subtitle import SubtitleSegment


SUPPORTED_LANGUAGES: Dict[str, str] = {
    "en": "English",
    "es": "Spanish",
    "hi": "Hindi",
    "ko": "Korean",
    "ja": "Japanese",
    "fr": "French",
    "de": "German",
    "pt": "Portuguese",
    "zh": "Chinese",
    "it": "Italian",
}


class BaseTranslationProvider(ABC):
    @abstractmethod
    async def translate(
        self,
        segments: List[SubtitleSegment],
        source_language: str,
        target_language: str
    ) -> List[SubtitleSegment]:
        """
        Translates a list of SubtitleSegment objects.
        Returns a new list with translated_text populated, preserving IDs, timestamps, and order.
        """
        pass
