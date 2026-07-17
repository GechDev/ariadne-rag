"""Server-sent event streaming for grounded answers.

The stream endpoint replays the full RAG pipeline as named SSE events so the
client can show retrieval progress, discovered sources and answer tokens as
they happen. Blocking work (retrieval, generation, persistence) runs off the
event loop, and the stream aborts cleanly when the client disconnects.
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import AsyncIterator
from queue import Queue
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from ariadne.citations.service import SourceReference
from ariadne.conversations.service import ConversationService
from ariadne.core.errors import AriadneError
from ariadne.db.session import get_session_factory
from ariadne.generation.service import GenerationService
from ariadne.logging import get_logger
from ariadne.models import Conversation
from ariadne.rag.service import RAGService
from ariadne.retrieval.fusion import RetrievedPassage
from ariadne.sse.events import (
    DONE,
    ERROR,
    GENERATION_COMPLETED,
    GENERATION_STARTED,
    RETRIEVAL_COMPLETED,
    RETRIEVAL_STARTED,
    SOURCES_FOUND,
    TOKEN,
    format_event,
)

router = APIRouter(prefix="/query", tags=["query"])
logger = get_logger("query.stream")

_DONE = object()


class StreamRequest(BaseModel):
    """A question asked against the indexed document corpus."""

    question: str = Field(min_length=1, max_length=2000, description="User question")
    top_k: int = Field(default=6, ge=1, le=50, description="Retrieved passages")
    document_ids: list[str] | None = Field(default=None, description="Scope the search")
    conversation_id: str | None = Field(default=None, description="Continue a conversation")


class _PreparedQuery:
    """Retrieval output staged before generation begins."""

    def __init__(
        self,
        passages: list[RetrievedPassage],
        references: list[SourceReference],
        conversation: Conversation,
    ) -> None:
        self.passages = passages
        self.references = references
        self.conversation = conversation


def _prepare(session: Any, payload: StreamRequest, rag: RAGService) -> _PreparedQuery:
    conversations = ConversationService()
    conversation = conversations.get_or_create(session, payload.conversation_id)
    conversations.add_message(session, conversation, "user", payload.question)
    passages = rag.retrieval.retrieve(
        session, payload.question, top_k=payload.top_k, document_ids=payload.document_ids
    )
    references = rag.citations.resolve(session, passages)
    session.flush()
    return _PreparedQuery(passages, references, conversation)


def _finalize(
    session: Any,
    payload: StreamRequest,
    prepared: _PreparedQuery,
    answer: str,
    grounded: bool,
) -> tuple[str, str]:
    conversations = ConversationService()
    assistant = conversations.add_message(session, prepared.conversation, "assistant", answer)
    prepared.conversation.title = payload.question[:120]
    rag = RAGService()
    rag.citations.persist(session, assistant.id, prepared.references)
    session.commit()
    return assistant.id, prepared.conversation.id


def _produce_tokens(
    generation: GenerationService,
    question: str,
    passages: list[RetrievedPassage],
    queue: Queue,
) -> None:
    try:
        for chunk in generation.stream(question, passages):
            queue.put_nowait(chunk)
    except Exception as exc:  # noqa: BLE001 - surfaced to the SSE error event
        queue.put_nowait(exc)
    finally:
        queue.put_nowait(_DONE)


async def _stream_tokens(
    generation: GenerationService,
    question: str,
    passages: list[RetrievedPassage],
    request: Request,
) -> AsyncIterator[str]:
    queue: Queue = Queue()
    thread = threading.Thread(
        target=_produce_tokens,
        args=(generation, question, passages, queue),
        daemon=True,
    )
    thread.start()
    while True:
        if await request.is_disconnected():
            logger.info("stream client disconnected during generation")
            return
        item = await asyncio.to_thread(queue.get)
        if item is _DONE:
            return
        if isinstance(item, Exception):
            raise item
        yield item


@router.post("/stream")
async def stream_query(payload: StreamRequest, request: Request) -> StreamingResponse:
    """Stream a grounded answer as server-sent events."""

    async def generate() -> AsyncIterator[str]:
        session = get_session_factory()()
        rag = RAGService()
        try:
            yield format_event(RETRIEVAL_STARTED, {"query": payload.question})
            prepared = await run_in_threadpool(_prepare, session, payload, rag)

            yield format_event(
                RETRIEVAL_COMPLETED,
                {
                    "retrieved": len(prepared.passages),
                    "documents": sorted({p.document_id for p in prepared.passages}),
                },
            )
            yield format_event(
                SOURCES_FOUND,
                {
                    "sources": [
                        {
                            "chunk_id": ref.chunk_id,
                            "document_id": ref.document_id,
                            "document_title": ref.document_title,
                            "index": ref.index,
                            "page_numbers": ref.page_numbers,
                            "rank": ref.rank,
                            "score": ref.score,
                        }
                        for ref in prepared.references
                    ]
                },
            )

            yield format_event(GENERATION_STARTED, {})
            tokens: list[str] = []
            async for token in _stream_tokens(
                rag.generation, payload.question, prepared.passages, request
            ):
                tokens.append(token)
                yield format_event(TOKEN, {"token": token})
            answer = "".join(tokens).strip()

            message_id, conversation_id = await run_in_threadpool(
                _finalize, session, payload, prepared, answer, bool(prepared.passages)
            )
            yield format_event(
                GENERATION_COMPLETED,
                {
                    "answer": answer,
                    "grounded": bool(prepared.passages) and answer != "",
                    "message_id": message_id,
                    "conversation_id": conversation_id,
                    "citations": [
                        {
                            "chunk_id": ref.chunk_id,
                            "document_id": ref.document_id,
                            "document_title": ref.document_title,
                            "index": ref.index,
                            "page_numbers": ref.page_numbers,
                            "rank": ref.rank,
                            "score": ref.score,
                        }
                        for ref in prepared.references
                    ],
                },
            )
            yield format_event(DONE, {})
        except AriadneError as exc:
            logger.error("stream query failed", extra={"error": exc.message})
            yield format_event(ERROR, {"code": exc.code, "message": exc.message})
        except Exception as exc:  # noqa: BLE001 - errors are reported over the stream
            logger.error("stream query failed", extra={"error": str(exc)})
            yield format_event(ERROR, {"code": "internal_error", "message": str(exc)})
        finally:
            session.close()

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
