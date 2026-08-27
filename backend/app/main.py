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
from app.api.routes import admin, auth, tts, voices

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


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    _seed_admin()
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
app.include_router(admin.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name}


app.mount(
    "/uploads",
    StaticFiles(directory=settings.upload_dir),
    name="uploads",
)