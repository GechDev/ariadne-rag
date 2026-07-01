"""Local filesystem storage for uploaded documents.

The storage layer hides how document bytes are persisted. It writes each
upload into the configured upload directory using a content-derived name so
the same file is never stored twice.
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from ariadne.config import get_settings
from ariadne.core.errors import NotFoundError
from ariadne.logging import get_logger

logger = get_logger("documents.storage")


class DocumentStorage:
    """Persist and retrieve raw document bytes on the local filesystem."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or get_settings().storage.upload_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, key: str) -> Path:
        # Guard against path traversal attempts.
        safe_key = Path(key).name
        return self.base_dir / safe_key

    def checksum(self, data: bytes) -> str:
        """Return the sha256 checksum of the uploaded bytes."""
        return hashlib.sha256(data).hexdigest()

    def save(self, data: bytes, checksum: str) -> str:
        """Persist bytes and return the storage key for later retrieval."""
        key = f"{checksum}.bin"
        path = self._path_for(key)
        if not path.exists():
            path.write_bytes(data)
        logger.info("stored document", extra={"storage_key": key, "bytes": len(data)})
        return key

    def read(self, key: str) -> bytes:
        """Return the bytes stored under ``key``."""
        path = self._path_for(key)
        if not path.exists():
            raise NotFoundError(f"stored file not found for key {key!r}")
        return path.read_bytes()

    def delete(self, key: str) -> None:
        """Remove the stored file for ``key`` if present."""
        path = self._path_for(key)
        if path.exists():
            path.unlink()
            logger.info("deleted stored document", extra={"storage_key": key})

    def open_for_reading(self, key: str) -> object:
        """Return a readable file handle for the stored document."""
        path = self._path_for(key)
        if not path.exists():
            raise NotFoundError(f"stored file not found for key {key!r}")
        return path.open("rb")

    def clear(self) -> None:
        """Remove every stored file (used by tests)."""
        for child in self.base_dir.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
