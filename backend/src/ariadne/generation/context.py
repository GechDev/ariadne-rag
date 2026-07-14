"""Context window management for grounded generation.

Retrieved passages are numbered, truncated to fit the model context budget and
emitted as a single block. `truncate_to_budget` guarantees the assembled
context never exceeds the configured number of characters.
"""

from __future__ import annotations

from ariadne.retrieval.fusion import RetrievedPassage


def truncate_to_budget(text: str, max_chars: int) -> str:
    """Truncate ``text`` to ``max_chars`` without splitting a word if possible."""
    if len(text) <= max_chars:
        return text
    cut = text[: max_chars + 1]
    break_at = cut.rfind(" ")
    end = break_at if break_at > 0 else max_chars
    return text[:end].rstrip() + "…"


def format_context(
    passages: list[RetrievedPassage], *, max_chars: int, max_passages: int
) -> str:
    """Render up to ``max_passages`` passages as numbered source blocks."""
    blocks: list[str] = []
    budget = max_chars
    for index, passage in enumerate(passages[:max_passages], start=1):
        text = truncate_to_budget(passage.text, max_chars=max(100, budget // (len(passages) or 1)))
        page = ", ".join(str(number) for number in passage.page_numbers) or "n/a"
        blocks.append(f"[{index}] (chunk {passage.chunk_id}, page {page})\n{text}")
    return "\n\n".join(blocks)
