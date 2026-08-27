import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models.user import User
from app.api.routes import admin, agent, auth, tts, voices
from app.services.tts_provider import tts_provider

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn")


def _seed_admin() -> None:
    db = SessionLocal()
    try:
        default_email = "admin@voiceclone.app"
        if not db.query(User).filter(User.email == default_email).first():
            db.add(
                User(
                    email=default_email,
                    full_name="Platform Admin",
                    hashed_password=hash_password("admin123"),
                    is_admin=True,
                    is_active=True,
                )
            )
            db.commit()
            logger.warning(
                "Seeded default admin %s / admin123 — change immediately in production",
                default_email,
            )
    finally:
        db.close()


def _validate_providers() -> None:
    """Fail-fast on insecure/demo-only configuration in production, and
    run lightweight connectivity checks on the AI providers."""
    if settings.is_production:
        problems = settings.validate_production()
        if problems:
            joined = "\n  - ".join(problems)
            raise RuntimeError(
                "Refusing to start in production with the following configuration "
                f"problems:\n  - {joined}\n\n"
                "Fix them in Railway (Variables) before the deploy can come up."
            )
        # Network reachability check for the voice engine.
        try:
            reachable = tts_provider.ping()
        except Exception as exc:  # pragma: no cover
            reachable = False
            logger.error("ElevenLabs reachability check failed: %s", exc)
        if not reachable:
            raise RuntimeError(
                "ELEVENLABS_API_KEY is set but the ElevenLabs API is unreachable. "
                "Check the key/network before going live."
            )
        logger.info("ElevenLabs API reachable.")
    else:
        logger.warning(
            "APP_ENV is %r (not 'production') — demo fallbacks and relaxed "
            "secrets are allowed. Set APP_ENV=production when going live.",
            settings.app_env,
        )

    if settings.openai_api_key:
        logger.info("OpenAI agent enabled (model=%s).", settings.openai_model)
    else:
        logger.info("OpenAI agent disabled — set OPENAI_API_KEY to enable Script Studio.")


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    _seed_admin()
    _validate_providers()
    logger.info("Storage dirs ready at %s", settings.upload_dir)
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(voices.router, prefix="/api")
app.include_router(tts.router, prefix="/api")
app.include_router(agent.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name}


app.mount(
    "/uploads",
    StaticFiles(directory=settings.upload_dir),
    name="uploads",
)