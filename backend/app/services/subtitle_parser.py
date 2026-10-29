import re
from typing import List, Optional, Tuple
from app.schemas.subtitle import SubtitleSegment


def clean_subtitle_text(text: str) -> str:
    """Removes HTML formatting tags, VTT cue formatting, and normalizes whitespace."""
    # Remove HTML tags (e.g. <b>, <i>, <u>, <font ...>, </font>)
    cleaned = re.sub(r'<[^>]+>', '', text)
    # Remove VTT speaker tags like <v Speaker> or other cue tags
    cleaned = re.sub(r'<v\s+[^>]+>', '', cleaned)
    # Normalize multiple spaces within a line while preserving intentional line breaks
    lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in cleaned.splitlines()]
    # Rejoin non-empty lines
    return "\n".join([line for line in lines if line])


def parse_timestamp_ms(ts_str: str) -> int:
    """
    Parses timestamp string into milliseconds.
    Supports:
      - 00:01:23,456 or 00:01:23.456 (HH:MM:SS,mmm or HH:MM:SS.mmm)
      - 01:23.456 (MM:SS.mmm)
      - 23.456 (SS.mmm)
    """
    ts_str = ts_str.strip().replace(',', '.')
    parts = ts_str.split(':')
    
    if len(parts) == 3:
        # HH:MM:SS.mmm
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds_parts = parts[2].split('.')
        seconds = int(seconds_parts[0])
        millis = int(seconds_parts[1].ljust(3, '0')[:3]) if len(seconds_parts) > 1 else 0
        return ((hours * 3600) + (minutes * 60) + seconds) * 1000 + millis
    elif len(parts) == 2:
        # MM:SS.mmm
        minutes = int(parts[0])
        seconds_parts = parts[1].split('.')
        seconds = int(seconds_parts[0])
        millis = int(seconds_parts[1].ljust(3, '0')[:3]) if len(seconds_parts) > 1 else 0
        return ((minutes * 60) + seconds) * 1000 + millis
    elif len(parts) == 1:
        # SS.mmm
        seconds_parts = parts[0].split('.')
        seconds = int(seconds_parts[0])
        millis = int(seconds_parts[1].ljust(3, '0')[:3]) if len(seconds_parts) > 1 else 0
        return seconds * 1000 + millis
    else:
        raise ValueError(f"Unrecognized timestamp format: '{ts_str}'")


def format_timestamp_srt(ms: int) -> str:
    """Formats milliseconds to SRT timestamp: HH:MM:SS,mmm"""
    total_sec = max(0, ms) // 1000
    millis = max(0, ms) % 1000
    hours = total_sec // 3600
    minutes = (total_sec % 3600) // 60
    seconds = total_sec % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def format_timestamp_vtt(ms: int) -> str:
    """Formats milliseconds to WebVTT timestamp: HH:MM:SS.mmm"""
    total_sec = max(0, ms) // 1000
    millis = max(0, ms) % 1000
    hours = total_sec // 3600
    minutes = (total_sec % 3600) // 60
    seconds = total_sec % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"


class SubtitleParser:
    TIMESTAMP_ARROW_REGEX = re.compile(r'(\d+:\d+(?::\d+)?(?:[,\.]\d+)?)\s*-->\s*(\d+:\d+(?::\d+)?(?:[,\.]\d+)?)')

    @classmethod
    def parse_srt(cls, content: str) -> List[SubtitleSegment]:
        """
        Parses SRT subtitle text into SubtitleSegment objects.
        Validates timestamps and removes HTML tags while preserving line order.
        """
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        # Split blocks by double or multiple newlines
        blocks = re.split(r'\n\s*\n', content.strip())
        segments: List[SubtitleSegment] = []
        seg_id = 1

        for block in blocks:
            lines = [l.strip() for l in block.strip().splitlines() if l.strip()]
            if not lines:
                continue

            # Find line with timestamp arrow '-->'
            arrow_idx = -1
            match = None
            for idx, line in enumerate(lines):
                m = cls.TIMESTAMP_ARROW_REGEX.search(line)
                if m:
                    arrow_idx = idx
                    match = m
                    break

            if arrow_idx == -1 or not match:
                # Malformed block or comment; if file has no valid timestamps, raise helpful error
                continue

            start_str, end_str = match.group(1), match.group(2)
            try:
                start_ms = parse_timestamp_ms(start_str)
                end_ms = parse_timestamp_ms(end_str)
            except Exception as e:
                raise ValueError(f"Invalid timestamp in segment {seg_id}: {e}")

            if end_ms < start_ms:
                raise ValueError(f"Segment {seg_id}: End timestamp ({end_str}) is earlier than start timestamp ({start_str})")

            # Lines after timestamp line are text
            text_lines = lines[arrow_idx + 1:]
            raw_text = "\n".join(text_lines)
            cleaned = clean_subtitle_text(raw_text)

            if not cleaned:
                continue

            segments.append(SubtitleSegment(
                id=seg_id,
                start_time_ms=start_ms,
                end_time_ms=end_ms,
                original_text=cleaned,
                translated_text=None
            ))
            seg_id += 1

        if not segments:
            raise ValueError("No valid subtitle segments found in the SRT file.")

        return segments

    @classmethod
    def parse_vtt(cls, content: str) -> List[SubtitleSegment]:
        """
        Parses WebVTT subtitle text into SubtitleSegment objects.
        """
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        lines = content.splitlines()

        # Check for WEBVTT header
        header_found = False
        start_idx = 0
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("WEBVTT"):
                header_found = True
                start_idx = idx + 1
                break
            elif stripped:
                # If first non-empty line isn't WEBVTT, check if it's still parsable
                break

        # Re-join remainder
        body = "\n".join(lines[start_idx:])
        blocks = re.split(r'\n\s*\n', body.strip())
        segments: List[SubtitleSegment] = []
        seg_id = 1

        for block in blocks:
            block_lines = [l.strip() for l in block.strip().splitlines() if l.strip()]
            if not block_lines:
                continue

            # Ignore WEBVTT metadata/comments (NOTE, STYLE, REGION)
            if block_lines[0].startswith("NOTE") or block_lines[0].startswith("STYLE") or block_lines[0].startswith("REGION"):
                continue

            arrow_idx = -1
            match = None
            for idx, line in enumerate(block_lines):
                m = cls.TIMESTAMP_ARROW_REGEX.search(line)
                if m:
                    arrow_idx = idx
                    match = m
                    break

            if arrow_idx == -1 or not match:
                continue

            start_str, end_str = match.group(1), match.group(2)
            try:
                start_ms = parse_timestamp_ms(start_str)
                end_ms = parse_timestamp_ms(end_str)
            except Exception as e:
                raise ValueError(f"Invalid timestamp in VTT cue {seg_id}: {e}")

            if end_ms < start_ms:
                raise ValueError(f"Cue {seg_id}: End timestamp ({end_str}) is earlier than start ({start_str})")

            text_lines = block_lines[arrow_idx + 1:]
            raw_text = "\n".join(text_lines)
            cleaned = clean_subtitle_text(raw_text)

            if not cleaned:
                continue

            segments.append(SubtitleSegment(
                id=seg_id,
                start_time_ms=start_ms,
                end_time_ms=end_ms,
                original_text=cleaned,
                translated_text=None
            ))
            seg_id += 1

        if not segments:
            raise ValueError("No valid subtitle cues found in the WebVTT file.")

        return segments

    @classmethod
    def parse_plain_text(cls, text: str, mode: str = "paragraph") -> List[SubtitleSegment]:
        """
        Parses pasted plain text into untimed SubtitleSegment list.
        mode can be 'paragraph', 'line', or 'sentence'.
        """
        text = text.replace('\r\n', '\n').replace('\r', '\n').strip()
        if not text:
            raise ValueError("Transcript text cannot be empty.")

        raw_segments: List[str] = []
        if mode == "line":
            raw_segments = [l.strip() for l in text.split('\n') if l.strip()]
        elif mode == "sentence":
            # Split by period, exclamation, question mark followed by space or newline
            sentences = re.split(r'(?<=[.!?])\s+', text)
            raw_segments = [s.strip() for s in sentences if s.strip()]
        else:
            # Paragraph mode (default)
            paragraphs = re.split(r'\n\s*\n', text)
            raw_segments = [p.strip() for p in paragraphs if p.strip()]

        segments: List[SubtitleSegment] = []
        for idx, seg_text in enumerate(raw_segments, start=1):
            cleaned = clean_subtitle_text(seg_text)
            if cleaned:
                segments.append(SubtitleSegment(
                    id=idx,
                    start_time_ms=None,
                    end_time_ms=None,
                    original_text=cleaned,
                    translated_text=None
                ))

        if not segments:
            raise ValueError("No valid content found in plain text transcript.")

        return segments

    @classmethod
    def segments_to_srt(cls, segments: List[SubtitleSegment], use_translated: bool = True) -> str:
        """Serializes segments back to SRT format."""
        out = []
        for idx, seg in enumerate(segments, start=1):
            text = (seg.translated_text if (use_translated and seg.translated_text) else seg.original_text)
            start_ms = seg.start_time_ms if seg.start_time_ms is not None else (idx - 1) * 3000
            end_ms = seg.end_time_ms if seg.end_time_ms is not None else start_ms + 2500
            out.append(f"{idx}\n{format_timestamp_srt(start_ms)} --> {format_timestamp_srt(end_ms)}\n{text}\n")
        return "\n".join(out)
