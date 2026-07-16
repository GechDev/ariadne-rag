"""RAG query orchestration.

Binds the retrieval pipeline to grounded generation and citation resolution so
a single ``answer()`` call returns a fully traceable response:

    Question -> Hybrid retrieval -> Citation resolution
             -> Prompt construction -> Generation -> AnswerResult
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from ariadne.citations.service import CitationService, SourceReference
from ariadne.generation.service import GenerationService
from ariadne.retrieval.fusion import RetrievedPassage
from ariadne.retrieval.orchestrator import HybridRetrievalService


@dataclass(slots=True)
class AnswerResult:
    """A complete grounded answer with its supporting sources."""

    question: str
    answer: str
    grounded: bool
    passages: list[RetrievedPassage] = field(default_factory=list)
    citations: list[SourceReference] = field(default_factory=list)


class RAGService:
    """Orchestrate retrieval, citation resolution and generation."""

    def __init__(
        self,
        retrieval: HybridRetrievalService | None = None,
        generation: GenerationService | None = None,
        citations: CitationService | None = None,
    ) -> None:
        self.retrieval = retrieval or HybridRetrievalService()
        self.generation = generation or GenerationService()
        self.citations = citations or CitationService()

    def answer(
        self,
        session: Session,
        question: str,
        *,
        top_k: int | None = None,
        document_ids: list[str] | None = None,
    ) -> AnswerResult:
        """Run the full RAG pipeline for ``question``."""
        passages = self.retrieval.retrieve(
            session, question, top_k=top_k, document_ids=document_ids
        )
        citations = self.citations.resolve(session, passages)
        generated = self.generation.generate(question, passages)
        return AnswerResult(
            question=question,
            answer=generated.answer,
            grounded=generated.grounded,
            passages=passages,
            citations=citations,
        )
