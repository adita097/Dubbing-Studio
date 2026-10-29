import math
import struct
import wave
from pathlib import Path
from typing import Optional
from app.providers.speech.base import BaseSpeechProvider


class MockSpeechProvider(BaseSpeechProvider):
    """
    Generates synthetic offline audio test fixtures using pure standard library (wave & struct).
    Calculates duration based on text length to simulate natural speech timing.
    """
    async def synthesize(
        self,
        text: str,
        voice: str,
        output_path: Path,
        language: Optional[str] = None
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Ensure we write a valid WAV file
        target_path = output_path.with_suffix('.wav')

        # Estimate duration: ~3 words per second, clamp between 1.2s and 10s
        words = len(text.strip().split())
        duration_sec = max(1.2, min(10.0, words * 0.45))

        sample_rate = 24000
        total_samples = int(sample_rate * duration_sec)
        
        # Tone frequency varies slightly by voice
        voice_freqs = {
            "alloy": 350.0,
            "echo": 220.0,
            "fable": 320.0,
            "onyx": 160.0,
            "nova": 440.0,
            "shimmer": 520.0,
        }
        freq = voice_freqs.get(voice.lower(), 400.0)

        with wave.open(str(target_path), 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)

            # Generate modulated sine wave with smooth attack/decay
            frames = bytearray()
            fade_samples = int(sample_rate * 0.05)  # 50ms fade

            for i in range(total_samples):
                # Envelope
                if i < fade_samples:
                    envelope = i / fade_samples
                elif i > total_samples - fade_samples:
                    envelope = (total_samples - i) / fade_samples
                else:
                    envelope = 1.0

                # Subtle frequency modulation for pleasant tone
                mod = math.sin(2.0 * math.pi * 3.0 * (i / sample_rate)) * 15.0
                sample_val = math.sin(2.0 * math.pi * (freq + mod) * (i / sample_rate))
                # 16-bit signed integer amplitude
                int_sample = int(sample_val * envelope * 16000)
                frames.extend(struct.pack('<h', int_sample))

            wav_file.writeframes(frames)

        return target_path
