"""Build public URLs for stored audio files."""


def audio_url(rel_path: str | None) -> str | None:
    if not rel_path:
        return None
    return f"/uploads/{rel_path}"


def demo_preview_url(voice_name: str | None) -> str:
    """Public preview URL for a landing-page library voice."""
    name = (voice_name or "").strip()
    return f"/api/demo/preview?voice={name}"