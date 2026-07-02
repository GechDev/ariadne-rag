"""Document parser interface and shared value types.

A parser converts raw document bytes into structured, page-aware text that
the ingestion pipeline can normalize and chunk. Parsers must never write to
storage; they are pure transformation functions.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(slots=True)
class ParsedPage:
    """Text extracted from a single document page, with its number."""

    page_number: int
    text: str


@dataclass(slots=True)
class ParsedDocument:
    """Result of parsing a document: ordered pages plus document metadata."""

    pages: list[ParsedPage] = field(default_factory=list)
    title: str | None = None
    metadata: dict = field(default_factory=dict)

    @property
    def page_count(self) -> int:
        return len(self.pages)

    @property
    def full_text(self) -> str:
        return "\n\n".join(page.text for page in self.pages)


class DocumentParser(ABC):
    """Base class for all document parsers."""

    @abstractmethod
    def parse(self, data: bytes) -> ParsedDocument:
        """Parse raw bytes into a :class:`ParsedDocument`."""
        raise NotImplementedError
