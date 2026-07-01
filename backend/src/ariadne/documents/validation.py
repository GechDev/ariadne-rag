"""Document upload validation.

Defines the set of accepted content types and enforces size limits before a
file is written to storage.
"""

from __future__ import annotations

from pathlib import Path

from ariadne.core.errors import UnsupportedDocumentTypeError

SUPPORTED_EXTENSIONS: dict[str, str] = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".json": "application/json",
    ".html": "text/html",
    ".htm": "text/html",
    ".rst": "text/x-rst",
}

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MiB


def infer_content_type(filename: str, declared: str | None = None) -> str:
    """Resolve the effective content type for an uploaded file.

    A declared type is trusted only when it matches a supported document
    format; otherwise the type is inferred from the file extension.
    """
    ext = Path(filename).suffix.lower()
    inferred = SUPPORTED_EXTENSIONS.get(ext)
    if inferred is None:
        raise UnsupportedDocumentTypeError(
            f"unsupported file type {ext or '(none)'!r}",
            detail={"supported": sorted(SUPPORTED_EXTENSIONS)},
        )
    return inferred


def validate_upload_size(size_bytes: int) -> None:
    """Raise if the upload exceeds the configured maximum size."""
    if size_bytes > MAX_UPLOAD_BYTES:
        from ariadne.core.errors import ValidationError

        raise ValidationError(
            "file exceeds the maximum allowed size",
            detail={"max_bytes": MAX_UPLOAD_BYTES, "received_bytes": size_bytes},
        )


def is_supported_content_type(content_type: str) -> bool:
    """Return True if a declared content type maps to a supported format."""
    base = content_type.split(";")[0].strip().lower()
    return base in SUPPORTED_EXTENSIONS.values()
