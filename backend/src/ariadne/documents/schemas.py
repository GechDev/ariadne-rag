"""Pydantic schemas for the document API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ariadne.models.document import DocumentStatus


class DocumentSummary(BaseModel):
    """Lightweight document representation for listings."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    content_type: str
    size_bytes: int
    status: DocumentStatus
    created_at: datetime
    updated_at: datetime


class DocumentDetail(DocumentSummary):
    """Full document metadata representation."""

    checksum: str
    error_message: str | None = None
    title: str | None = None
    page_count: int | None = None
    word_count: int | None = None


class DocumentUpdate(BaseModel):
    """Fields that may be updated on an existing document."""

    title: str | None = Field(default=None, max_length=512)


class UploadResponse(BaseModel):
    """Result of a document upload."""

    document: DocumentDetail
    message: str = "document uploaded"


class DeleteResponse(BaseModel):
    """Result of a document deletion."""

    deleted: bool = True
    id: str
