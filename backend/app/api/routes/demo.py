"""Public landing-page demo endpoints.

These let visitors preview library voices and try the live text-to-speech demo
without an account or API key. The audio is generated on demand by the free
edge-tts engine (or gTTS as a fallback), and each endpoint is rate-limited to
prevent abuse.
"""

import logging

from fastapi import APIRouter, Depends, Query, Response

from app.core.ratelimit import rate_limit
from app.services.tts_provider import LIBRARY_SAMPLE, TTSError, tts_provider

logger = logging.getLogger(__name__)

router = APIRouter(tags=["demo"])

_DEFAULT_TEXT = (
    "Welcome to Voxcraft. Type anything here, and I will speak it back to you."
)


def _resolve_voice(name: str | None) -> str:
    clean = (name or "").strip()
    return clean or "Aurora"


@router.get("/demo/voices", name="demo:voices")
def list_voices(
    _rl: None = Depends(rate_limit(60)),
):
    """Public library voices, each with a one-click preview URL."""
    return tts_provider.library_voices()


@router.get("/demo/preview", name="demo:preview", response_class=Response)
def preview(
    voice: str = Query(default="Aurora"),
    _rl: None = Depends(rate_limit(20)),
):
    """Real audio sample for a library voice, on demand."""
    name = _resolve_voice(voice)
    text = LIBRARY_SAMPLE.format(name=name)
    audio = _synthesize(text, name)
    return Response(
        content=audio,
        media_type="audio/mpeg",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.get("/demo/speak", name="demo:speak", response_class=Response)
def speak(
    voice: str = Query(default="Aurora"),
    text: str = Query(default=_DEFAULT_TEXT),
    _rl: None = Depends(rate_limit(20)),
):
    """Generate speech for the landing demo's typed text."""
    name = _resolve_voice(voice)
    cleaned = (text or "").strip() or _DEFAULT_TEXT
    audio = _synthesize(cleaned, name)
    return Response(content=audio, media_type="audio/mpeg")


def _synthesize(text: str, voice_name: str) -> bytes:
    try:
        return tts_provider.synthesize_demo(text, voice_name)
    except TTSError as exc:
        logger.error("Demo synthesis failed for %s: %s", voice_name, exc)
        raise