"""Plain-text document parser."""

from __future__ import annotations

from ariadne.ingestion.parsers.base import DocumentParser, ParsedDocument, ParsedPage


class TextParser(DocumentParser):
    """Wrap a raw byte stream of text into a single logical page."""

    def parse(self, data: bytes) -> ParsedDocument:
        text = data.decode("utf-8", errors="replace")
        return ParsedDocument(
            pages=[ParsedPage(page_number=1, text=text)],
            metadata={"format": "text"},
        )
