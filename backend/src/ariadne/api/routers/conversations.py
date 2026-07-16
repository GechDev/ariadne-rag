"""Conversation history endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ariadne.api.deps import get_db
from ariadne.conversations.service import ConversationService

router = APIRouter(prefix="/conversations", tags=["conversations"])

Db = Annotated[Session, Depends(get_db)]


class ConversationSummary(BaseModel):
    """A conversation list entry."""

    id: str
    title: str
    created_at: str
    updated_at: str


class MessageView(BaseModel):
    """A single conversation message."""

    id: str
    role: str
    content: str
    created_at: str


class CitationView(BaseModel):
    """A citation attached to an assistant message."""

    chunk_id: str
    document_id: str
    document_title: str
    index: int
    page_numbers: list[int] = Field(default_factory=list)
    rank: int
    score: float


class ConversationDetail(BaseModel):
    """A conversation with its full message history."""

    id: str
    title: str
    created_at: str
    updated_at: str
    messages: list[MessageView] = Field(default_factory=list)


@router.get("", response_model=list[ConversationSummary], summary="List conversations")
def list_conversations(db: Db) -> list[ConversationSummary]:
    service = ConversationService()
    return [
        ConversationSummary(
            id=conversation.id,
            title=conversation.title,
            created_at=conversation.created_at.isoformat(),
            updated_at=conversation.updated_at.isoformat(),
        )
        for conversation in service.list_conversations(db)
    ]


@router.get("/{conversation_id}", response_model=ConversationDetail, summary="Get a conversation")
def get_conversation(conversation_id: str, db: Db) -> ConversationDetail:
    service = ConversationService()
    conversation = service.get(db, conversation_id)
    messages = service.messages(db, conversation_id)
    return ConversationDetail(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at.isoformat(),
        updated_at=conversation.updated_at.isoformat(),
        messages=[
            MessageView(
                id=message.id,
                role=message.role,
                content=message.content,
                created_at=message.created_at.isoformat(),
            )
            for message in messages
        ],
    )


@router.get(
    "/{conversation_id}/messages/{message_id}/citations",
    response_model=list[CitationView],
    summary="Get citations for a message",
)
def get_message_citations(conversation_id: str, message_id: str, db: Db) -> list[CitationView]:
    service = ConversationService()
    service.get(db, conversation_id)
    citations = service.citations(db, message_id)
    return [
        CitationView(
            chunk_id=citation.chunk_id,
            document_id=citation.document_id,
            document_title=citation.document_title,
            index=citation.index,
            page_numbers=list(citation.page_numbers),
            rank=citation.rank,
            score=citation.score,
        )
        for citation in citations
    ]
