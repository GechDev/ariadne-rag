"""Conversation persistence service."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from ariadne.core.errors import NotFoundError
from ariadne.logging import get_logger
from ariadne.models import Citation, Conversation, Message

logger = get_logger("conversations.service")


class ConversationService:
    """Create conversations and persist their messages and citations."""

    def get_or_create(self, session: Session, conversation_id: str | None = None) -> Conversation:
        if conversation_id:
            conversation = session.get(Conversation, conversation_id)
            if conversation is None:
                raise NotFoundError(f"conversation not found: {conversation_id}")
            return conversation
        conversation = Conversation(title="New conversation")
        session.add(conversation)
        session.flush()
        return conversation

    def list_conversations(self, session: Session) -> list[Conversation]:
        return list(
            session.scalars(select(Conversation).order_by(Conversation.updated_at.desc()))
        )

    def get(self, session: Session, conversation_id: str) -> Conversation:
        conversation = session.get(Conversation, conversation_id)
        if conversation is None:
            raise NotFoundError(f"conversation not found: {conversation_id}")
        return conversation

    def add_message(
        self,
        session: Session,
        conversation: Conversation,
        role: str,
        content: str,
    ) -> Message:
        message = Message(
            id=str(uuid4()),
            conversation_id=conversation.id,
            role=role,
            content=content,
        )
        session.add(message)
        conversation.updated_at = datetime.now(UTC)
        session.flush()
        return message

    def messages(self, session: Session, conversation_id: str) -> list[Message]:
        return list(
            session.scalars(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at)
            )
        )

    def citations(self, session: Session, message_id: str) -> list[Citation]:
        return list(
            session.scalars(
                select(Citation).where(Citation.message_id == message_id).order_by(Citation.rank)
            )
        )
