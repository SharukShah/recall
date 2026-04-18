import asyncio, asyncpg

async def main():
    c = await asyncpg.connect("postgresql://postgres:postgres@localhost:5432/recall_mvp")
    r = await c.fetchval("SELECT 1 FROM pg_available_extensions WHERE name='vector'")
    print("pgvector available:", r is not None)
    tables = await c.fetch("SELECT tablename FROM pg_tables WHERE schemaname='public'")
    print("Tables:", [t["tablename"] for t in tables])
    cnt = await c.fetchval("SELECT count(*) FROM extracted_points")
    print("Existing extracted_points:", cnt)
    # Check if embedding column exists
    col = await c.fetchval("SELECT 1 FROM information_schema.columns WHERE table_name='extracted_points' AND column_name='embedding'")
    print("embedding column exists:", col is not None)
    await c.close()

asyncio.run(main())
