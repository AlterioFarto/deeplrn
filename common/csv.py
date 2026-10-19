"""CSV export helpers: formula-injection sanitising and streaming responses."""

import csv
from collections.abc import Iterator, Sequence
from typing import Any

from django.http import StreamingHttpResponse


class _StringSink:
    """Minimal file-like sink capturing written CSV fragments."""

    def __init__(self) -> None:
        self.parts: list[str] = []

    def write(self, value: str) -> None:
        self.parts.append(value)


_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def sanitize_cell(value: Any) -> str:
    """Neutralise spreadsheet formula injection in exported cells."""
    text = "" if value is None else str(value)
    if text.startswith(_FORMULA_PREFIXES):
        return f"'{text}"
    return text


def streaming_csv_response(
    *, filename: str, headers: Sequence[str], rows: Iterator[Sequence[Any]]
) -> StreamingHttpResponse:
    """Build a streaming CSV attachment; rows are sanitised on the fly."""

    def generate() -> Iterator[bytes]:
        sink = _StringSink()
        writer = csv.writer(sink)
        writer.writerow(headers)
        yield "".join(sink.parts).encode("utf-8-sig")
        for row in rows:
            sink.parts.clear()
            writer.writerow([sanitize_cell(cell) for cell in row])
            yield "".join(sink.parts).encode("utf-8-sig")

    response = StreamingHttpResponse(generate(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["Cache-Control"] = "no-store"
    return response
