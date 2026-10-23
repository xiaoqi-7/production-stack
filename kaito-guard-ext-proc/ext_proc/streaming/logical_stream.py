class LogicalStreamBuffer:
    """Accumulate decoded content fragments without SSE framing."""

    def __init__(self) -> None:
        self._parts: list[str] = []
        self._length = 0

    def append(self, content: str) -> None:
        if not isinstance(content, str):
            raise TypeError("content must be a string")
        if content:
            self._parts.append(content)
            self._length += len(content)

    def get(self) -> str:
        return "".join(self._parts)

    def clear(self) -> None:
        self._parts.clear()
        self._length = 0

    def flush_and_clear(self) -> str:
        content = self.get()
        self.clear()
        return content

    def __len__(self) -> int:
        return self._length
