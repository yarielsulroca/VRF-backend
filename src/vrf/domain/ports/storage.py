from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class StoredFile:
    nombre_original: str
    mime: str
    path: str
    sha256: str
    size: int


class ArchivoStorage(Protocol):
    def save(self, data: bytes, nombre_original: str, mime: str) -> StoredFile: ...
    def read(self, path: str) -> bytes: ...
