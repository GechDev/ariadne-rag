"""SQLAlchemy ORM models for ARIADNE.

Importing this package registers every model on the shared metadata so that
``Base.metadata.create_all`` knows about the full schema.
"""

from __future__ import annotations

from ariadne.models.chunk import Chunk
from ariadne.models.conversation import Citation, Conversation, Message
from ariadne.models.document import Document, DocumentStatus
from ariadne.models.graph import GraphEntity, GraphRelationship
from ariadne.models.vector_entry import VectorEntry

__all__ = [
    "Chunk",
    "Citation",
    "Conversation",
    "Document",
    "DocumentStatus",
    "GraphEntity",
    "GraphRelationship",
    "Message",
    "VectorEntry",
]
