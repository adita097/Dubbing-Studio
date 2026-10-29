import json
from typing import List
import httpx
from app.providers.translation.base import BaseTranslationProvider, SUPPORTED_LANGUAGES
from app.schemas.subtitle import SubtitleSegment


class OpenAITranslationProvider(BaseTranslationProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        if not api_key:
            raise ValueError("OpenAI API key is required for OpenAITranslationProvider.")
        self.api_key = api_key
        self.model = model
        self.api_url = "https://api.openai.com/v1/chat/completions"

    async def translate(
        self,
        segments: List[SubtitleSegment],
        source_language: str,
        target_language: str
    ) -> List[SubtitleSegment]:
        source_name = SUPPORTED_LANGUAGES.get(source_language.lower(), source_language)
        target_name = SUPPORTED_LANGUAGES.get(target_language.lower(), target_language)

        # Prepare segment input payload
        input_items = [{"id": s.id, "text": s.original_text} for s in segments]

        prompt = f"""You are a professional video dubbing and subtitle translator.
Translate the following subtitle segments from {source_name} to {target_name}.

CRITICAL REQUIREMENTS:
1. Preserve meaning, names, technical terms, numbers, and natural conversational dubbing tone.
2. Return exactly the same number of segments with the exact matching IDs.
3. Do NOT merge, skip, reorder, or invent segments.
4. Output strict JSON with a key "translations" containing an array of objects: [{{"id": <int>, "text": "<translated string>"}}].

Segments to translate:
{json.dumps(input_items, ensure_ascii=False, indent=2)}
"""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a professional audiovisual dubbing and subtitle translator."},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.3
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(self.api_url, headers=headers, json=payload)
                if response.status_code != 200:
                    error_detail = response.text
                    try:
                        err_json = response.json()
                        error_detail = err_json.get("error", {}).get("message", error_detail)
                    except Exception:
                        pass
                    raise RuntimeError(f"OpenAI Translation API error ({response.status_code}): {error_detail}")

                data = response.json()
                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                translations = parsed.get("translations", [])

                # Map translations by id
                trans_map = {item["id"]: item["text"] for item in translations if "id" in item and "text" in item}

                # Construct result
                result: List[SubtitleSegment] = []
                for s in segments:
                    translated_text = trans_map.get(s.id, s.original_text)
                    new_seg = s.model_copy(update={"translated_text": translated_text})
                    result.append(new_seg)

                return result

            except httpx.RequestError as exc:
                raise RuntimeError(f"Network error calling OpenAI Translation API: {str(exc)}")
