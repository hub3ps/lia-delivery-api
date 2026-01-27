from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker

from app.settings import settings

_engine = None
_async_engine = None
_SessionLocal = None


def _normalize_db_url(url: str) -> str:
    if not url:
        return settings.database_url
    if url.startswith("http://") or url.startswith("https://"):
        # fallback for misconfigured DATABASE_URL in local envs
        return "postgresql+psycopg://postgres:postgres@localhost:5432/lia"
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    return url


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(_normalize_db_url(settings.database_url), pool_pre_ping=True)
    return _engine


def get_async_engine():
    global _async_engine
    if _async_engine is None:
        _async_engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    return _async_engine


def get_sessionmaker():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal


@contextmanager
def get_db():
    db = get_sessionmaker()()
    try:
        yield db
    finally:
        db.close()
