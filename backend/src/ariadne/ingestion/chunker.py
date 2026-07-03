"""Recursive text chunking with page metadata preservation.

The chunker splits a page-aware parsed document into overlapping chunks.
Each chunk records the page(s) it came from and its character offsets so
that downstream citation logic can trace a passage back to its source.
"""

from __future__ import annotations

from dataclasses import dataclass

from ariadne.ingestion.normalizer import normalize_text
from ariadne.ingestion.parsers.base import ParsedDocument


@dataclass(slots=True)
class TextChunk:
    """A single chunk of normalized text with source provenance."""

    document_id: str
    text: str
    page_numbers: list[int]
    section: str | None = None
    start_offset: int = 0
    end_offset: int = 0
    char_count: int = 0
    index: int = 0


_SEPARATORS = ["\n\n", "\n", ". ", " "]


class RecursiveChunker:
    """Chunk text by splitting on descending-sized separators."""

    def __init__(self, chunk_size: int = 1200, overlap: int = 200) -> None:
        if overlap >= chunk_size:
            raise ValueError("overlap must be smaller than chunk_size")
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_document(self, parsed: ParsedDocument, document_id: str) -> list[TextChunk]:
        """Chunk an entire parsed document, preserving page boundaries."""
        chunks: list[TextChunk] = []
        index = 0
        global_offset = 0

        for page in parsed.pages:
            normalized = normalize_text(page.text)
            if not normalized:
                continue
            page_chunks = self._split_text(normalized)
            for piece in page_chunks:
                start = global_offset + piece["offset"]
                end = start + len(piece["text"])
                chunks.append(
                    TextChunk(
                        document_id=document_id,
                        text=piece["text"],
                        page_numbers=[page.page_number],
                        start_offset=start,
                        end_offset=end,
                        char_count=len(piece["text"]),
                        index=index,
                    )
                )
                index += 1
            global_offset += len(normalized) + 2  # account for page separator

        if not chunks:
            chunks.append(
                TextChunk(
                    document_id=document_id,
                    text="",
                    page_numbers=[page.page_number for page in parsed.pages] or [1],
                    char_count=0,
                )
            )
        return chunks

    def _split_text(self, text: str) -> list[dict]:
        """Split a single block of text into overlapping pieces."""
        pieces: list[dict] = []
        start = 0
        length = len(text)

        while start < length:
            end = (
                length
                if length - start <= self.chunk_size
                else self._find_split(text, start)
            )
            if end <= start:
                end = min(start + self.chunk_size, length)

            pieces.append({"text": text[start:end], "offset": start})

            if end >= length:
                break
            start = max(start, end - self.overlap)

        return pieces

    def _find_split(self, text: str, start: int) -> int:
        """Find the best separator within the chunk window."""
        window_end = start + self.chunk_size
        target = window_end
        for sep in _SEPARATORS:
            idx = text.rfind(sep, start + 1, window_end)
            if idx != -1 and idx > start:
                target = idx + len(sep)
                break
        return min(target, window_end)
