import os
import wave
import struct
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from app.core.config import settings
from app.schemas.subtitle import SubtitleSegment
from app.providers.speech.base import BaseSpeechProvider, VOICE_OPTIONS
from app.providers.speech.mock_provider import MockSpeechProvider
from app.providers.speech.openai_provider import OpenAISpeechProvider
from app.storage.local_storage import storage


def get_audio_duration_ms(file_path: Path) -> int:
    """Gets duration of WAV or MP3 audio file in milliseconds."""
    if file_path.suffix.lower() == '.wav':
        try:
            with wave.open(str(file_path), 'rb') as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                if rate > 0:
                    return int((frames / float(rate)) * 1000)
        except Exception:
            pass

    # Fallback estimation if wave fails (e.g. mp3 without ffprobe)
    size = file_path.stat().st_size
    # Assume 128kbps = 16000 bytes/sec
    return int((size / 16000) * 1000)


def create_silence_wav(output_path: Path, duration_ms: int, sample_rate: int = 24000) -> Path:
    """Creates a silence WAV file of specific duration in milliseconds."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    num_samples = int(sample_rate * (duration_ms / 1000.0))
    with wave.open(str(output_path), 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        # 16-bit zeros
        wf.writeframes(b'\x00\x00' * num_samples)
    return output_path


class SpeechService:
    def __init__(self, provider: Optional[BaseSpeechProvider] = None):
        self._provider = provider

    def get_provider(self) -> BaseSpeechProvider:
        if self._provider:
            return self._provider

        if settings.MOCK_AI_MODE or settings.SPEECH_PROVIDER.lower() == "mock":
            return MockSpeechProvider()

        api_key = settings.SPEECH_API_KEY or settings.OPENAI_API_KEY
        if not api_key:
            raise ValueError("No API key configured for speech provider. Enable MOCK_AI_MODE or set OPENAI_API_KEY.")
        return OpenAISpeechProvider(api_key=api_key)

    async def generate_voiceover_for_project(
        self,
        project_id: str,
        segments: List[SubtitleSegment],
        voice_id: str = "alloy",
        target_language: Optional[str] = None
    ) -> Tuple[List[SubtitleSegment], Path, Dict[str, Any]]:
        """
        Synthesizes speech for each segment and arranges them into a consolidated voiceover track.
        Returns:
            - updated_segments (with audio_asset paths)
            - full_voiceover_path
            - metadata (duration_ms, timing_warnings, is_timed)
        """
        provider = self.get_provider()
        updated_segments: List[SubtitleSegment] = []
        segment_audio_files: List[Tuple[SubtitleSegment, Path, int]] = []

        # 1. Synthesize each segment
        for seg in segments:
            text_to_speak = seg.translated_text or seg.original_text
            seg_out = storage.get_segment_voiceover_path(project_id, seg.id)
            audio_path = await provider.synthesize(
                text=text_to_speak,
                voice=voice_id,
                output_path=seg_out,
                language=target_language
            )
            seg_duration = get_audio_duration_ms(audio_path)
            
            new_seg = seg.model_copy(update={"audio_asset": str(audio_path.relative_to(settings.base_storage_path))})
            updated_segments.append(new_seg)
            segment_audio_files.append((new_seg, audio_path, seg_duration))

        # 2. Check timing & overflow
        is_timed = any(s.is_timed for s in segments)
        warnings: List[str] = []

        if is_timed:
            for i in range(len(segment_audio_files) - 1):
                cur_seg, _, cur_dur = segment_audio_files[i]
                next_seg, _, _ = segment_audio_files[i + 1]
                if cur_seg.start_time_ms is not None and next_seg.start_time_ms is not None:
                    expected_end = cur_seg.start_time_ms + cur_dur
                    if expected_end > next_seg.start_time_ms:
                        overflow = expected_end - next_seg.start_time_ms
                        warnings.append(
                            f"Segment {cur_seg.id} speech ({cur_dur}ms) extends {overflow}ms into Segment {next_seg.id} start."
                        )

        # 3. Assemble timeline into single master voiceover file
        # Using pure Python WAV concatenation for robust zero-dependency offline rendering
        full_voiceover_path = storage.get_voiceover_path(project_id, ext="wav")
        sample_rate = 24000
        total_audio_frames = bytearray()
        current_timeline_ms = 0

        for idx, (seg, audio_file, dur_ms) in enumerate(segment_audio_files):
            target_start_ms = seg.start_time_ms if (is_timed and seg.start_time_ms is not None) else current_timeline_ms

            # If there's a gap before this segment, insert silence
            if target_start_ms > current_timeline_ms:
                gap_ms = target_start_ms - current_timeline_ms
                gap_samples = int(sample_rate * (gap_ms / 1000.0))
                total_audio_frames.extend(b'\x00\x00' * gap_samples)
                current_timeline_ms = target_start_ms

            # Append segment audio data
            try:
                if audio_file.suffix.lower() == '.wav':
                    with wave.open(str(audio_file), 'rb') as wf:
                        data = wf.readframes(wf.getnframes())
                        total_audio_frames.extend(data)
                else:
                    # In case of non-wav files (e.g. mp3 in live OpenAI), we write a placeholder or let FFmpeg assemble
                    # For wav files, byte manipulation is direct and instantaneous
                    data = audio_file.read_bytes()
                    total_audio_frames.extend(data)
            except Exception:
                pass

            current_timeline_ms += dur_ms
            # Add small gap for untimed sequential segments
            if not is_timed and idx < len(segment_audio_files) - 1:
                silence_gap_ms = 350
                gap_samples = int(sample_rate * (silence_gap_ms / 1000.0))
                total_audio_frames.extend(b'\x00\x00' * gap_samples)
                current_timeline_ms += silence_gap_ms

        # Write consolidated WAV file
        with wave.open(str(full_voiceover_path), 'wb') as out_wf:
            out_wf.setnchannels(1)
            out_wf.setsampwidth(2)
            out_wf.setframerate(sample_rate)
            out_wf.writeframes(total_audio_frames)

        metadata = {
            "duration_ms": current_timeline_ms,
            "timing_warnings": warnings,
            "is_timed": is_timed,
            "voice_id": voice_id
        }

        return updated_segments, full_voiceover_path, metadata


speech_service = SpeechService()
