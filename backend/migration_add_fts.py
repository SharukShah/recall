"""Add fts tsvector column for future hybrid search."""
import asyncio
import asyncpg


async def main():
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:5432/recall_mvp")
    try:
        await conn.execute("""
            ALTER TABLE extracted_points
            ADD COLUMN IF NOT EXISTS fts tsvector
            GENERATED ALWAYS AS (to_tsvector('english', content)) STORED
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_extracted_points_fts
            ON extracted_points USING gin (fts)
        """)
        print("fts column and GIN index added")
    finally:
        await conn.close()


asyncio.run(main())
