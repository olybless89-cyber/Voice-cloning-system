"""Build public URLs for stored audio files."""


def audio_url(rel_path: str | None) -> str | None:
    if not rel_path:
        return None
    return f"/uploads/{rel_path}"