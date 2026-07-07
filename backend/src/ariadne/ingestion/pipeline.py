"""Document ingestion pipeline.

The pipeline takes a stored document, parses it, normalizes the text,
chunks it and persists chunks together with page-aware provenance metadata.

Flow:

    Document -> Validation -> Parsing -> Metadata extraction
             -> Normalization -> Chunking -> Chunk persistence
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from ariadne.core.errors import IngestionError
from ariadne.documents.service import DocumentService
from ariadne.documents.storage import DocumentStorage
from ariadne.graph.service import GraphExtractionService
from ariadne.ingestion.chunker import RecursiveChunker
from ariadne.ingestion.parsers.base import ParsedDocument
from ariadne.ingestion.parsers.registry import get_parser
from ariadne.logging import get_logger
from ariadne.models import Chunk, Document
from ariadne.vectors.service import VectorIndexService

logger = get_logger("ingestion.pipeline")


class IngestionPipeline:
    """Orchestrate the transformation of a document into indexed chunks."""

    def __init__(
        self,
        chunker: RecursiveChunker | None = None,
        storage: DocumentStorage | None = None,
        document_service: DocumentService | None = None,
        vector_index: VectorIndexService | None = None,
        graph_service: GraphExtractionService | None = None,
    ) -> None:
        self.chunker = chunker or RecursiveChunker()
        self.storage = storage or DocumentStorage()
        self.documents = document_service or DocumentService(storage=self.storage)
        self.vector_index = vector_index or VectorIndexService()
        self.graph_service = graph_service or GraphExtractionService()

    def ingest(self, session: Session, document_id: str) -> list[Chunk]:
        """Parse, chunk and persist the given document. Returns the chunks."""
        document = self.documents.mark_ingesting(session, document_id)
        session.commit()

        try:
            parsed = self._parse(document)
            chunks = self._chunk(document.id, parsed)
            session.query(Chunk).filter(Chunk.document_id == document.id).delete()
            session.add_all(chunks)
            self.vector_index.reindex_document(session, document.id, chunks)
            self.graph_service.build_document_graph(session, document.id, chunks)
            word_count = sum(len(chunk.text.split()) for chunk in chunks)
            self.documents.mark_ready(
                session,
                document_id,
                title=parsed.title or document.title,
                page_count=parsed.page_count,
                word_count=word_count,
            )
            session.commit()
            logger.info(
                "document ingested",
                extra={"document_id": document.id, "chunks": len(chunks), "words": word_count},
            )
            return chunks
        except Exception as exc:
            session.rollback()
            self.documents.mark_failed(session, document_id, error=str(exc))
            session.commit()
            logger.error(
                "ingestion failed",
                extra={"document_id": document_id, "error": str(exc)},
            )
            raise IngestionError(f"ingestion failed for {document_id}: {exc}") from exc

    def _parse(self, document: Document) -> ParsedDocument:
        data = self.storage.read(document.storage_path)
        parser = get_parser(document.content_type)
        return parser.parse(data)

    def _chunk(self, document_id: str, parsed: ParsedDocument) -> list[Chunk]:
        chunks = self.chunker.chunk_document(parsed, document_id)
        return [
            Chunk(
                document_id=chunk.document_id,
                index=chunk.index,
                text=chunk.text,
                page_numbers=chunk.page_numbers,
                section=chunk.section,
                start_offset=chunk.start_offset,
                end_offset=chunk.end_offset,
                char_count=chunk.char_count,
            )
            for chunk in chunks
        ]

    def chunk_counts(self, session: Session, document_id: str) -> int:
        return session.query(Chunk).filter(Chunk.document_id == document_id).count()

    @staticmethod
    def chunk_to_dict(chunk: Chunk) -> dict:
        """Serialize a chunk for API/vector indexing use."""
        return {
            "id": chunk.id,
            "document_id": chunk.document_id,
            "index": chunk.index,
            "text": chunk.text,
            "page_numbers": list(chunk.page_numbers),
            "section": chunk.section,
            "start_offset": chunk.start_offset,
            "end_offset": chunk.end_offset,
            "char_count": chunk.char_count,
        }
