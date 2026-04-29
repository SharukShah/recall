import asyncio, asyncpg

async def main():
    c = await asyncpg.connect('postgresql://postgres:postgres@localhost:5432/recall_mvp')
    r = await c.fetchrow(
        "SELECT column_name, data_type, udt_name FROM information_schema.columns "
        "WHERE table_name='extracted_points' AND column_name='embedding'"
    )
    print("Column info:", r)
    # Also check if pgvector extension exists
    r2 = await c.fetchval("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname='vector')")
    print("pgvector installed:", r2)
    await c.close()

asyncio.run(main())
