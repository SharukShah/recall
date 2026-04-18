"""Embedding functions using OpenAI text-embedding-3-small."""
import logging
from openai import AsyncOpenAI
from config import settings

logger = logging.getLogger(__name__)


async def embed_text(client: AsyncOpenAI, text: str) -> list[float]:
    """Embed a single text string. Returns list of floats."""
    response = await client.embeddings.create(
        model=settings.EMBEDDING_MODEL,
        input=text,
    )
    return response.data[0].embedding


async def embed_texts(client: AsyncOpenAI, texts: list[str]) -> list[list[float]]:
    """Embed multiple texts in one API call (batch). Returns list of embeddings in input order."""
    if not texts:
        return []
    response = await client.embeddings.create(
        model=settings.EMBEDDING_MODEL,
        input=texts,
    )
    sorted_data = sorted(response.data, key=lambda x: x.index)
    return [item.embedding for item in sorted_data]
