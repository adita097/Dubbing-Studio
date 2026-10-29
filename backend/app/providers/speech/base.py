from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, List, Dict


VOICE_OPTIONS: List[Dict[str, str]] = [
    {"id": "alloy", "name": "Alloy (Neutral, Balanced)", "gender": "neutral"},
    {"id": "echo", "name": "Echo (Warm, Confident)", "gender": "male"},
    {"id": "fable", "name": "Fable (Expressive, British)", "gender": "neutral"},
    {"id": "onyx", "name": "Onyx (Deep, Authoritative)", "gender": "male"},
    {"id": "nova", "name": "Nova (Friendly, Energetic)", "gender": "female"},
    {"id": "shimmer", "name": "Shimmer (Clear, Melodic)", "gender": "female"},
]


class BaseSpeechProvider(ABC):
    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice: str,
        output_path: Path,
        language: Optional[str] = None
    ) -> Path:
        """
        Synthesizes given text into an audio file saved at output_path.
        Returns the output Path.
        """
        pass
