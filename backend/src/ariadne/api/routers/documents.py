"""Document management endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.orm import Session

from ariadne.api.deps import get_db
from ariadne.documents.schemas import (
    DeleteResponse,
    DocumentDetail,
    DocumentSummary,
    DocumentUpdate,
    UploadResponse,
)
from ariadne.documents.service import DocumentService
from ariadne.ingestion.pipeline import IngestionPipeline
from ariadne.logging import get_logger
from ariadne.models import Chunk

router = APIRouter(prefix="/documents", tags=["documents"])
logger = get_logger("documents.api")

Db = Annotated[Session, Depends(get_db)]
Service = Annotated[DocumentService, Depends(lambda: DocumentService())]


@router.post("", status_code=201, response_model=UploadResponse, summary="Upload a document")
async def upload_document(
    db: Db,
    service: Service,
    file: UploadFile = File(...),
    content_type: str | None = Form(default=None),
) -> UploadResponse:
    data = await file.read()
    document = service.create_from_bytes(
        db,
        filename=file.filename or "unnamed",
        data=data,
        declared_content_type=content_type,
    )
    return UploadResponse(document=service.to_detail(document))


@router.get("", response_model=list[DocumentSummary], summary="List documents")
def list_documents(
    db: Db,
    service: Service,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[DocumentSummary]:
    documents = service.list_documents(db, limit=limit, offset=offset)
    return [DocumentSummary.model_validate(doc) for doc in documents]


@router.post("/{document_id}/ingest", status_code=200, summary="Ingest a document")
def ingest_document(
    db: Db,
    service: Service,
    document_id: str,
    pipeline: Annotated[IngestionPipeline, Depends(lambda: IngestionPipeline())],
) -> dict:
    chunks = pipeline.ingest(db, document_id)
    return {"document_id": document_id, "chunks": len(chunks), "status": "ready"}


@router.get("/{document_id}/chunks", summary="List ingested chunks")
def list_document_chunks(
    db: Db,
    service: Service,
    document_id: str,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    service.get(db, document_id)
    query = db.query(Chunk).filter(Chunk.document_id == document_id)
    chunks = query.order_by(Chunk.index).limit(limit).offset(offset)
    return [IngestionPipeline.chunk_to_dict(chunk) for chunk in chunks]


@router.get("/{document_id}", response_model=DocumentDetail, summary="Get a document")
def get_document(db: Db, service: Service, document_id: str) -> DocumentDetail:
    return service.to_detail(service.get(db, document_id))


@router.patch("/{document_id}", response_model=DocumentDetail, summary="Update document metadata")
def update_document(
    db: Db, service: Service, document_id: str, update: DocumentUpdate
) -> DocumentDetail:
    document = service.update_metadata(db, document_id, title=update.title)
    return service.to_detail(document)


@router.delete("/{document_id}", response_model=DeleteResponse, summary="Delete a document")
def delete_document(
    db: Db,
    service: Service,
    document_id: str,
    pipeline: Annotated[IngestionPipeline, Depends(lambda: IngestionPipeline())],
) -> DeleteResponse:
    service.get(db, document_id)
    pipeline.vector_index.delete_document(db, document_id)
    service.delete(db, document_id)
    logger.info("document deleted", extra={"document_id": document_id})
    return DeleteResponse(id=document_id)
