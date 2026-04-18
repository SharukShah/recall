"""
ReCall MVP — FastAPI application entry point.
Handles app lifecycle, CORS, routing, and error handling.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from openai import AsyncOpenAI
from fsrs import Scheduler
import logging

from config import settings
from db import create_db_pool, close_db_pool
from routers import captures, reviews, stats

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Sets up resources on startup and cleans up on shutdown.
    """
    # STARTUP
    logger.info("Starting ReCall API...")
    
    # Create database connection pool
    app.state.db_pool = await create_db_pool()
    logger.info("Database pool created")
    
    # Initialize OpenAI client
    app.state.openai = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    logger.info("OpenAI client initialized")
    
    # Initialize FSRS scheduler with default parameters
    app.state.scheduler = Scheduler()
    logger.info("FSRS scheduler initialized")
    
    yield
    
    # SHUTDOWN
    logger.info("Shutting down ReCall API...")
    await close_db_pool(app.state.db_pool)
    logger.info("Database pool closed")


# Create FastAPI app
app = FastAPI(
    title="ReCall API",
    description="AI-powered spaced repetition memory system",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware (allow Next.js frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catch-all exception handler.
    Logs error and returns generic 500 response.
    """
    logger.error(
        f"Unhandled error: {exc}",
        extra={"path": request.url.path, "method": request.method},
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )


# Root endpoint
@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "ReCall API", "version": "0.1.0"}


# Mount routers
app.include_router(captures.router, prefix="/api/captures", tags=["captures"])
app.include_router(reviews.router, prefix="/api/reviews", tags=["reviews"])
app.include_router(stats.router, prefix="/api/stats", tags=["stats"])


# TODO: Mount routers in later steps
# app.include_router(captures_router, prefix="/api/captures", tags=["captures"])
# app.include_router(reviews_router, prefix="/api/reviews", tags=["reviews"])
# app.include_router(stats_router, prefix="/api/stats", tags=["stats"])
