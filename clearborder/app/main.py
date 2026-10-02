"""ClearBorder API: CBAM embedded-emissions calculator and quarterly report export."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from . import routes
from .config import settings
from .database import engine, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="ClearBorder API",
    description="CBAM specific embedded emissions (SEE) calculator and quarterly report export",
    version=settings.app_version,
    lifespan=lifespan,
)

# Wide-open CORS keeps the local dashboard simple; restrict origins before any real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes.router, prefix="/api/v1", tags=["API"])


@app.get("/")
def root():
    return {"name": settings.app_name, "version": settings.app_version, "docs": "/docs", "health": "/health"}


@app.get("/health")
def health():
    """Liveness probe; also pings the database when it is not SQLite."""
    result = {"status": "ok"}
    if not settings.database_url.startswith("sqlite"):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            result["database"] = "connected"
        except SQLAlchemyError as e:  # report, do not crash the probe
            result["database"] = "error"
            result["error"] = str(e)
    return result
