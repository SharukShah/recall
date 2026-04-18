"""Knowledge search service — semantic search + RAG synthesis."""
import logging
from openai import AsyncOpenAI
import asyncpg

from core.embedder import embed_text
from core.db_queries import search_similar_points
from core import llm
from config import settings

logger = logging.getLogger(__name__)


class KnowledgeService:
    def __init__(self, db_pool: asyncpg.Pool, openai_client: AsyncOpenAI):
        self.db_pool = db_pool
        self.openai = openai_client

    async def search(
        self,
        query: str,
        limit: int | None = None,
        min_similarity: float | None = None,
    ) -> dict:
        limit = limit if limit is not None else settings.SEARCH_DEFAULT_LIMIT
        min_similarity = min_similarity if min_similarity is not None else settings.SEARCH_MIN_SIMILARITY

        # 1. Embed query
        query_embedding = await embed_text(self.openai, query)

        # 2. Vector search
        results = await search_similar_points(
            self.db_pool, query_embedding,
            limit=limit, min_similarity=min_similarity,
        )

        # 3. No results
        if not results:
            return {
                "answer": "I don't have any information about that topic in your knowledge base.",
                "sources": [],
                "has_answer": False,
            }

        # 4. Build context
        context, sources = _build_context(results)

        # 5. LLM synthesis (fallback to raw results on failure)
        try:
            llm_response = await llm.synthesize_answer(self.openai, query, context)
        except Exception as e:
            logger.error(f"LLM synthesis failed: {e}")
            return {
                "answer": "I found relevant information but couldn't synthesize an answer. See the sources below.",
                "sources": sources,
                "has_answer": True,
            }

        return {
            "answer": llm_response["answer"],
            "sources": sources,
            "has_answer": llm_response["has_answer"],
        }


def _build_context(
    results: list[dict],
    max_tokens: int | None = None,
) -> tuple[str, list[dict]]:
    """Format search results into numbered context for LLM + build source list."""
    max_tokens = max_tokens or settings.SEARCH_MAX_CONTEXT_TOKENS
    context_parts = []
    sources = []
    estimated_tokens = 0

    for i, result in enumerate(results, 1):
        entry = (
            f"[{i}] ({result['content_type']}, "
            f"captured {result['capture_created_at'].strftime('%Y-%m-%d')}): "
            f"{result['content']}"
        )
        entry_tokens = len(entry) // 4

        if estimated_tokens + entry_tokens > max_tokens:
            break

        context_parts.append(entry)
        sources.append({
            "index": i,
            "capture_id": str(result["capture_id"]),
            "content": result["content"],
            "content_type": result["content_type"],
            "similarity": round(float(result["similarity"]), 3),
            "captured_at": result["capture_created_at"].isoformat(),
        })
        estimated_tokens += entry_tokens

    return "\n".join(context_parts), sources
