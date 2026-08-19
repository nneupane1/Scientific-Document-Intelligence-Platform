from collections.abc import Iterator
from contextlib import contextmanager


@contextmanager
def span(name: str, **attributes: object) -> Iterator[None]:
    """No-op tracing seam for a future OpenTelemetry adapter."""
    yield
