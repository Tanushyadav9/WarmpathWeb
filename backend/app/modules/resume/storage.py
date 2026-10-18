import os
from pathlib import Path
from typing import Protocol, runtime_checkable

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_UPLOAD_DIR = REPO_ROOT / "uploads" / "resumes"


@runtime_checkable
class StorageDriver(Protocol):
    async def save(self, file_bytes: bytes, filename: str) -> str:
        """Saves file bytes and returns canonical storage URI or path."""
        ...

    async def read(self, path: str) -> bytes:
        """Reads file bytes from storage URI or path."""
        ...

    async def delete(self, path: str) -> None:
        """Deletes file from storage."""
        ...


class LocalStorageDriver:
    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or DEFAULT_UPLOAD_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def save(self, file_bytes: bytes, filename: str) -> str:
        target_path = self.base_dir / filename
        target_path.write_bytes(file_bytes)
        return str(target_path)

    async def read(self, path: str) -> bytes:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Stored resume file not found: {path}")
        return p.read_bytes()

    async def delete(self, path: str) -> None:
        p = Path(path)
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass


def get_storage_driver() -> StorageDriver:
    return LocalStorageDriver()
