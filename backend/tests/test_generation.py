"""Tests for grounded answer generation."""

from __future__ import annotations

from ariadne.generation.context import format_context, truncate_to_budget
from ariadne.generation.deterministic import (
    INSUFFICIENT_EVIDENCE,
    DeterministicLLMProvider,
)
from ariadne.generation.prompts import ANSWER_HEADER, CONTEXT_HEADER, QUESTION_HEADER, build_prompt
from ariadne.generation.service import GenerationService
from ariadne.retrieval.fusion import RetrievedPassage


def _passage(chunk_id: str, text: str, page: int = 1) -> RetrievedPassage:
    return RetrievedPassage(
        chunk_id=chunk_id,
        document_id="doc-1",
        index=0,
        page_numbers=[page],
        text=text,
        score=1.0,
    )


def test_prompt_contains_system_context_and_question():
    prompt = build_prompt(
        "What is ARIADNE?",
        [_passage("c1", "ARIADNE is a RAG platform.")],
        max_context_chars=8000,
        max_passages=6,
    )
    assert "question-answering assistant" in prompt
    assert CONTEXT_HEADER in prompt
    assert QUESTION_HEADER in prompt
    assert ANSWER_HEADER in prompt
    assert "What is ARIADNE?" in prompt
    assert "c1" in prompt


def test_context_respects_max_chars():
    text = "word " * 100
    truncated = truncate_to_budget(text, 50)
    assert len(truncated) <= 55


def test_context_caps_passage_count():
    passages = [_passage(f"c{i}", f"Passage number {i}.") for i in range(10)]
    context = format_context(passages, max_chars=10000, max_passages=3)
    assert context.count("[") == 3


def test_deterministic_provider_returns_grounded_sentences():
    provider = DeterministicLLMProvider()
    prompt = (
        "system instructions\n"
        f"{CONTEXT_HEADER}\n"
        "ARIADNE is a local-first RAG platform.\n"
        "The ocean is full of fish.\n"
        f"{QUESTION_HEADER}\n"
        "What is ARIADNE?\n"
        f"{ANSWER_HEADER}\n"
    )
    answer = provider.generate(prompt)
    assert "local-first RAG platform" in answer
    assert "ocean" not in answer


def test_deterministic_provider_reports_insufficient_evidence():
    provider = DeterministicLLMProvider()
    prompt = (
        "system instructions\n"
        f"{CONTEXT_HEADER}\n"
        "The ocean is full of fish.\n"
        f"{QUESTION_HEADER}\n"
        "What is ARIADNE?\n"
        f"{ANSWER_HEADER}\n"
    )
    assert provider.generate(prompt) == INSUFFICIENT_EVIDENCE


def test_deterministic_provider_streams_word_chunks():
    provider = DeterministicLLMProvider()
    prompt = (
        f"{CONTEXT_HEADER}\n"
        "ARIADNE is a local-first RAG platform.\n"
        f"{QUESTION_HEADER}\n"
        "What is ARIADNE?\n"
        f"{ANSWER_HEADER}\n"
    )
    chunks = list(provider.stream(prompt))
    assert len(chunks) > 1
    assert "".join(chunks).strip() == provider.generate(prompt)


def test_generation_service_returns_grounding_metadata():
    service = GenerationService()
    passages = [_passage("c1", "ARIADNE is a local-first RAG platform.")]
    result = service.generate("What is ARIADNE?", passages)
    assert result.grounded is True
    assert result.used_chunk_ids == ["c1"]
    assert "local-first RAG platform" in result.answer


def test_generation_service_flags_unsupported_answer():
    service = GenerationService()
    passages = [_passage("c1", "The ocean is full of fish.")]
    result = service.generate("What is ARIADNE?", passages)
    assert result.grounded is False
    assert result.answer == INSUFFICIENT_EVIDENCE


def test_generation_service_empty_passages_is_ungrounded():
    service = GenerationService()
    result = service.generate("Anything", [])
    assert result.grounded is False
    assert result.answer == INSUFFICIENT_EVIDENCE


def test_generation_service_streams_chunks():
    service = GenerationService()
    passages = [_passage("c1", "ARIADNE is a local-first RAG platform.")]
    streamed = "".join(service.stream("What is ARIADNE?", passages)).strip()
    assert "local-first" in streamed


def test_factory_returns_deterministic_provider():
    from ariadne.generation.factory import get_llm_provider

    assert isinstance(get_llm_provider(), DeterministicLLMProvider)
