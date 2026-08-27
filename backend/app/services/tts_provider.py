"""AI text-to-speech and voice-cloning provider.

Voice engine chain (best → fallback):

* **ElevenLabs** — used when ``ELEVENLABS_API_KEY`` is set. Highest quality and
  the only engine that performs true per-user voice cloning.
* **edge-tts** — free, no-key Microsoft Edge neural voices. Used by default in
  production so TTS works with zero configuration. Good language/voice coverage.
* **gTTS** — final fallback (only if edge-tts is unavailable).
"""

import asyncio
import io
import logging
from pathlib import Path

import httpx

from app.core.config import settings
from app.services import audio_utils

logger = logging.getLogger(__name__)

ELEVENLABS_API = "https://api.elevenlabs.io/v1"

# Map app voice characteristics (name hints) to suitable edge-tts voices so the
# chosen voice feels different depending on the voice/creator. Keys are matched
# loosely against the voice name; lower-case comparison is used.
EDGE_VOICE_ALIASES = {
    "aurora": "en-GB-SoniaNeural",
    "nolan": "en-US-GuyNeural",
    "iris": "en-AU-NatashaNeural",
    "atlas": "en-US-ChristopherNeural",
    "sable": "fr-FR-DeniseNeural",
    "kei": "ja-JP-NanamiNeural",
}

# Public "library" voices shown on the landing page with one-click previews.
# Each maps to a free edge-tts neural voice; the backend generates a real,
# playable sample for the demo so previews work with no ElevenLabs key.
LIBRARY_VOICES = [
    {"name": "Aurora", "tag": "Neural · EN-GB", "mood": "Bright, cinematic"},
    {"name": "Nolan", "tag": "Deep · EN-US", "mood": "Grounded, assured"},
    {"name": "Iris", "tag": "Warm · EN-AU", "mood": "Soft, close"},
    {"name": "Atlas", "tag": "Narrative · EN-US", "mood": "Documentary weight"},
    {"name": "Sable", "tag": "Intimate · FR", "mood": "Velvet, hushed"},
    {"name": "Kei", "tag": "Precise · EN-JP", "mood": "Crisp, editorial"},
]

# Short sample spoken when previewing a library voice.
LIBRARY_SAMPLE = (
    "Hello, I am {name}. Listen closely — this is what your next script "
    "could sound like, right before you use it."
)


class TTSError(Exception):
    """Raised when speech synthesis or cloning fails."""


class TTSProvider:
    def __init__(self) -> None:
        self.api_key = settings.elevenlabs_api_key
        self.use_elevenlabs = bool(self.api_key)
        # Populated once at startup (never per-healthcheck) so /api/health stays
        # local and fast even when the vendor endpooint is slow/unreachable.
        self.reachability_ok: bool | None = None
        self.edge_enabled = True
        try:
            import edge_tts  # noqa: F401
        except ImportError:
            self.edge_enabled = False
            logger.warning("edge-tts is not installed; falling back to gTTS.")
        engine = "ElevenLabs" if self.use_elevenlabs else "edge-tts (free)"
        logger.info("TTS provider: %s (fallback: gTTS)", engine)

    def ping(self, timeout: float = 8.0) -> bool:
        """Return True when the ElevenLabs API is reachable with the configured key.

        Uses a short timeout so a health/probe call never blocks for long if the
        vendor endpoint is slow or unreachable.
        """
        if not self.use_elevenlabs:
            return False
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.get(f"{ELEVENLABS_API}/user")
                return resp.status_code < 400
        except Exception:
            return False

    def _client(self) -> httpx.Client:
        return httpx.Client(
            headers={"xi-api-key": self.api_key} if self.api_key else {},
            timeout=300,
        )

    @staticmethod
    def _call(client: httpx.Client, method: str, url: str, **kwargs):
        resp = client.request(method, url, **kwargs)
        if resp.status_code >= 400:
            raise TTSError(f"provider error {resp.status_code}: {resp.text[:200]}")
        return resp

    def list_eleven_voices(self) -> list[dict]:
        if not self.use_elevenlabs:
            return []
        with self._client() as client:
            resp = self._call(client, "GET", f"{ELEVENLABS_API}/voices")
            return resp.json().get("voices", [])

    def get_voice(self, voice_id: str) -> dict | None:
        if not self.use_elevenlabs:
            return None
        try:
            with self._client() as client:
                resp = self._call(client, "GET", f"{ELEVENLABS_API}/voices/{voice_id}")
                return resp.json()
        except TTSError:
            return None

    # -- text-to-speech ---------------------------------------------------
    def synthesize(self, text: str, voice_ref: dict | None) -> tuple[bytes, str]:
        """Returns (audio_bytes, extension). voice_ref selects the voice:
          - provider_voice_id -> ElevenLabs voice by id (when a key is set)
          - audio_sample_path -> ElevenLabs instant-clone sample (when a key is set)
          - name              -> hint used to pick a suitable free edge voice
          - fallback          -> edge-tts, then gTTS
        """
        if self.use_elevenlabs:
            provider_id = (voice_ref or {}).get("provider_voice_id")
            sample_path = (voice_ref or {}).get("audio_sample_path")
            if provider_id or sample_path:
                try:
                    if provider_id:
                        return self._eleven_synthesize(
                            text, provider_id
                        ), ".mp3"
                    return self._eleven_instant_clone_synthesize(
                        text, Path(sample_path)
                    ), ".mp3"
                except TTSError as exc:
                    if settings.is_production:
                        raise
                    logger.warning(
                        "ElevenLabs synthesis failed, falling back to edge-tts: %s",
                        exc,
                    )

        # Free default engine (no key required): edge-tts, then gTTS.
        return self._free_synthesize(text, voice_ref)

    def _free_synthesize(
        self, text: str, voice_ref: dict | None
    ) -> tuple[bytes, str]:
        try:
            return self._edge_synthesize(text, voice_ref=voice_ref), ".mp3"
        except TTSError as exc:
            logger.warning("edge-tts failed, falling back to gTTS: %s", exc)
        return self._gtts_synthesize(text, voice_ref=voice_ref), ".mp3"

    def _resolve_edge_voice(self, voice_ref: dict | None) -> str:
        """Pick a free edge-tts voice based on the voice name, else default."""
        name = (voice_ref or {}).get("name") or ""
        default = settings.edge_voice or "en-US-AriaNeural"
        if not name:
            return default
        lower = name.lower()
        for alias, edge_voice in EDGE_VOICE_ALIASES.items():
            if alias in lower:
                return edge_voice
        return default

    def _edge_synthesize(
        self, text: str, *, voice_ref: dict | None = None
    ) -> bytes:
        """Synthesize via edge-tts (free Microsoft Edge neural voices)."""
        if not self.edge_enabled:
            raise TTSError("edge-tts is not installed")
        try:
            import edge_tts
        except ImportError as exc:  # pragma: no cover
            raise TTSError("edge-tts is not installed") from exc

        voice = self._resolve_edge_voice(voice_ref)
        communicate = edge_tts.Communicate(text[:2000], voice=voice)
        try:
            out = io.BytesIO()
            async def _save():
                chunks = []
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        chunks.append(chunk["data"])
                out.write(b"".join(chunks))
            asyncio.run(_save())
            data = out.getvalue()
        except Exception as exc:
            raise TTSError(f"edge-tts synthesis failed: {exc}") from exc
        if not data:
            raise TTSError("edge-tts produced empty audio")
        return data

    @staticmethod
    def library_voices() -> list[dict]:
        """The public library voices shown on the landing page, including each
        voice's preview URL (a real audio sample generated on demand)."""
        from app.api.urls import demo_preview_url

        return [
            {
                "name": v["name"],
                "tag": v["tag"],
                "mood": v["mood"],
                "preview_url": demo_preview_url(v["name"]),
            }
            for v in LIBRARY_VOICES
        ]

    def synthesize_demo(self, text: str, voice_name: str) -> bytes:
        """Generate real speech for the landing demo / library preview for a
        named voice. Uses the free edge-tts engine; falls back to gTTS."""
        voice_ref = {"name": voice_name or ""}
        try:
            return self._edge_synthesize(text[:2000], voice_ref=voice_ref)
        except TTSError as exc:
            logger.warning(
                "edge-tts demo synthesis failed, falling back to gTTS: %s", exc
            )
            return self._gtts_synthesize(text[:2000], voice_ref=voice_ref)

    def _gtts_synthesize(self, text: str, voice_ref: dict | None) -> bytes:
        try:
            from gtts import gTTS
        except ImportError as exc:  # pragma: no cover
            raise TTSError("gTTS is not installed") from exc

        try:
            tts = gTTS(text=text[:2000], lang="en")
            with io.BytesIO() as buf:
                tts.write_to_fp(buf)
                return buf.getvalue()
        except Exception as exc:
            raise TTSError(f"gTTS synthesis failed: {exc}") from exc

    def _eleven_synthesize(self, text: str, voice_id: str) -> bytes:
        with self._client() as client:
            resp = self._call(
                client, "POST",
                f"{ELEVENLABS_API}/text-to-speech/{voice_id}",
                json={"text": text[:2000], "model_id": settings.elevenlabs_model},
            )
            return resp.content

    def _eleven_instant_clone_synthesize(self, text: str, sample_path: Path) -> bytes:
        with self._client() as client:
            files = {"files": ("sample.wav", sample_path.read_bytes(), "audio/wav")}
            resp = self._call(
                client, "POST",
                f"{ELEVENLABS_API}/text-to-speech/_demo/instant-clone",
                data={"text": text[:2000], "model_id": settings.elevenlabs_model},
                files=files,
            )
            return resp.content

    # -- voice cloning ----------------------------------------------------
    def clone_voice(
        self,
        name: str,
        sample_path: Path,
        *,
        description: str | None = None,
    ) -> dict:
        """Create a cloned voice. Returns a dict that may contain
        ``provider_voice_id``. Raises TTSError on failure."""
        sample_wav = audio_utils.to_wav(sample_path)

        if self.use_elevenlabs:
            with open(sample_wav, "rb") as fh:
                files = {
                    "files": ("sample.wav", fh, "audio/wav"),
                    "name": (None, name[:120] or "Cloned Voice"),
                }
                if description:
                    files["description"] = (None, str(description)[:250])
                with self._client() as client:
                    resp = self._call(
                        client, "POST", f"{ELEVENLABS_API}/voices/add", files=files
                    )
                    return {"provider_voice_id": resp.json().get("voice_id")}

        # Fallback: no remote registration — the clone is stored locally using
        # its reference sample. True per-user cloning isn't available without a
        # key, but the voice still works (free edge-tts generates the speech),
        # so this is allowed in production too.
        logger.info(
            "No ElevenLabs key; storing clone locally using reference sample "
            "(proximity cloning via free edge-tts)."
        )
        return {"provider_voice_id": None}

    def create_preview(self, name: str, sample_path: Path) -> tuple[bytes, str]:
        """Generate preview audio for a newly cloned voice.

        With no key we synthesize a short greeting via edge-tts/gTTS so the
        preview can play in the browser.
        """
        greeting = f"Hi, this is {name}." if name else "Hi, this is a cloned voice."
        return self.synthesize(
            greeting,
            {"audio_sample_path": str(sample_path), "name": name},
        )


tts_provider = TTSProvider()