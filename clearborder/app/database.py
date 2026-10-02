"""Database engine: SQLite for local development, PostgreSQL when DATABASE_URL says so."""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

_is_sqlite = settings.database_url.startswith("sqlite")

_engine_kwargs: dict = {
    "connect_args": {"check_same_thread": False} if _is_sqlite else {},
    "pool_pre_ping": not _is_sqlite,
    "echo": settings.debug,
}
if not _is_sqlite:
    _engine_kwargs.update(pool_size=10, max_overflow=20, pool_recycle=3600)

engine = create_engine(settings.database_url, **_engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency: one session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables (no migrations in this prototype)."""
    from app import models  # noqa: F401  (registers the models on Base.metadata)

    Base.metadata.create_all(bind=engine)
