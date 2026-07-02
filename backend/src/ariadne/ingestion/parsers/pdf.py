"""PDF document parser backed by pypdf."""

from __future__ import annotations

from ariadne.core.errors import IngestionError
from ariadne.ingestion.parsers.base import DocumentParser, ParsedDocument, ParsedPage
from ariadne.logging import get_logger

logger = get_logger("ingestion.parsers.pdf")


class PDFParser(DocumentParser):
    """Extract page-oriented text from a PDF byte stream."""

    def parse(self, data: bytes) -> ParsedDocument:
        import io

        from pypdf import PdfReader
        from pypdf.errors import PdfReadError

        try:
            reader = PdfReader(io.BytesIO(data))
        except (PdfReadError, ValueError) as exc:
            logger.warning("failed to read PDF", extra={"error": str(exc)})
            raise IngestionError(f"invalid PDF document: {exc}") from exc

        pages: list[ParsedPage] = []
        for index, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            pages.append(ParsedPage(page_number=index, text=text))

        title: str | None = None
        if reader.metadata is not None and reader.metadata.title:
            title = reader.metadata.title

        logger.info(
            "parsed PDF",
            extra={
                "pages": len(pages),
                "title": title,
                "producer": getattr(reader.metadata, "producer", None),
            },
        )
        return ParsedDocument(pages=pages, title=title, metadata={"format": "pdf"})
