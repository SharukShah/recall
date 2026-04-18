"""Schema migration: add pgvector embedding support to extracted_points."""
import asyncio
import asyncpg


async def main():
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:5432/recall_mvp")
    try:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        await conn.execute("ALTER TABLE extracted_points ADD COLUMN IF NOT EXISTS embedding vector(1536)")
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_extracted_points_embedding
            ON extracted_points USING hnsw (embedding vector_cosine_ops)
            WHERE embedding IS NOT NULL
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_extracted_points_capture
            ON extracted_points (capture_id)
        """)
        # Verify
        version = await conn.fetchval("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
        print(f"pgvector version: {version}")
        col = await conn.fetchval(
            "SELECT 1 FROM information_schema.columns WHERE table_name='extracted_points' AND column_name='embedding'"
        )
        print(f"embedding column: {col is not None}")
        cnt = await conn.fetchval("SELECT count(*) FROM extracted_points WHERE embedding IS NULL")
        print(f"points needing embeddings: {cnt}")
    finally:
        await conn.close()


asyncio.run(main())
