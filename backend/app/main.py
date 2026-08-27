import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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


def _readiness_problems() -> list[str]:
    """Configuration problems that block full functionality.

    Non-fatal at startup so the process always serves /api/health (Railway
    treats the deploy as healthy) and logs exactly what to fix.
    """
    problems: list[str] = []
    if settings.is_production:
        problems = settings.validate_production()
        # Optional connectivity check — informational only when it works.
        try:
            if settings.elevenlabs_api_key and not tts_provider.ping():
                problems.append(
                    "ELEVENLABS_API_KEY is set but the ElevenLabs API was "
                    "unreachable — generation may fail."
                )
        except Exception as exc:  # pragma: no cover
            logger.error("ElevenLabs reachability check failed: %s", exc)
    return problems


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        Base.metadata.create_all(bind=engine)
        _seed_admin()
    except Exception as exc:
        # Don't crash-loop the container over a DB hiccup; keep the healthcheck
        # up and log the real cause (health will report degraded).
        logger.error("Database init/seeding failed: %s", exc)
    problems = _readiness_problems()
    if problems:
        joined = "\n  - ".join(problems)
        logger.error(
            "=== CONFIG READINESS (%s) ===\n"
            "  Missing/incorrect env vars mean some or all features are limited:\n"
            "  - %s\n"
            "  Fix them in Railway (Variables) and redeploy/restart. "
            "The healthcheck passes regardless so the deploy can come up.",
            settings.app_env,
            joined,
        )
    else:
        logger.info("Config readiness: OK (%s).", settings.app_env)
    if settings.openai_api_key:
        logger.info("OpenAI agent enabled (model=%s).", settings.openai_model)
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
    problems = _readiness_problems()
    body = {
        "status": "ok" if not problems else "degraded",
        "app": settings.app_name,
        "env": settings.app_env,
        "ready": not problems,
    }
    if problems:
        body["warnings"] = problems
    return body


app.mount(
    "/uploads",
    StaticFiles(directory=settings.upload_dir),
    name="uploads",
)