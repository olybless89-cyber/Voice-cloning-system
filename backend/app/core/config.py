from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_name: str = "VoiceClone AI"
    debug: bool = False

    # Database
    database_url: str = "sqlite:///./voiceclone.db"

    # Auth
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Storage (override to /data/uploads in Railway with a mounted volume)
    upload_dir: str = "./uploads"

    # CORS
    frontend_url: str = "http://localhost:5173"

    # AI provider
    elevenlabs_api_key: str = ""
    elevenlabs_model: str = "eleven_multilingual_v2"

    @property
    def voice_dir(self) -> str:
        return f"{self.upload_dir}/voices"

    @property
    def generation_dir(self) -> str:
        return f"{self.upload_dir}/generations"

    @property
    def cors_origins(self) -> list[str]:
        origins = [self.frontend_url]
        if self.debug:
            origins.append("http://localhost:5173")
        return list(dict.fromkeys(o for o in origins if o))


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()