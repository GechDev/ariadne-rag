"""Retrieval endpoints for searching the vector index."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ariadne.api.deps import get_db
from ariadne.core.errors import EmbeddingProviderError
from ariadne.embeddings.factory import get_embedding_provider
from ariadne.vectors.numpy_store import NumpyVectorStore
from ariadne.vectors.service import VectorIndexService

router = APIRouter(prefix="/retrieval", tags=["retrieval"])

Db = Annotated[Session, Depends(get_db)]


class RetrievedChunk(BaseModel):
    """A single retrieval hit with its provenance metadata."""

    chunk_id: str
    document_id: str
    index: int
    page_numbers: list[int] = Field(default_factory=list)
    text: str
    score: float


class SearchResponse(BaseModel):
    """Result of a vector search."""

    query: str
    hits: list[RetrievedChunk]


@router.get("/vector/search", response_model=SearchResponse, summary="Search the vector index")
def vector_search(
    db: Db,
    q: str = Query(..., min_length=1, max_length=2000, description="Search query"),
    top_k: int = Query(default=10, ge=1, le=50),
    document_ids: list[str] | None = Query(default=None),
) -> SearchResponse:
    service = VectorIndexService(provider=get_embedding_provider(), store=NumpyVectorStore())
    try:
        query_vector = service.provider.embed_one(q)
    except EmbeddingProviderError:
        raise
    matches = service.store.search(
        db, query_vector, top_k=top_k, document_ids=document_ids
    )
    return SearchResponse(
        query=q,
        hits=[
            RetrievedChunk(
                chunk_id=hit.chunk_id,
                document_id=hit.document_id,
                index=hit.index,
                page_numbers=hit.page_numbers,
                text=hit.text,
                score=hit.score,
            )
            for hit in matches
        ],
    )
