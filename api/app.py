"""FastAPI application factory.

Creates the app instance, wires up routers, and manages startup/shutdown
via an async lifespan context manager (replaces deprecated on_event hooks).
"""

import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import JSONResponse

import config
from api.routes import artifacts, pipeline, search
from api.schemas import HealthResponse

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Configure logging and environment on startup; log shutdown on exit.

    Args:
        app: The FastAPI application instance (injected by Starlette).
    """
    load_dotenv()
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format=config.LOG_FORMAT,
    )
    logger.info("Incident Analysis API starting")
    yield
    logger.info("Incident Analysis API shutting down")


def create_app() -> FastAPI:
    """Construct and configure the FastAPI application.

    Registers all routers under the /api prefix and attaches the health
    endpoint directly on the app so it is always reachable.

    Returns:
        Configured FastAPI instance ready to serve.
    """
    app = FastAPI(
        title="Incident Analysis API",
        description="LangGraph pipeline for production incident analysis",
        version="0.1.0",
        lifespan=lifespan,
    )

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(pipeline.router, prefix="/api")
    app.include_router(search.router, prefix="/api")
    app.include_router(artifacts.router, prefix="/api")

    @app.get("/api/health", response_model=HealthResponse, tags=["health"])
    def health() -> HealthResponse:
        """Liveness probe — returns ok when the server is accepting requests.

        Returns:
            HealthResponse with status and API version.
        """
        return HealthResponse(status="ok", version="0.1.0")

    return app


# Module-level app instance consumed by uvicorn and the test client.
app = create_app()
