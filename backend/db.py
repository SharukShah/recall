"""
Database connection pool management using asyncpg.
Provides async context manager for connection lifecycle.
"""
import asyncpg
from config import settings


async def create_db_pool() -> asyncpg.Pool:
    """
    Create asyncpg connection pool.
    
    Returns:
        asyncpg.Pool: Database connection pool
    """
    pool = await asyncpg.create_pool(
        dsn=settings.DATABASE_URL,
        min_size=2,
        max_size=10,
        command_timeout=60,
    )
    return pool


async def close_db_pool(pool: asyncpg.Pool) -> None:
    """
    Close database connection pool gracefully.
    
    Args:
        pool: Database connection pool to close
    """
    await pool.close()
