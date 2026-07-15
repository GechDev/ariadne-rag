"""Citation resolution and persistence.

A generated answer is backed by a ranked list of retrieved passages. The
citation service turns those passages into traceable source references —
document, page, chunk and rank — so every claim can be verified against the
original material, and persists them alongside the assistant message that
used them.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from ariadne.logging import get_logger
from ariadne.models import Citation, Document
from ariadne.retrieval.fusion import RetrievedPassage

logger = get_logger("citations.service")


@dataclass(slots=True)
class SourceReference:
    """A single traceable source backing part of an answer."""

    chunk_id: str
    document_id: str
    document_title: str
    index: int
    page_numbers: list[int] = field(default_factory=list)
    rank: int = 0
    score: float = 0.0


class CitationService:
    """Resolve retrieved passages into document-backed citations."""

    def resolve(
        self, session: Session, passages: list[RetrievedPassage]
    ) -> list[SourceReference]:
        """Build ordered source references for the given passages."""
        if not passages:
            return []

        document_ids = {passage.document_id for passage in passages}
        documents = session.scalars(select(Document).where(Document.id.in_(document_ids))).all()
        titles = {document.id: document.filename for document in documents}

        references: list[SourceReference] = []
        for rank, passage in enumerate(passages, start=1):
            references.append(
                SourceReference(
                    chunk_id=passage.chunk_id,
                    document_id=passage.document_id,
                    document_title=titles.get(passage.document_id, "Unknown source"),
                    index=passage.index,
                    page_numbers=list(passage.page_numbers),
                    rank=rank,
                    score=passage.score,
                )
            )
        return references

    def persist(
        self,
        session: Session,
        message_id: str,
        references: list[SourceReference],
    ) -> int:
        """Persist citations linked to ``message_id``. Returns rows written."""
        for reference in references:
            session.add(
                Citation(
                    message_id=message_id,
                    chunk_id=reference.chunk_id,
                    document_id=reference.document_id,
                    document_title=reference.document_title,
                    index=reference.index,
                    page_numbers=reference.page_numbers,
                    score=reference.score,
                    rank=reference.rank,
                )
            )
        session.flush()
        logger.info(
            "citations persisted",
            extra={"message_id": message_id, "count": len(references)},
        )
        return len(references)
