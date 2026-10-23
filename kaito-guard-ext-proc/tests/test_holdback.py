from itertools import product

import pytest

from ext_proc.streaming.holdback import (
    detect_cross_boundary_pattern,
    release_safe_prefix,
)


@pytest.mark.parametrize("pending, length, expected", [
    ("", 1, ("", "")),
    ("", 12, ("", "")),
    ("abc", 1, ("abc", "")),
    ("abc", 3, ("a", "bc")),
    ("abc", 4, ("", "abc")),
    ("abc", 12, ("", "abc")),
    ("abcdef", 3, ("abcd", "ef")),
    ("prefix sk-12", 12, ("p", "refix sk-12")),
    ("\u4f60\u597d\U0001f600", 2, ("\u4f60\u597d", "\U0001f600")),
])
def test_release_prefix(pending, length, expected):
    assert release_safe_prefix(pending, length) == expected


def test_holdback_length_and_reconstruction():
    for size, length in product(range(20), range(1, 25)):
        pending = "x" * size
        safe, held = release_safe_prefix(pending, length)
        assert safe + held == pending
        assert len(held) == min(size, length - 1)
        assert len(safe) == max(0, size - length + 1)


@pytest.mark.parametrize("length", [0, -1, -12])
def test_nonpositive_pattern_length_is_rejected(length):
    with pytest.raises(ValueError, match="positive"):
        release_safe_prefix("text", length)


@pytest.mark.parametrize("length", [None, True, False, 1.5, "3"])
def test_invalid_pattern_length_type_is_rejected(length):
    with pytest.raises(TypeError, match="integer"):
        release_safe_prefix("text", length)


def test_pending_must_be_text():
    with pytest.raises(TypeError, match="pending must be a string"):
        release_safe_prefix(b"text", 3)


@pytest.mark.parametrize("held, new, pattern, expected", [
    ("sk-12", "3456789", "sk-123456789", True),
    ("ab", "c", "abc", True),
    ("abc", "def", "abc", False),
    ("abc", "def", "def", False),
    ("a", "bc", "missing", False),
    ("", "abc", "abc", False),
    ("abc", "", "abc", False),
    ("a", "a", "a", False),
    ("abcab", "c", "abc", True),
    ("aaaa", "a", "aaa", True),
    ("a\u4f60", "\u597db", "\u4f60\u597d", True),
])
def test_detect_only_matches_crossing_the_boundary(held, new, pattern, expected):
    assert detect_cross_boundary_pattern(held, new, pattern) is expected


def test_empty_pattern_is_rejected():
    with pytest.raises(ValueError, match="must not be empty"):
        detect_cross_boundary_pattern("held", "new", "")


@pytest.mark.parametrize("held, new, pattern", [
    (None, "new", "pattern"),
    ("held", b"new", "pattern"),
    ("held", "new", 1),
])
def test_boundary_detection_requires_text(held, new, pattern):
    with pytest.raises(TypeError, match="must be strings"):
        detect_cross_boundary_pattern(held, new, pattern)


@pytest.mark.parametrize("pattern", ["abc", "sk-123456789", "\u4f60\u597d\U0001f600"])
def test_every_literal_split_is_retained_and_detected(pattern):
    prefix = "safe text: "
    for split in range(1, len(pattern)):
        pending = prefix + pattern[:split]
        assert pattern not in pending
        safe, held = release_safe_prefix(pending, len(pattern))
        assert prefix.startswith(safe)
        assert detect_cross_boundary_pattern(held, pattern[split:], pattern) is True
        assert pattern in held + pattern[split:]


def test_boundary_detection_matches_exhaustive_reference():
    texts = [
        "".join(characters)
        for size in range(4)
        for characters in product("ab", repeat=size)
    ]
    patterns = [pattern for pattern in texts if pattern]
    for held, new, pattern in product(texts, texts, patterns):
        combined = held + new
        boundary = len(held)
        expected = any(
            combined.startswith(pattern, index)
            and index < boundary < index + len(pattern)
            for index in range(len(combined))
        )
        assert detect_cross_boundary_pattern(held, new, pattern) is expected
