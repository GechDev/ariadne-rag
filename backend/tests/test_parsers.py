"""Tests for document parsers and the parser registry."""

from __future__ import annotations

import pytest

from ariadne.core.errors import UnsupportedDocumentTypeError
from ariadne.ingestion.parsers.base import DocumentParser, ParsedDocument
from ariadne.ingestion.parsers.pdf import PDFParser
from ariadne.ingestion.parsers.registry import get_parser
from ariadne.ingestion.parsers.text import TextParser


def test_text_parser_decodes_bytes():
    parser = TextParser()
    parsed = parser.parse(b"hello world")
    assert isinstance(parsed, ParsedDocument)
    assert parsed.page_count == 1
    assert parsed.pages[0].text == "hello world"
    assert parsed.metadata == {"format": "text"}


def test_text_parser_replaces_invalid_bytes():
    parser = TextParser()
    parsed = parser.parse(b"\xff\xfehello")
    assert "hello" in parsed.pages[0].text


def test_registry_returns_parser_for_supported_type():
    parser = get_parser("application/pdf")
    assert isinstance(parser, DocumentParser)


def test_registry_aliases_markdown_to_text():
    parser = get_parser("text/markdown")
    assert isinstance(parser, TextParser)


def test_registry_rejects_unknown_type():
    with pytest.raises(UnsupportedDocumentTypeError):
        get_parser("application/x-unknown")


def test_pdf_parser_extracts_pages():
    import io

    from pypdf import PdfWriter

    buffer = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.add_blank_page(width=200, height=200)
    writer.write(buffer)

    parser = PDFParser()
    parsed = parser.parse(buffer.getvalue())
    assert parsed.page_count == 2
    assert [page.page_number for page in parsed.pages] == [1, 2]
    assert parsed.metadata["format"] == "pdf"
