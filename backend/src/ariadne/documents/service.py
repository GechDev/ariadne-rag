"""Document service layer.

Coordinates persistence, storage and validation for uploaded documents.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ariadne.core.errors import ConflictError, NotFoundError
from ariadne.documents.schemas import DocumentDetail
from ariadne.documents.storage import DocumentStorage
from ariadne.documents.validation import infer_content_type, validate_upload_size
from ariadne.logging import get_logger
from ariadne.models import Document, DocumentStatus

logger = get_logger("documents.service")


class DocumentService:
    """Business operations for the document lifecycle."""

    def __init__(self, storage: DocumentStorage | None = None) -> None:
        self.storage = storage or DocumentStorage()

    def create_from_bytes(
        self,
        session: Session,
        *,
        filename: str,
        data: bytes,
        declared_content_type: str | None = None,
    ) -> Document:
        """Validate, store and register an uploaded document."""
        content_type = infer_content_type(filename, declared_content_type)
        validate_upload_size(len(data))
        checksum = self.storage.checksum(data)

        existing = session.scalar(select(Document).where(Document.checksum == checksum))
        if existing is not None:
            raise ConflictError(
                "a document with identical content already exists",
                detail={"document_id": existing.id, "filename": existing.filename},
            )

        storage_key = self.storage.save(data, checksum)
        document = Document(
            filename=filename,
            content_type=content_type,
            size_bytes=len(data),
            checksum=checksum,
            storage_path=storage_key,
            status=DocumentStatus.UPLOADED,
        )
        session.add(document)
        session.flush()
        logger.info(
            "document registered",
            extra={"document_id": document.id, "filename": filename, "size": len(data)},
        )
        return document

    def get(self, session: Session, document_id: str) -> Document:
        document = session.get(Document, document_id)
        if document is None:
            raise NotFoundError(f"document {document_id} not found")
        return document

    def list_documents(
        self, session: Session, *, limit: int = 100, offset: int = 0
    ) -> list[Document]:
        stmt = select(Document).order_by(Document.created_at.desc()).limit(limit).offset(offset)
        return list(session.scalars(stmt))

    def update_metadata(self, session: Session, document_id: str, **fields) -> Document:
        document = self.get(session, document_id)
        for key, value in fields.items():
            if value is not None:
                setattr(document, key, value)
        session.flush()
        return document

    def mark_ingesting(self, session: Session, document_id: str) -> Document:
        document = self.get(session, document_id)
        document.status = DocumentStatus.INGESTING
        session.flush()
        return document

    def mark_ready(self, session: Session, document_id: str, **stats) -> Document:
        document = self.get(session, document_id)
        document.status = DocumentStatus.READY
        for key, value in stats.items():
            if value is not None:
                setattr(document, key, value)
        session.flush()
        return document

    def mark_failed(self, session: Session, document_id: str, error: str) -> Document:
        document = self.get(session, document_id)
        document.status = DocumentStatus.FAILED
        document.error_message = error
        session.flush()
        return document

    def delete(self, session: Session, document_id: str) -> None:
        document = self.get(session, document_id)
        try:
            self.storage.delete(document.storage_path)
        except Exception:  # pragma: no cover - storage is best-effort
            logger.warning(
                "failed to delete stored file",
                extra={"storage_key": document.storage_path},
            )
        session.delete(document)
        session.flush()

    def to_detail(self, document: Document) -> DocumentDetail:
        return DocumentDetail.model_validate(document)
