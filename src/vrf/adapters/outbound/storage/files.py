from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StoredFile:
    nombre_original: str
    mime: str
    path: str
    sha256: str
    size: int


class FileStorage:
    def __init__(self, storage_path: str) -> None:
        self._base = Path(storage_path)

    def save(self, data: bytes, nombre_original: str, mime: str) -> StoredFile:
        self._base.mkdir(parents=True, exist_ok=True)
        sha256 = hashlib.sha256(data).hexdigest()
        dest = self._base / sha256
        if not dest.exists():
            dest.write_bytes(data)
        return StoredFile(
            nombre_original=nombre_original,
            mime=mime,
            path=sha256,
            sha256=sha256,
            size=len(data),
        )

    def read(self, path: str) -> bytes:
        return (self._base / path).read_bytes()