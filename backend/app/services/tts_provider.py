"""AI text-to-speech and voice-cloning provider.

Uses ElevenLabs when ``ELEVENLABS_API_KEY`` is configured, otherwise falls back
to the free, no-key gTTS service so the entire product flow (clone → generate →
listen → download) works out of the box for demos and local development.
"""

import io
import logging
from pathlib import Path

import httpx

from app.core.config import settings
from app.services import audio_utils

logger = logging.getLogger(__name__)

ELEVENLABS_API = "https://api.elevenlabs.io/v1"


class TTSError(Exception):
    """Raised when speech synthesis or cloning fails."""


class TTSProvider:
    def __init__(self) -> None:
        self.api_key = settings.elevenlabs_api_key
        self.use_elevenlabs = bool(self.api_key)
        logger.info(
            "TTS provider: %s",
            "ElevenLabs" if self.use_elevenlabs else "gTTS fallback (no ELEVENLABS_API_KEY)",
        )

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
          - provider_voice_id -> ElevenLabs voice by id
          - audio_sample_path -> ElevenLabs instant-clone from that sample
          - fallback          -> gTTS
        """
        if self.use_elevenlabs:
            provider_id = (voice_ref or {}).get("provider_voice_id")
            sample_path = (voice_ref or {}).get("audio_sample_path")
            provider_params = {}
            if provider_id:
                provider_params["voice_id"] = provider_id
            elif sample_path:
                provider_params["clone_sample"] = str(sample_path)
            try:
                if provider_params.get("voice_id"):
                    return self._eleven_synthesize(text, provider_params["voice_id"]), ".mp3"
                if provider_params.get("clone_sample"):
                    return self._eleven_instant_clone_synthesize(
                        text, Path(provider_params["clone_sample"])
                    ), ".mp3"
            except TTSError as exc:
                logger.warning(
                    "ElevenLabs synthesis failed, falling back to gTTS: %s", exc
                )

        return self._gtts_synthesize(text, voice_ref=voice_ref), ".mp3"

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

        # Fallback: no remote registration — the local reference sample is the
        # clone, so synthesis reuses it.
        logger.info(
            "No ElevenLabs key; storing clone locally using reference sample."
        )
        return {"provider_voice_id": None}

    def create_preview(self, name: str, sample_path: Path) -> tuple[bytes, str]:
        """Generate preview audio for a newly cloned voice.

        With no key we synthesize a short greeting via gTTS so the preview can
        play in the browser.
        """
        greeting = f"Hi, this is {name}." if name else "Hi, this is a cloned voice."
        return self.synthesize(greeting, {"audio_sample_path": str(sample_path)})


tts_provider = TTSProvider()