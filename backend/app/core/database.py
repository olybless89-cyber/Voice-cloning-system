from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


def _connect_args():
    if settings.database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    # Bound the connect so a slow/unreachable DATABASE_URL fails fast instead
    # of hanging uvicorn's startup (psycopg2 defaults to no timeout, which can
    # block indefinitely and make Railway report the deploy as never healthy).
    return {"connect_timeout": 10}


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_timeout=30,
    pool_recycle=1800,
    connect_args=_connect_args(),
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()