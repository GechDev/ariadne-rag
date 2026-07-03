"""Tests for the recursive text chunker."""

from __future__ import annotations

from ariadne.ingestion.chunker import RecursiveChunker, TextChunk
from ariadne.ingestion.parsers.base import ParsedDocument, ParsedPage


def test_long_text_is_split_into_multiple_chunks():
    text = "word " * 5000
    chunker = RecursiveChunker(chunk_size=1000, overlap=100)
    chunks = chunker.chunk_document(
        ParsedDocument(pages=[ParsedPage(page_number=1, text=text)]), "doc-1"
    )
    assert len(chunks) > 1
    assert all(isinstance(chunk, TextChunk) for chunk in chunks)
    assert all(chunk.page_numbers == [1] for chunk in chunks)


def test_short_text_produces_single_chunk():
    chunker = RecursiveChunker()
    chunks = chunker.chunk_document(
        ParsedDocument(pages=[ParsedPage(page_number=1, text="short text")]), "doc-1"
    )
    assert len(chunks) == 1
    assert chunks[0].text == "short text"


def test_pages_are_preserved_across_chunks():
    chunker = RecursiveChunker(chunk_size=500, overlap=50)
    parsed = ParsedDocument(
        pages=[
            ParsedPage(page_number=1, text="a" * 3000),
            ParsedPage(page_number=2, text="b" * 3000),
        ]
    )
    chunks = chunker.chunk_document(parsed, "doc-1")
    assert any(chunk.page_numbers == [1] for chunk in chunks)
    assert any(chunk.page_numbers == [2] for chunk in chunks)


def test_chunks_carry_offset_metadata():
    text = "The quick brown fox jumps over the lazy dog. " * 100
    chunker = RecursiveChunker(chunk_size=600, overlap=100)
    chunks = chunker.chunk_document(
        ParsedDocument(pages=[ParsedPage(page_number=1, text=text)]), "doc-1"
    )
    for chunk in chunks:
        assert chunk.end_offset > chunk.start_offset
        assert chunk.char_count == len(chunk.text)
    # Overlapping chunks should share some characters.
    assert chunks[0].end_offset > chunks[1].start_offset


def test_empty_document_produces_placeholder_chunk():
    chunker = RecursiveChunker()
    chunks = chunker.chunk_document(ParsedDocument(), "doc-1")
    assert len(chunks) == 1
    assert chunks[0].text == ""


def test_invalid_chunker_parameters_raise():
    import pytest

    with pytest.raises(ValueError):
        RecursiveChunker(chunk_size=100, overlap=200)


def test_whitespace_is_normalized_before_chunking():
    chunker = RecursiveChunker()
    parsed = ParsedDocument(pages=[ParsedPage(page_number=1, text="  hello\u00a0 world  \n\n\n  ")])
    chunks = chunker.chunk_document(parsed, "doc-1")
    assert chunks[0].text == "hello world"
