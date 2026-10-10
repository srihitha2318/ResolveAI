from contextlib import asynccontextmanager
from pathlib import Path
import sys
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse

_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from app.core.config import settings
from app.core.logging_config import logger
from app.api.routes import api_router
from app.schemas.health import HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup and shutdown routines."""
    logger.info("Starting up %s (v%s) in %s mode", settings.APP_NAME, settings.APP_VERSION, settings.APP_ENV)

    if settings.is_production and settings.SECRET_KEY == "resolveai-super-secret-key-development-2026-secure-random":
        logger.warning(
            "CRITICAL SECURITY WARNING: Production environment detected with default development SECRET_KEY! "
            "Please configure a secure random SECRET_KEY environment variable."
        )

    # Ensure database schema is initialized and seeded if running in a fresh container
    try:
        from app.database.init_db import init_db
        init_db()
        from app.database.db import SessionLocal
        from app.database.seed import seed_database
        from app.database.models import User
        with SessionLocal() as db_session:
            has_users = db_session.query(User).first() is not None
            if not has_users:
                logger.info("Fresh database detected. Seeding initial marketplace demonstration data...")
                seed_database(db_session)
    except Exception as e:
        logger.warning("Database schema check warning: %s", e)

    # Ensure ChromaDB policy knowledge base is indexed if empty
    try:
        from app.rag.vector_store import ChromaPolicyVectorStore
        from app.rag.embeddings import get_embedding_provider
        from app.rag.index_policies import run_indexing
        store = ChromaPolicyVectorStore(embedding_provider=get_embedding_provider())
        if store.count == 0 and settings.POLICIES_DIR.exists():
            logger.info("Empty ChromaDB policy collection detected. Indexing policies from %s...", settings.POLICIES_DIR)
            run_indexing(force_reindex=False)
    except Exception as e:
        logger.warning("Policy knowledge base indexing check warning: %s", e)

    yield
    logger.info("Shutting down %s", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Autonomous Multimodal Multi-Agent Customer Support Resolution Foundation API",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [settings.CORS_ORIGINS]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler to log errors and avoid leaking internal tracebacks."""
    logger.error("Unhandled server exception processing %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred."},
    )


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Basic health check probe",
    tags=["system"]
)
def health_check() -> HealthResponse:
    """Lightweight health check endpoint returning HTTP 200 when service is running."""
    return HealthResponse(status="ok")


@app.get(
    "/dashboard",
    response_class=HTMLResponse,
    summary="Human-in-the-Loop Supervisor Review Command Center",
    tags=["system"],
)
def supervisor_dashboard() -> HTMLResponse:
    """Serves the Level 5 Human-in-the-Loop supervisor review dashboard."""
    dashboard_file = Path(__file__).resolve().parent / "static" / "dashboard.html"
    if dashboard_file.exists():
        return HTMLResponse(content=dashboard_file.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Dashboard UI file not found</h1>", status_code=404)


@app.get(
    "/",
    summary="Root service greeting and documentation reference",
    tags=["system"]
)
def root():
    """Root endpoint welcoming clients and directing them to OpenAPI documentation."""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "docs": "/docs",
        "api_status": f"{settings.API_PREFIX}/status",
        "health": "/health",
        "dashboard": "/dashboard",
    }


# Include versioned API routes
app.include_router(api_router, prefix=settings.API_PREFIX)
