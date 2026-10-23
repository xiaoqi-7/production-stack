import json

import pytest

from ext_proc.streaming.holdback import release_safe_prefix
from ext_proc.streaming.logical_stream import LogicalStreamBuffer
from ext_proc.streaming.sse_parser import parse_sse_event, split_sse_events


def test_empty_buffer():
    buffer = LogicalStreamBuffer()
    assert buffer.get() == ""
    assert len(buffer) == 0
    assert buffer.flush_and_clear() == ""


@pytest.mark.parametrize("parts", [
    ["hello"],
    ["hello", " ", "world"],
    ["", "hello", "", " world", ""],
    ["\u4f60", "\u597d", "\U0001f600"],
    ["a"] * 1000,
])
def test_append_preserves_content_and_length(parts):
    buffer = LogicalStreamBuffer()
    for part in parts:
        buffer.append(part)
    expected = "".join(parts)
    assert buffer.get() == expected
    assert buffer.get() == expected
    assert len(buffer) == len(expected)


def test_clear_and_reuse():
    buffer = LogicalStreamBuffer()
    buffer.append("old")
    buffer.clear()
    buffer.clear()
    assert buffer.get() == ""
    assert len(buffer) == 0
    buffer.append("new")
    assert buffer.get() == "new"
    assert len(buffer) == 3


def test_flush_and_clear_and_reuse():
    buffer = LogicalStreamBuffer()
    buffer.append("hello")
    buffer.append(" world")
    assert buffer.flush_and_clear() == "hello world"
    assert buffer.get() == ""
    assert len(buffer) == 0
    assert buffer.flush_and_clear() == ""
    buffer.append("next")
    assert buffer.flush_and_clear() == "next"


def test_buffers_are_independent():
    first = LogicalStreamBuffer()
    second = LogicalStreamBuffer()
    first.append("first")
    second.append("second")
    first.clear()
    assert second.get() == "second"


@pytest.mark.parametrize("invalid", [None, 1, b"text", []])
def test_invalid_append_does_not_change_buffer(invalid):
    buffer = LogicalStreamBuffer()
    buffer.append("kept")
    with pytest.raises(TypeError, match="content must be a string"):
        buffer.append(invalid)
    assert buffer.get() == "kept"
    assert len(buffer) == 4


def test_sse_fragments_accumulate_through_eof():
    contents = ["Hello", "", " ", "\u4e16\u754c"]
    raw = b"".join(
        b"data: " + json.dumps({
            "choices": [{"index": 0, "delta": {"content": content}}],
        }).encode() + b"\r\n\r\n"
        for content in contents
    ) + b"data:[DONE]\r\r"
    buffer = LogicalStreamBuffer()
    remaining = b""
    done = False
    for offset in range(0, len(raw), 7):
        events, remaining = split_sse_events(
            remaining + raw[offset:offset + 7],
            final=offset + 7 >= len(raw),
        )
        for event in events:
            parsed = parse_sse_event(event)
            if parsed is not None:
                done = parsed.get("done", False)
                buffer.append(parsed["delta"]["content"])
    assert done is True
    assert remaining == b""
    assert buffer.flush_and_clear() == "".join(contents)
    assert len(buffer) == 0


@pytest.mark.parametrize("contents, pattern, expected_released", [
    (["safe text: ", "sk-12", "345", "6789"], "sk-123456789", "safe tex"),
    (["safe ", "ab", "c"], "abc", "safe "),
])
def test_literal_is_checked_before_releasing_prefix(contents, pattern, expected_released):
    buffer = LogicalStreamBuffer()
    released = ""
    detected = False
    for content in contents:
        buffer.append(content)
        pending = buffer.get()
        if pattern in pending:
            detected = True
            break
        safe, held = release_safe_prefix(pending, len(pattern))
        released += safe
        buffer.clear()
        buffer.append(held)
    assert detected is True
    assert released == expected_released
    assert pattern in buffer.get()
    assert not any(released.endswith(pattern[:size]) for size in range(1, len(pattern)))


def test_no_match_preserves_text_after_final_check():
    buffer = LogicalStreamBuffer()
    released = ""
    contents = ["hello", " ", "world"]
    pattern = "secret"
    for content in contents:
        buffer.append(content)
        pending = buffer.get()
        assert pattern not in pending
        safe, held = release_safe_prefix(pending, len(pattern))
        released += safe
        buffer.clear()
        buffer.append(held)
    assert pattern not in buffer.get()
    released += buffer.flush_and_clear()
    assert released == "".join(contents)
    assert buffer.get() == ""
