"""FastAPI application entry point for the civic AI platform."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:
    from .database import engine, run_sqlite_migrations
    from .models.db_models import Base
    from .routers.complaints import router as complaints_router
    from .routers.clusters import router as clusters_router
    from .routers.geocoding import router as geocoding_router
    from .routers.aggregation import router as aggregation_router
    from .routers.insights import router as insights_router
    from .routers.simulation import router as simulation_router
except ImportError:  # Supports `uvicorn main:app` from the backend directory.
    from database import engine, run_sqlite_migrations
    from models.db_models import Base
    from routers.complaints import router as complaints_router
    from routers.clusters import router as clusters_router
    from routers.geocoding import router as geocoding_router
    from routers.aggregation import router as aggregation_router
    from routers.insights import router as insights_router
    from routers.simulation import router as simulation_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Create database tables before serving requests."""

    run_sqlite_migrations()
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Civic AI Platform",
    description="Decision-support infrastructure for civic policy simulations.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3002",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(complaints_router, prefix="/api")
app.include_router(clusters_router, prefix="/api")
app.include_router(geocoding_router, prefix="/api")
app.include_router(aggregation_router, prefix="/api")
app.include_router(insights_router, prefix="/api")
app.include_router(simulation_router, prefix="/api")


@app.get("/")
def root() -> dict[str, str]:
    """Return a minimal service health response."""

    return {"status": "ok"}
