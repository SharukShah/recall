"""Backfill embeddings for existing extracted_points that have embedding = NULL."""
import asyncio
import logging
from openai import AsyncOpenAI
import asyncpg
from pgvector.asyncpg import register_vector

from config import settings
from core.embedder import embed_texts

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

BATCH_SIZE = 100


async def main():
    conn = await asyncpg.connect(dsn=settings.DATABASE_URL)
    await register_vector(conn)
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    try:
        total = await conn.fetchval(
            "SELECT count(*) FROM extracted_points WHERE embedding IS NULL"
        )
        logger.info(f"Points needing embeddings: {total}")

        if total == 0:
            logger.info("Nothing to backfill.")
            return

        processed = 0
        while True:
            rows = await conn.fetch(
                "SELECT id, content FROM extracted_points WHERE embedding IS NULL LIMIT $1",
                BATCH_SIZE,
            )
            if not rows:
                break

            texts = [r["content"] for r in rows]
            ids = [r["id"] for r in rows]

            embeddings = await embed_texts(client, texts)

            for point_id, embedding in zip(ids, embeddings):
                await conn.execute(
                    "UPDATE extracted_points SET embedding = $1 WHERE id = $2",
                    embedding, point_id,
                )

            processed += len(rows)
            logger.info(f"Backfilled {processed}/{total}")

        logger.info(f"Done. Total embedded: {processed}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
