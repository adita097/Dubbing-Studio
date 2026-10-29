import pytest
from app.services.subtitle_parser import (
    SubtitleParser,
    parse_timestamp_ms,
    clean_subtitle_text,
    format_timestamp_srt,
    format_timestamp_vtt,
)


def test_parse_timestamp_ms():
    assert parse_timestamp_ms("00:00:01,000") == 1000
    assert parse_timestamp_ms("00:01:23.456") == 83456
    assert parse_timestamp_ms("01:30.500") == 90500
    assert parse_timestamp_ms("45.200") == 45200


def test_clean_subtitle_text():
    html = "<b>Hello</b> <i>World</i>! <font color=\"#ff0000\">DubStudio</font>"
    assert clean_subtitle_text(html) == "Hello World! DubStudio"

    vtt_cue = "<v Speaker 1>Welcome to the show."
    assert clean_subtitle_text(vtt_cue) == "Welcome to the show."


def test_parse_valid_srt():
    srt_content = """1
00:00:01,500 --> 00:00:04,200
Hello and welcome to <b>DubStudio</b>.

2
00:00:05,000 --> 00:00:08,750
Today we will translate and dub
this video into Spanish.
"""
    segments = SubtitleParser.parse_srt(srt_content)
    assert len(segments) == 2
    assert segments[0].id == 1
    assert segments[0].start_time_ms == 1500
    assert segments[0].end_time_ms == 4200
    assert segments[0].original_text == "Hello and welcome to DubStudio."

    assert segments[1].id == 2
    assert segments[1].start_time_ms == 5000
    assert segments[1].end_time_ms == 8750
    assert segments[1].original_text == "Today we will translate and dub\nthis video into Spanish."


def test_parse_valid_vtt():
    vtt_content = """WEBVTT - Sample subtitle

1
00:00:01.000 --> 00:00:03.500
First segment of video.

NOTE A comment that should be skipped

00:00:04.000 --> 00:00:07.000
Second segment with <i>italics</i>.
"""
    segments = SubtitleParser.parse_vtt(vtt_content)
    assert len(segments) == 2
    assert segments[0].id == 1
    assert segments[0].start_time_ms == 1000
    assert segments[0].end_time_ms == 3500
    assert segments[0].original_text == "First segment of video."

    assert segments[1].id == 2
    assert segments[1].start_time_ms == 4000
    assert segments[1].end_time_ms == 7000
    assert segments[1].original_text == "Second segment with italics."


def test_parse_plain_text():
    raw_text = """This is paragraph one of the transcript.

This is paragraph two.
It has two lines."""
    segments = SubtitleParser.parse_plain_text(raw_text, mode="paragraph")
    assert len(segments) == 2
    assert segments[0].start_time_ms is None
    assert segments[0].end_time_ms is None
    assert segments[0].original_text == "This is paragraph one of the transcript."
    assert segments[1].original_text == "This is paragraph two.\nIt has two lines."


def test_invalid_srt_timestamp_order():
    invalid_srt = """1
00:00:10,000 --> 00:00:05,000
End time before start time.
"""
    with pytest.raises(ValueError, match="is earlier than start"):
        SubtitleParser.parse_srt(invalid_srt)


def test_empty_srt():
    with pytest.raises(ValueError, match="No valid subtitle segments"):
        SubtitleParser.parse_srt("   \n\n   ")
