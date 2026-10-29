from pathlib import Path
from typing import Optional
import httpx
from app.providers.speech.base import BaseSpeechProvider


class OpenAISpeechProvider(BaseSpeechProvider):
    def __init__(self, api_key: str, model: str = "tts-1"):
        if not api_key:
            raise ValueError("OpenAI API key is required for OpenAISpeechProvider.")
        self.api_key = api_key
        self.model = model
        self.api_url = "https://api.openai.com/v1/audio/speech"

    async def synthesize(
        self,
        text: str,
        voice: str,
        output_path: Path,
        language: Optional[str] = None
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        target_path = output_path.with_suffix('.mp3')

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        valid_voices = {"alloy", "echo", "fable", "onyx", "nova", "shimmer"}
        selected_voice = voice.lower() if voice.lower() in valid_voices else "alloy"

        payload = {
            "model": self.model,
            "input": text.strip(),
            "voice": selected_voice,
            "response_format": "mp3"
        }

        async with httpx.AsyncClient(timeout=90.0) as client:
            try:
                response = await client.post(self.api_url, headers=headers, json=payload)
                if response.status_code != 200:
                    err_msg = response.text
                    try:
                        err_json = response.json()
                        err_msg = err_json.get("error", {}).get("message", err_msg)
                    except Exception:
                        pass
                    raise RuntimeError(f"OpenAI TTS API error ({response.status_code}): {err_msg}")

                with open(target_path, "wb") as f:
                    f.write(response.content)

                return target_path

            except httpx.RequestError as exc:
                raise RuntimeError(f"Network error calling OpenAI TTS API: {str(exc)}")
