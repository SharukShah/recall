# Knowledge Search — Architecture Extension
**Date:** April 18, 2026  
**Status:** Ready for implementation  
**Depends on:** pgvector installed on PostgreSQL 16 (see `pgvector-rag-implementation.md` §1)

---

## 1. System Overview

Knowledge Search adds semantic search + RAG (Retrieval-Augmented Generation) to ReCall. Users type a natural language query, the backend embeds it, finds similar facts via pgvector cosine similarity, and optionally synthesizes a natural language answer from the retrieved context using GPT-4.1-mini.

Two sub-features:
1. **Embedding pipeline extension** — embed extracted_points at capture time (extends existing `CaptureService.process()`)
2. **Search flow** — new `POST /api/knowledge/search` endpoint with full RAG pipeline

**Key design decisions:**
- Embeddings are **non-blocking**: capture succeeds even if embedding fails (NULL embedding, backfilled later)
- Single endpoint for search: always does vector retrieval + LLM synthesis (no separate `/search` vs `/query` — simplify to one)
- Pure vector search first (hybrid search with FTS is a later enhancement — schema supports it from day one)

---

## 2. Data Flow Diagram

### Flow A: Embedding at Capture Time (modified capture pipeline)

```
CaptureService.process()  [EXISTING — modifications marked with ←NEW]
│
├─ Step 1: LLM extract facts (unchanged)
│
├─ Step 2: PARALLEL  (asyncio.gather)
│   ├─ LLM generate questions     (unchanged)
│   ├─ LLM select technique       (unchanged)
│   └─ Embed all fact contents     ←NEW  embed_texts(facts)  ~200ms
│       via OpenAI text-embedding-3-small (batch, single API call)
│
├─ Step 3: DB Transaction (single transaction, unchanged boundary)
│   ├─ INSERT capture              (unchanged)
│   ├─ INSERT extracted_points     (unchanged)
│   ├─ UPDATE extracted_points     ←NEW  SET embedding = $1 WHERE id = $2
│   │   (only if embeddings_result succeeded; skip if None)
│   └─ INSERT questions            (unchanged)
│
└─ Step 4: Return response         (unchanged)

Latency impact: 0ms additional — embedding runs parallel with LLM calls (~200ms vs ~600ms)
```

### Flow B: Knowledge Search (new flow)

```
User types query              Frontend: POST /api/knowledge/search
  in search UI          →       { query, limit?, min_similarity? }
                                        │
                              ┌─────────▼─────────────────────────┐
                              │ Router: knowledge.router           │
                              │   validate request (Pydantic)      │
                              │   rate limit check (10 req/min)    │
                              └─────────┬─────────────────────────┘
                                        │
                              ┌─────────▼─────────────────────────┐
                              │ KnowledgeService.search()          │
                              │                                    │
                              │  1. EMBED QUERY                    │
                              │     embed_text(query)              │
                              │     → float[1536]                  │
                              │     ~200ms                         │
                              │                                    │
                              │  2. VECTOR SEARCH                  │
                              │     search_similar_points(         │
                              │       query_embedding,             │
                              │       limit, min_similarity)       │
                              │     → top-K rows with similarity   │
                              │     ~5-20ms (HNSW)                 │
                              │                                    │
                              │  3. DECISION: results found?       │
                              │     ├─ NO  → return no_answer      │
                              │     └─ YES → continue              │
                              │                                    │
                              │  4. CONTEXT ASSEMBLY               │
                              │     _build_context(results)        │
                              │     → numbered text + source list  │
                              │     ~0ms (string formatting)       │
                              │                                    │
                              │  5. LLM SYNTHESIS                  │
                              │     synthesize_answer(query, ctx)  │
                              │     GPT-4.1-mini                   │
                              │     → answer with [citations]      │
                              │     ~600-800ms                     │
                              │                                    │
                              │  6. RETURN                         │
                              │     { answer, sources[], has_answer│
                              │       result_count }               │
                              └───────────────────────────────────┘

Total latency: ~800ms–1.2s
OpenAI calls per search: 2 (1 embedding + 1 chat completion)
```

---

## 3. Decision Tree — Search Flow

```
POST /api/knowledge/search arrives
│
├─ VALIDATE
│   ├─ query is empty or whitespace → 422 "query is required"
│   ├─ query.length > 2000 → 422 "Query too long"
│   ├─ limit not in 1..20 → 422 (Pydantic validation)
│   └─ valid → proceed
│
├─ RATE LIMIT CHECK
│   ├─ > 10 requests/minute from this IP → 429 "Rate limit exceeded"
│   └─ under limit → proceed
│
├─ EMBED QUERY
│   ├─ OpenAI API fails → 503 "Search temporarily unavailable"
│   └─ success → query_embedding (float[1536])
│
├─ VECTOR SEARCH
│   ├─ 0 results above min_similarity threshold
│   │   └─ return { has_answer: false,
│   │              answer: "I don't have any information about that topic.",
│   │              sources: [], result_count: 0 }
│   │
│   └─ 1+ results → continue
│
├─ CONTEXT ASSEMBLY
│   ├─ Format top-K results as numbered context
│   ├─ Track token budget (max ~3000 tokens)
│   └─ Build sources list with capture_id, content, similarity, date
│
├─ LLM SYNTHESIS
│   ├─ OpenAI API fails → FALLBACK:
│   │   return { has_answer: true,
│   │            answer: "Found relevant info but couldn't synthesize. See sources below.",
│   │            sources: [...], result_count: N }
│   │   (return raw matches — still useful without synthesis)
│   │
│   └─ success → return { has_answer: true,
│                          answer: "synthesized answer with [1][2] citations",
│                          sources: [...], result_count: N }
│
└─ DONE
```

**Similarity threshold guidance:**

| Threshold | Behavior | When to use |
|-----------|----------|-------------|
| 0.2 | Very permissive — includes tangentially related | Never (too noisy) |
| **0.3** | **Balanced — default** | **Default for general search** |
| 0.5 | Strict — clearly relevant only | If user reports too many irrelevant results |
| 0.7+ | Near-exact semantic match | Not recommended (misses paraphrased content) |

---

## 4. API Contract

### `POST /api/knowledge/search`

**Rate limit:** 10 requests/minute (embeds query via OpenAI + potentially calls LLM synthesis)

#### Request

```json
{
  "query": "What did I learn about WebSockets?",
  "limit": 5,
  "min_similarity": 0.3
}
```

| Field | Type | Required | Default | Constraints |
|-------|------|----------|---------|-------------|
| `query` | string | yes | — | 1–2000 chars |
| `limit` | int | no | 5 | 1–20 |
| `min_similarity` | float | no | 0.3 | 0.0–1.0 |

#### Response — 200 (results found)

```json
{
  "answer": "You learned that WebSockets enable full-duplex communication [1] using an HTTP upgrade handshake [2].",
  "sources": [
    {
      "index": 1,
      "capture_id": "a1b2c3d4-...",
      "content": "WebSockets provide full-duplex communication over a single TCP connection.",
      "content_type": "fact",
      "similarity": 0.847,
      "captured_at": "2026-04-15T10:30:00Z"
    }
  ],
  "has_answer": true,
  "result_count": 1
}
```

#### Response — 200 (no results)

```json
{
  "answer": "I don't have any information about that topic in your knowledge base.",
  "sources": [],
  "has_answer": false,
  "result_count": 0
}
```

#### Response — 422 (validation error)

Standard FastAPI validation error body.

#### Response — 429 (rate limited)

```json
{ "detail": "Rate limit exceeded" }
```

#### Response — 503 (OpenAI down)

```json
{ "detail": "Search is temporarily unavailable. Please try again." }
```

---

## 5. File-by-File Change List

### 5.1 Schema Migration — `backend/migration_add_embeddings.sql` (NEW FILE)

```sql
CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE extracted_points
    ADD COLUMN embedding vector(1536);

ALTER TABLE extracted_points
    ADD COLUMN fts tsvector
    GENERATED ALWAYS AS (to_tsvector('english', content)) STORED;

CREATE INDEX idx_extracted_points_embedding
    ON extracted_points
    USING hnsw (embedding vector_cosine_ops)
    WHERE embedding IS NOT NULL;

CREATE INDEX idx_extracted_points_fts
    ON extracted_points
    USING gin (fts);

CREATE INDEX IF NOT EXISTS idx_extracted_points_capture
    ON extracted_points (capture_id);
```

**Why:** Adds `embedding` (vector) and `fts` (full-text search) columns to `extracted_points`. HNSW index for fast cosine similarity. GIN index for future hybrid search. `fts` is auto-generated — no app code needed. Partial index on `embedding IS NOT NULL` so unembedded rows don't waste index space.

---

### 5.2 `backend/db.py` — Register pgvector codec (MODIFY)

**What changes:**
- Add `init=_init_connection` to `create_db_pool()`
- Add `_init_connection()` function that calls `register_vector(conn)`
- This lets asyncpg send/receive `vector` type as Python lists

```python
# Add import:
from pgvector.asyncpg import register_vector

# Add init callback:
async def _init_connection(conn):
    await register_vector(conn)

# Modify create_db_pool — add init= parameter:
pool = await asyncpg.create_pool(
    dsn=settings.DATABASE_URL,
    min_size=2,
    max_size=10,
    command_timeout=60,
    init=_init_connection,
)
```

---

### 5.3 `backend/config.py` — Add embedding config (MODIFY)

**What changes:** Add configuration constants for embedding model, dimensions, and search defaults.

```python
class Settings(BaseSettings):
    # ... existing fields ...

    # Embedding
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536

    # Search defaults
    SEARCH_DEFAULT_LIMIT: int = 5
    SEARCH_MIN_SIMILARITY: float = 0.3
    SEARCH_MAX_CONTEXT_TOKENS: int = 3000
```

---

### 5.4 `backend/core/embedder.py` — Implement embedding functions (REPLACE STUB)

**What changes:** Replace placeholder with two functions: `embed_text()` (single) and `embed_texts()` (batch).

```python
"""Embedding functions using OpenAI text-embedding-3-small."""
from openai import AsyncOpenAI
from config import settings

async def embed_text(client: AsyncOpenAI, text: str) -> list[float]:
    """Embed a single text string. Returns list of 1536 floats."""
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
```

**Dependencies:** Uses `settings.EMBEDDING_MODEL` from config. Called by `CaptureService` (batch at capture) and `KnowledgeService` (single at search).

---

### 5.5 `backend/core/db_queries.py` — Add vector search query (MODIFY)

**What changes:** Add `search_similar_points()` function and `update_point_embedding()` function.

```python
async def update_point_embedding(
    pool_or_conn: PoolOrConn,
    point_id: str,
    embedding: list[float],
) -> None:
    """Set the embedding vector for an extracted_point."""
    async with await _acquire(pool_or_conn) as conn:
        await conn.execute(
            "UPDATE extracted_points SET embedding = $1 WHERE id = $2",
            embedding,
            uuid.UUID(point_id),
        )

async def search_similar_points(
    pool_or_conn: PoolOrConn,
    query_embedding: list[float],
    limit: int = 5,
    min_similarity: float = 0.3,
) -> list[dict]:
    """
    Cosine similarity search against extracted_points embeddings.
    Returns rows with similarity score, joined with capture metadata.
    """
    async with await _acquire(pool_or_conn) as conn:
        rows = await conn.fetch(
            """
            SELECT
                ep.id,
                ep.content,
                ep.content_type,
                ep.capture_id,
                ep.created_at,
                1 - (ep.embedding <=> $1::vector) AS similarity,
                c.raw_text AS capture_raw_text,
                c.source_type AS capture_source_type,
                c.created_at AS capture_created_at
            FROM extracted_points ep
            JOIN captures c ON c.id = ep.capture_id
            WHERE ep.embedding IS NOT NULL
              AND 1 - (ep.embedding <=> $1::vector) >= $3
            ORDER BY ep.embedding <=> $1::vector
            LIMIT $2
            """,
            query_embedding,
            limit,
            min_similarity,
        )
        return [dict(row) for row in rows]
```

**Note:** The `<=>` operator is pgvector's cosine distance. `1 - distance = similarity`. The `WHERE` clause filters by similarity threshold before `LIMIT`. The JOIN fetches capture metadata for source attribution.

---

### 5.6 `backend/core/llm.py` — Add `synthesize_answer()` (MODIFY)

**What changes:** Add `synthesize_answer()` function and its system prompt constant.

```python
SEARCH_SYNTHESIS_PROMPT = """You are a personal knowledge assistant. The user is searching their own captured knowledge base.

You will be given CONTEXT — numbered excerpts from the user's previously captured knowledge — and a QUESTION.

Rules:
1. Answer ONLY based on the provided context. Do not add information from your training data.
2. Cite your sources using bracket notation [1], [2], etc. matching the context numbers.
3. If the context does not contain enough information to answer, say so clearly.
4. Be concise but complete. The user captured this knowledge — help them recall it.
5. If multiple context items are relevant, synthesize them into a coherent answer."""

async def synthesize_answer(
    client: AsyncOpenAI,
    query: str,
    context: str,
) -> dict:
    """
    Generate answer from retrieved context using GPT-4.1-mini.
    Returns { answer: str, has_answer: bool }.
    """
    user_message = f"CONTEXT:\n{context}\n\nQUESTION: {query}"
    response = await client.responses.create(
        model=MODEL_MINI,
        instructions=SEARCH_SYNTHESIS_PROMPT,
        input=user_message,
        temperature=0.3,
        max_output_tokens=1000,
    )
    return {
        "answer": response.output_text,
        "has_answer": True,
    }
```

**Uses `responses.create` (not `chat.completions`)** to match the existing pattern in `llm.py`. Model: `GPT-4.1-mini` — same model used for answer evaluation (needs reasoning quality, not bulk extraction).

---

### 5.7 `backend/services/knowledge_service.py` — Replace stub with implementation (REPLACE STUB)

**What changes:** Full RAG pipeline implementation.

```python
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
        limit = limit or settings.SEARCH_DEFAULT_LIMIT
        min_similarity = min_similarity or settings.SEARCH_MIN_SIMILARITY

        # 1. Embed query (can raise — let router handle 503)
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
```

**Constructor takes `db_pool` + `openai_client`** — same pattern as `CaptureService` and `ReviewService`. No FSRS scheduler needed.

---

### 5.8 `backend/services/capture_service.py` — Add embedding step (MODIFY)

**What changes:** 
1. Import `embed_texts` from `core.embedder`
2. Add embedding to the `asyncio.gather` parallel call (Step 2)
3. Write embeddings inside the existing transaction (Step 3)

**Specific modifications:**

```python
# Add import at top:
from core.embedder import embed_texts

# In process(), after facts_dicts is built — modify the parallel section:
# ADD embed_task to asyncio.gather:
embed_task = embed_texts(self.openai, [f.content for f in extracted.facts])
questions_result, technique_result, embeddings_result = await asyncio.gather(
    questions_task, technique_task, embed_task,
    return_exceptions=True,
)

# Handle embedding failure (add after existing isinstance checks):
if isinstance(embeddings_result, Exception):
    logger.warning(f"Embedding failed: {embeddings_result}")
    embeddings_result = None

# Inside the transaction, AFTER the loop that inserts extracted_points
# and BEFORE the questions block — ADD:
if embeddings_result and len(embeddings_result) == len(point_ids):
    for point_id, embedding in zip(point_ids, embeddings_result):
        await update_point_embedding(conn, point_id, embedding)
    logger.info(f"Embedded {len(embeddings_result)} points for capture {capture_id}")
```

**Key rule:** Embedding failure does NOT fail the capture. The `embeddings_result = None` guard ensures we skip the UPDATE if the API call failed. Those points get `embedding = NULL` and are picked up by the backfill script.

---

### 5.9 `backend/models/knowledge_models.py` — Update Pydantic models (MODIFY)

**What changes:** Replace stubs with full request/response models.

```python
"""Pydantic models for knowledge search endpoints."""
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    limit: int = Field(default=5, ge=1, le=20)
    min_similarity: float = Field(default=0.3, ge=0.0, le=1.0)


class SearchSource(BaseModel):
    index: int
    capture_id: str
    content: str
    content_type: str
    similarity: float
    captured_at: str


class SearchResponse(BaseModel):
    answer: str
    sources: list[SearchSource]
    has_answer: bool
    result_count: int
```

**Changes from stub:** Added `SearchSource` model, `SearchResponse` model, `min_similarity` field on request, `content_type` on sources. Removed `KnowledgeItem` and `QueryResponse` (replaced by `SearchSource` and `SearchResponse`).

---

### 5.10 `backend/routers/knowledge.py` — NEW FILE (or modify if exists)

**What changes:** Create router with `POST /search` endpoint, rate-limited.

```python
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
```

**Rate limit:** 10 requests/minute. Each search makes 1-2 OpenAI API calls (embedding + optional synthesis), so this prevents accidental cost spikes.

---

### 5.11 `backend/main.py` — Mount knowledge router (MODIFY)

**What changes:** Add one import and one `include_router` line.

```python
# Add import:
from routers import knowledge

# Add after existing router mounts:
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["knowledge"])
```

---

### 5.12 `backend/requirements.txt` — Add pgvector (MODIFY)

**What changes:** Add `pgvector` package.

```
pgvector>=0.3.0
```

---

### 5.13 `backend/backfill_embeddings.py` — NEW FILE

One-shot script to embed existing `extracted_points` that have `embedding = NULL`. Idempotent — safe to re-run. See `pgvector-rag-implementation.md` §6 for full implementation. Process: fetch batch → embed via OpenAI API → UPDATE rows → repeat. Handles rate limits via delay between batches.

---

### 5.14 Frontend Changes

#### `frontend/types/api.ts` — Add search types (MODIFY)

```typescript
export interface SearchRequest {
  query: string;
  limit?: number;
  min_similarity?: number;
}

export interface SearchSource {
  index: number;
  capture_id: string;
  content: string;
  content_type: string;
  similarity: number;
  captured_at: string;
}

export interface SearchResponse {
  answer: string;
  sources: SearchSource[];
  has_answer: boolean;
  result_count: number;
}
```

#### `frontend/lib/api.ts` — Add search API function (MODIFY)

```typescript
export async function searchKnowledge(data: SearchRequest): Promise<SearchResponse> {
  return request<SearchResponse>("/api/knowledge/search", {
    method: "POST",
    body: JSON.stringify(data),
  });
}
```

#### `frontend/app/search/page.tsx` — NEW FILE

Search page with:
- Search input bar with submit button
- Loading state while searching
- Answer display (rendered markdown for citation brackets)
- Source cards below answer (each showing content, content_type badge, similarity %, capture date, link to `/history/{capture_id}`)
- Empty state when `has_answer: false`
- Error state for 503/429

#### `frontend/components/search/SearchBar.tsx` — NEW FILE

Controlled input + submit button. Debounce not needed (explicit submit, not typeahead).

#### `frontend/components/search/SearchResults.tsx` — NEW FILE

Renders `SearchResponse`: answer text + list of `SearchSource` cards.

#### `frontend/components/search/SourceCard.tsx` — NEW FILE

Individual source card: content snippet, content_type badge, similarity score, capture date, link to history detail.

#### `frontend/hooks/useKnowledgeSearch.ts` — NEW FILE

React hook wrapping `searchKnowledge()` with loading/error/data state management. Pattern matches existing `useReviewSession.ts`.

#### Navigation — Update `layout/DesktopSidebar.tsx` and `layout/MobileTabBar.tsx`

Add Search nav link pointing to `/search` (icon: magnifying glass). The system-design.md already shows Search in the frontend component map — this just wires it up.

---

## 6. Integration Points with Existing System

### 6.1 Capture Pipeline Integration

```
BEFORE (current):
  extract → [questions + technique] (parallel) → transaction(capture, points, questions)

AFTER:
  extract → [questions + technique + EMBEDDINGS] (parallel) → transaction(capture, points, EMBEDDINGS, questions)
                                    ↑ new                                      ↑ new
```

- **No new transactions.** Embeddings write inside the existing transaction.
- **No new error paths that break capture.** Embedding failure → `NULL` column, capture succeeds.
- **No latency increase.** Embedding (~200ms) runs parallel with question gen (~600ms).

### 6.2 Dependencies Between Components

```
embedder.py ← capture_service.py  (batch embed at capture)
embedder.py ← knowledge_service.py (single embed at search)
db_queries.py ← knowledge_service.py (search_similar_points)
db_queries.py ← capture_service.py (update_point_embedding)
llm.py ← knowledge_service.py (synthesize_answer)
knowledge_service.py ← routers/knowledge.py
rate_limiter.py ← routers/knowledge.py
```

### 6.3 Source Links in Search Results

Search results include `capture_id`. The frontend already has `/history/[id]` pages that show capture details. Source cards in search results link directly to these pages — no new backend endpoint needed for this.

---

## 7. Configuration Summary

| Config Key | Value | Location | Purpose |
|------------|-------|----------|---------|
| `EMBEDDING_MODEL` | `text-embedding-3-small` | `config.py` | OpenAI embedding model name |
| `EMBEDDING_DIMENSIONS` | `1536` | `config.py` | Vector column size (must match model) |
| `SEARCH_DEFAULT_LIMIT` | `5` | `config.py` | Default top-K results |
| `SEARCH_MIN_SIMILARITY` | `0.3` | `config.py` | Default cosine similarity threshold |
| `SEARCH_MAX_CONTEXT_TOKENS` | `3000` | `config.py` | Max tokens in LLM context window |

No new API keys needed — uses existing `OPENAI_API_KEY` for both embeddings and synthesis.

---

## 8. Cost per Search

| Operation | Model | Est. Tokens | Cost |
|-----------|-------|-------------|------|
| Embed query | text-embedding-3-small | ~20 | $0.0000004 |
| Synthesize answer | GPT-4.1-mini | ~1500 (in+out) | ~$0.0006 |
| **Total per search** | | | **~$0.0006** |
| 20 searches/day × 30 days | | | **~$0.36/month** |

---

## 9. Implementation Order

1. **Install pgvector** on PostgreSQL (see `pgvector-rag-implementation.md` §1)
2. **Run migration SQL** (`migration_add_embeddings.sql`)
3. **Add `pgvector` to `requirements.txt`** and install
4. **Modify `db.py`** — register vector codec
5. **Modify `config.py`** — add embedding/search settings
6. **Implement `core/embedder.py`** — `embed_text()` + `embed_texts()`
7. **Modify `core/db_queries.py`** — add `update_point_embedding()` + `search_similar_points()`
8. **Modify `core/llm.py`** — add `synthesize_answer()`
9. **Modify `services/capture_service.py`** — add embedding to parallel step + transaction
10. **Implement `services/knowledge_service.py`** — replace stub
11. **Update `models/knowledge_models.py`** — full request/response models
12. **Create `routers/knowledge.py`** — search endpoint with rate limiting
13. **Modify `main.py`** — mount knowledge router
14. **Run `backfill_embeddings.py`** — embed any existing extracted_points
15. **Frontend** — types, API function, search page, components, nav update

Steps 6-8 can be done in parallel (no dependencies between them). Step 9 depends on 6+7. Step 10 depends on 6+7+8. Steps 11-13 depend on 10.
