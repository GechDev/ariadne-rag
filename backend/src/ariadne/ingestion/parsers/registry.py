"""Parser registry mapping document content types to parser instances."""

from __future__ import annotations

from ariadne.core.errors import UnsupportedDocumentTypeError
from ariadne.ingestion.parsers.base import DocumentParser
from ariadne.ingestion.parsers.pdf import PDFParser
from ariadne.ingestion.parsers.text import TextParser

_PARSERS: dict[str, DocumentParser] = {
    "application/pdf": PDFParser(),
    "text/plain": TextParser(),
    "text/markdown": TextParser(),
    "text/x-rst": TextParser(),
    "text/html": TextParser(),
}

# Aliases that can be handled by an existing parser.
_ALIASES: dict[str, str] = {
    "text/markdown": "text/plain",
    "text/x-rst": "text/plain",
    "text/html": "text/plain",
}


def get_parser(content_type: str) -> DocumentParser:
    """Return a parser for the given content type or raise."""
    effective = _ALIASES.get(content_type, content_type)
    parser = _PARSERS.get(effective)
    if parser is None:
        raise UnsupportedDocumentTypeError(
            f"no parser registered for content type {content_type!r}",
            detail={"supported": sorted(_PARSERS)},
        )
    return parser


def registered_content_types() -> list[str]:
    """Return the list of content types that have a parser."""
    return sorted(_PARSERS)
