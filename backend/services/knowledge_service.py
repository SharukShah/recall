"""Knowledge service — Phase 2 placeholder (needs embeddings/pgvector)."""
import logging

logger = logging.getLogger(__name__)


class KnowledgeService:
    """Stub — semantic search and PA queries will be implemented in Phase 2."""

    async def search(self, query: str, limit: int = 5) -> dict:
        return {"answer": "Knowledge search not yet available. Coming in Phase 2.", "sources": []}

    async def query(self, query: str) -> dict:
        return {"answer": "Knowledge query not yet available. Coming in Phase 2.", "sources": []}
