"""Knowledge search router."""
from fastapi import APIRouter, Request, Depends, HTTPException
from core.rate_limiter import rate_limit
from models.knowledge_models import SearchRequest, SearchResponse, SearchSource
from services.knowledge_service import KnowledgeService

router = APIRouter()


@router.post("/search", response_model=SearchResponse, dependencies=[Depends(rate_limit(10))])
async def search_knowledge(body: SearchRequest, request: Request):
    """Search knowledge base using semantic similarity + RAG synthesis."""
    service = KnowledgeService(
        db_pool=request.app.state.db_pool,
        openai_client=request.app.state.openai,
    )
    try:
        result = await service.search(
            query=body.query,
            limit=body.limit,
            min_similarity=body.min_similarity,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail="Search is temporarily unavailable. Please try again.")

    return SearchResponse(
        answer=result["answer"],
        sources=[SearchSource(**s) for s in result["sources"]],
        has_answer=result["has_answer"],
        result_count=len(result["sources"]),
    )
