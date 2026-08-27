import logging
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App / environment
    app_name: str = "Voxcraft"
    app_env: str = "production"  # development | production
    debug: bool = False

    # Database
    database_url: str = "sqlite:///./voiceclone.db"

    # Auth
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Storage (override to /data/uploads in Railway with a mounted volume)
    upload_dir: str = "./uploads"
    # Built SPA directory (present in the single-container image).
    www_dir: str = "/app/www"

    # CORS
    frontend_url: str = "http://localhost:5173"

    # ── AI voice engine (ElevenLabs, optional) ─────────────────────
    # Optional. When set, high-quality ElevenLabs neural voices and true
    # voice cloning are used. When empty, the app transparently uses the free,
    # no-key edge-tts (Microsoft Edge neural voices) so all core features work
    # in production out of the box. gTTS remains as a final fallback.
    elevenlabs_api_key: str = ""
    elevenlabs_model: str = "eleven_multilingual_v2"
    # Default edge-tts voice used for generation when no ElevenLabs key is set.
    edge_voice: str = "en-US-AriaNeural"

    # ── OpenAI agent (LLM) ─────────────────────────────────────────
    # Optional: powers the Script Studio / voice-assistant features.
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # ── Rate limiting ──────────────────────────────────────────────
    # Requests per minute, per client, on sensitive routes.
    rate_limit_minute: int = 20

    @property
    def voice_dir(self) -> str:
        return f"{self.upload_dir}/voices"

    @property
    def generation_dir(self) -> str:
        return f"{self.upload_dir}/generations"

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def cors_origins(self) -> list[str]:
        origins = [self.frontend_url]
        if self.debug:
            origins.append("http://localhost:5173")
        return list(dict.fromkeys(o for o in origins if o))

    def validate_production(self) -> list[str]:
        """Return a list of configuration problems. Fail-hard in production so
        we never silently ship demo-grade behaviour."""
        problems: list[str] = []

        if not self.database_url or self.database_url.startswith("sqlite"):
            problems.append(
                "DATABASE_URL must point to PostgreSQL in production "
                "(got a SQLite URL)."
            )
        if not self.jwt_secret or self.jwt_secret == "dev-secret-change-me":
            problems.append("JWT_SECRET must be a strong random secret.")
        # ELEVENLABS_API_KEY is now optional: without it the app uses the free
        # edge-tts engine. Only warn so operators know voices are limited to the
        # built-in neural voices (no true per-user voice cloning).
        if not self.elevenlabs_api_key:
            logger.info(
                "ELEVENLABS_API_KEY not set — using free edge-tts for TTS "
                "(no per-user voice cloning)."
            )
        return problems


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()