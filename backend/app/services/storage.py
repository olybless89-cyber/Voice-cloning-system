import uuid
from pathlib import Path

from app.core.config import settings


class StorageService:
    """Local filesystem storage for voice samples and generated audio.

    Swap this for S3/GCS by replacing these methods; the rest of the app
    relies only on the relative URL returned by ``save_*``.
    """

    def __init__(self) -> None:
        self._root = Path(settings.upload_dir)
        self.voice_dir = self._root / "voices"
        self.generation_dir = self._root / "generations"
        self.voice_dir.mkdir(parents=True, exist_ok=True)
        self.generation_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _ext(filename: str) -> str:
        suffix = Path(filename).suffix.lower()
        return suffix if suffix else ".mp3"

    def save_voice_sample(self, data: bytes, filename: str) -> "tuple[str, Path]":
        suffix = self._ext(filename)
        rel = f"voices/{uuid.uuid4().hex}{suffix}"
        path = self._root / rel
        path.write_bytes(data)
        return rel, path

    def save_preview(self, data: bytes, suffix: str = ".mp3") -> tuple[str, Path]:
        rel = f"voices/preview_{uuid.uuid4().hex}{suffix if suffix else '.mp3'}"
        path = self._root / rel
        path.write_bytes(data)
        return rel, path

    def save_generation(self, data: bytes, suffix: str = ".mp3") -> tuple[str, Path]:
        rel = f"generations/{uuid.uuid4().hex}{suffix if suffix else '.mp3'}"
        path = self._root / rel
        path.write_bytes(data)
        return rel, path

    def path(self, rel_path: str) -> Path:
        """Resolve a stored relative path (e.g. 'voices/abc.mp3') to a filesystem
        path, guarding against path traversal."""
        root = self._root.resolve()
        candidate = (root / rel_path).resolve()
        if not str(candidate).startswith(str(root)):
            raise ValueError("Invalid path")
        return candidate

    def remove(self, rel_path: str | None) -> None:
        if not rel_path:
            return
        try:
            Path(self._root / rel_path).unlink(missing_ok=True)
        except (OSError, ValueError):
            pass


storage = StorageService()