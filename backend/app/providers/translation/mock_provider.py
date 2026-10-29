from typing import List, Dict
import copy
from app.providers.translation.base import BaseTranslationProvider, SUPPORTED_LANGUAGES
from app.schemas.subtitle import SubtitleSegment


MOCK_TRANSLATION_MAP: Dict[str, Dict[str, str]] = {
    "es": {
        "hello": "Hola",
        "welcome": "bienvenido",
        "video": "video",
        "subtitle": "subtítulo",
        "translation": "traducción",
        "dubbing": "doblaje",
    },
    "fr": {
        "hello": "Bonjour",
        "welcome": "bienvenue",
        "video": "vidéo",
        "subtitle": "sous-titre",
        "translation": "traduction",
        "dubbing": "doublage",
    },
    "de": {
        "hello": "Hallo",
        "welcome": "willkommen",
        "video": "Video",
        "subtitle": "Untertitel",
        "translation": "Übersetzung",
        "dubbing": "Synchronisation",
    },
    "hi": {
        "hello": "नमस्ते",
        "welcome": "स्वागत हे",
        "video": "वीडियो",
        "subtitle": "उपशीर्षक",
        "translation": "अनुवाद",
        "dubbing": "डबिंग",
    },
    "ko": {
        "hello": "안녕하세요",
        "welcome": "환영합니다",
        "video": "동영상",
        "subtitle": "자막",
        "translation": "번역",
        "dubbing": "더빙",
    },
    "ja": {
        "hello": "こんにちは",
        "welcome": "ようこそ",
        "video": "動画",
        "subtitle": "字幕",
        "translation": "翻訳",
        "dubbing": "吹き替え",
    },
    "pt": {
        "hello": "Olá",
        "welcome": "bem-vindo",
        "video": "vídeo",
        "subtitle": "legenda",
        "translation": "tradução",
        "dubbing": "dublagem",
    },
}


class MockTranslationProvider(BaseTranslationProvider):
    async def translate(
        self,
        segments: List[SubtitleSegment],
        source_language: str,
        target_language: str
    ) -> List[SubtitleSegment]:
        target_name = SUPPORTED_LANGUAGES.get(target_language.lower(), target_language.upper())
        translated_segments: List[SubtitleSegment] = []

        dict_map = MOCK_TRANSLATION_MAP.get(target_language.lower(), {})

        for seg in segments:
            new_seg = copy.deepcopy(seg)
            original = seg.original_text.strip()
            
            # Simple keyword replacement for realistic demo appearance
            words = original.split()
            translated_words = []
            for w in words:
                clean_w = w.lower().strip(",.!?\"'")
                if clean_w in dict_map:
                    translated_words.append(dict_map[clean_w])
                else:
                    translated_words.append(w)

            mock_text = f"[{target_name} Mock] " + " ".join(translated_words)
            new_seg.translated_text = mock_text
            translated_segments.append(new_seg)

        return translated_segments
