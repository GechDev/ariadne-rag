"""Text normalization utilities for the ingestion pipeline.

Normalization produces clean, consistent text before chunking: excess
whitespace is collapsed, non-breaking spaces become regular spaces, and
logical paragraphs are separated by exactly one blank line.
"""

from __future__ import annotations

import re

_WHITESPACE_RE = re.compile(r"[ \t\u00a0\u2007\u202f]+")
_BLANK_LINES_RE = re.compile(r"\n{3,}")
_LEADING_TRAILING_RE = re.compile(r"^[ \t]+|[ \t]+$", re.MULTILINE)


def normalize_text(text: str) -> str:
    """Normalize whitespace while preserving paragraph structure."""
    if not text:
        return ""
    lines = [_WHITESPACE_RE.sub(" ", line) for line in text.splitlines()]
    lines = [_LEADING_TRAILING_RE.sub("", line) for line in lines]
    joined = "\n".join(lines)
    joined = _BLANK_LINES_RE.sub("\n\n", joined)
    return joined.strip()


def normalize_metadata(metadata: dict | None) -> dict:
    """Return a normalized copy of parser metadata."""
    if not metadata:
        return {}
    return {str(key): str(value) if value is not None else "" for key, value in metadata.items()}
