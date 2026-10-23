def release_safe_prefix(pending: str, pattern_length: int) -> tuple[str, str]:
    """Split already-scanned text, retaining up to L-1 characters for a literal."""
    if not isinstance(pending, str):
        raise TypeError("pending must be a string")
    if type(pattern_length) is not int:
        raise TypeError("pattern_length must be an integer")
    if pattern_length < 1:
        raise ValueError("pattern_length must be positive")
    release_length = max(0, len(pending) - pattern_length + 1)
    return pending[:release_length], pending[release_length:]


def detect_cross_boundary_pattern(
    previously_held: str, new_content: str, pattern: str
) -> bool:
    """Check for a literal match using characters on both sides of the boundary."""
    if not all(
        isinstance(value, str) for value in (previously_held, new_content, pattern)
    ):
        raise TypeError("held content, new content, and pattern must be strings")
    if not pattern:
        raise ValueError("pattern must not be empty")
    boundary = len(previously_held)
    start = max(0, boundary - len(pattern) + 1)
    index = (previously_held + new_content).find(pattern, start)
    return index >= 0 and index < boundary < index + len(pattern)
