"""
Goldmine AI — FastAPI Application

Main entry point for the backend.
"""

import asyncio

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from contextlib import asynccontextmanager

from app.core.config import settings
from app.api.routes import attachments, chat, memory, models, preferences
from app.db.prisma import connect_prisma, disconnect_prisma

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.database_ready = False
    if not settings.is_database_configured:
        logger.error("Database connection unavailable: DATABASE_URL is not configured.")
        chat.enable_memory_mode()
    else:
        logger.info("Connecting to Prisma database...")
        try:
            # Direct Supabase Postgres can be unreachable on some local
            # networks. Do not let that socket wait block the API startup;
            # chat falls back to a temporary in-memory session until it recovers.
            await asyncio.wait_for(connect_prisma(), timeout=8)
            app.state.database_ready = True
            logger.info("Connected to Prisma database successfully.")
        except Exception as exc:
            logger.error("Failed to connect to Prisma (%s)", type(exc).__name__)
            # Continue in degraded mode; health reports the failed connection.
            # Route chat CRUD and generation through the outage fallback instead
            # of making each request wait for another failing Postgres call.
            chat.enable_memory_mode()
    try:
        yield
    finally:
        logger.info("Disconnecting from Prisma database...")
        await disconnect_prisma()


# Initialize FastAPI
app = FastAPI(
    title="Goldmine AI API",
    description="Multi-model AI Orchestration Engine",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy" if getattr(app.state, "database_ready", False) else "degraded",
        "services": {
            "database": {
                "configured": settings.is_database_configured,
                "ready": getattr(app.state, "database_ready", False),
            },
            "huggingface": "configured" if settings.is_hf_configured else "unconfigured",
            "gemini": "configured" if settings.is_gemini_configured else "unconfigured",
            "openrouter": "configured" if settings.is_openrouter_configured else "unconfigured",
            "free_models_only": settings.free_models_only,
            "supabase_auth": "configured" if settings.is_supabase_configured else "unconfigured",
            "web_research": "configured" if settings.search_api_key else "unconfigured",
        },
    }


# Exception handlers
@app.exception_handler(RuntimeError)
async def runtime_error_handler(request, exc):
    logger.error("Runtime error (%s)", type(exc).__name__)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "The server could not complete this request."},
    )


# Include routers
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(models.router, prefix="/api/models", tags=["models"])
app.include_router(memory.router, prefix="/api/memory", tags=["memory"])
app.include_router(attachments.router, prefix="/api/attachments", tags=["attachments"])
app.include_router(preferences.router, prefix="/api/preferences", tags=["preferences"])
