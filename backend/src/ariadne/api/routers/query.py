"""Grounded RAG query endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ariadne.api.deps import get_db
from ariadne.citations.service import SourceReference
from ariadne.conversations.service import ConversationService
from ariadne.logging import get_logger
from ariadne.rag.service import RAGService

router = APIRouter(prefix="/query", tags=["query"])
logger = get_logger("query.api")

Db = Annotated[Session, Depends(get_db)]


class QueryRequest(BaseModel):
    """A question asked against the indexed document corpus."""

    question: str = Field(min_length=1, max_length=2000, description="User question")
    top_k: int = Field(default=6, ge=1, le=50, description="Retrieved passages")
    document_ids: list[str] | None = Field(default=None, description="Scope the search")
    conversation_id: str | None = Field(default=None, description="Continue a conversation")


class QueryCitation(BaseModel):
    """A source reference backing the generated answer."""

    chunk_id: str
    document_id: str
    document_title: str
    index: int
    page_numbers: list[int] = Field(default_factory=list)
    rank: int
    score: float


class QueryResponse(BaseModel):
    """A grounded answer with its supporting citations."""

    conversation_id: str
    message_id: str
    question: str
    answer: str
    grounded: bool
    citations: list[QueryCitation] = Field(default_factory=list)


def _to_citation(reference: SourceReference) -> QueryCitation:
    return QueryCitation(
        chunk_id=reference.chunk_id,
        document_id=reference.document_id,
        document_title=reference.document_title,
        index=reference.index,
        page_numbers=reference.page_numbers,
        rank=reference.rank,
        score=reference.score,
    )


@router.post("", response_model=QueryResponse, summary="Ask a grounded question")
def ask(
    db: Db,
    payload: QueryRequest,
) -> QueryResponse:
    conversations = ConversationService()
    rag = RAGService()

    conversation = conversations.get_or_create(db, payload.conversation_id)
    conversations.add_message(db, conversation, "user", payload.question)

    result = rag.answer(
        db,
        payload.question,
        top_k=payload.top_k,
        document_ids=payload.document_ids,
    )

    assistant = conversations.add_message(db, conversation, "assistant", result.answer)
    rag.citations.persist(db, assistant.id, result.citations)
    db.commit()

    logger.info(
        "query answered",
        extra={
            "conversation_id": conversation.id,
            "grounded": result.grounded,
            "citations": len(result.citations),
        },
    )
    return QueryResponse(
        conversation_id=conversation.id,
        message_id=assistant.id,
        question=result.question,
        answer=result.answer,
        grounded=result.grounded,
        citations=[_to_citation(reference) for reference in result.citations],
    )
