# pgvector + RAG Implementation — Technical Brief
**Project:** ReCall — Voice-First Personal Memory Assistant  
**Date:** April 18, 2026  
**Status:** Design document for Phase 2 implementation  
**Stack:** PostgreSQL 16 (Windows, local), asyncpg, OpenAI SDK, FastAPI

---

## Table of Contents
1. [pgvector on Windows PostgreSQL 16](#1-pgvector-on-windows-postgresql-16)
2. [Schema Migration Plan](#2-schema-migration-plan)
3. [Embedding Model Selection](#3-embedding-model-selection)
4. [RAG Pipeline Design](#4-rag-pipeline-design)
5. [Embedding at Capture Time](#5-embedding-at-capture-time)
6. [Backfill Strategy](#6-backfill-strategy)
7. [Indexing: HNSW vs IVFFlat](#7-indexing-hnsw-vs-ivfflat)
8. [Hybrid Search](#8-hybrid-search)
9. [Search API Design](#9-search-api-design)
10. [Cost Estimate](#10-cost-estimate)

---

## 1. pgvector on Windows PostgreSQL 16

### The Windows Problem

pgvector is a C extension for PostgreSQL. On Linux/macOS, installation is trivial (`apt install`, `brew install`, or `make install`). On Windows, there is no package manager for PostgreSQL extensions — you must either find a pre-built binary or compile from source.

### Option A: Pre-Built Binary (Recommended)

As of 2026, the pgvector GitHub releases page includes pre-built Windows DLLs for PostgreSQL 16. This is the simplest path.

**Steps:**

1. **Download the pre-built release** from https://github.com/pgvector/pgvector/releases
   - Look for the asset matching your PostgreSQL version (e.g., `pgvector-X.X.X-pg16-windows-x64.zip`)
   - If no pre-built ZIP is available for your exact version, proceed to Option B

2. **Extract and copy files** to your PostgreSQL installation directory:
   ```powershell
   # Find your PostgreSQL install path (typically):
   # C:\Program Files\PostgreSQL\16\

   # Copy the DLL
   Copy-Item vector.dll "C:\Program Files\PostgreSQL\16\lib\"

   # Copy the SQL and control files
   Copy-Item vector.control "C:\Program Files\PostgreSQL\16\share\extension\"
   Copy-Item vector--*.sql "C:\Program Files\PostgreSQL\16\share\extension\"
   ```

3. **Restart PostgreSQL** (required after adding new extensions):
   ```powershell
   # Via Windows Services
   Restart-Service postgresql-x64-16

   # Or via pg_ctl
   & "C:\Program Files\PostgreSQL\16\bin\pg_ctl" restart -D "C:\Program Files\PostgreSQL\16\data"
   ```

4. **Enable the extension** in your database:
   ```sql
   -- Connect to recall_mvp
   CREATE EXTENSION IF NOT EXISTS vector;
   
   -- Verify
   SELECT extversion FROM pg_extension WHERE extname = 'vector';
   ```

### Option B: Build from Source with Visual Studio

If no pre-built binary matches your setup, you can compile pgvector from source.

**Prerequisites:**
- Visual Studio 2022 (Community edition is fine) with "Desktop development with C++" workload
- PostgreSQL 16 development headers (included in standard PostgreSQL Windows installer)
- Git

**Steps:**

1. **Open the Visual Studio "x64 Native Tools Command Prompt"** (search in Start Menu — it must be the x64 variant).

2. **Set PostgreSQL paths:**
   ```cmd
   set "PGROOT=C:\Program Files\PostgreSQL\16"
   ```

3. **Clone and build pgvector:**
   ```cmd
   cd %TEMP%
   git clone --branch v0.8.0 https://github.com/pgvector/pgvector.git
   cd pgvector

   nmake /F Makefile.win
   nmake /F Makefile.win install
   ```

   The `Makefile.win` that ships with pgvector handles finding the PostgreSQL headers and libs via `PGROOT`. The build produces `vector.dll` and copies it plus the SQL files into the correct directories.

4. **Restart PostgreSQL and enable** (same as Option A steps 3–4).

**Common build errors on Windows:**

| Error | Cause | Fix |
|-------|-------|-----|
| `cl.exe not found` | Not using VS Native Tools prompt | Open "x64 Native Tools Command Prompt for VS 2022" |
| `Cannot open include file: 'postgres.h'` | `PGROOT` not set or wrong path | Verify `%PGROOT%\include\server\postgres.h` exists |
| `LINK : fatal error LNK1181: cannot open input file 'postgres.lib'` | Missing dev files | Reinstall PostgreSQL with "Development" component selected |
| `nmake not found` | Wrong shell | Must use VS command prompt, not PowerShell |

### Option C: Use pgvector via Docker (Alternative)

If Windows native installation proves painful, run PostgreSQL + pgvector in Docker:

```powershell
docker run -d --name recall-db `
  -e POSTGRES_DB=recall_mvp `
  -e POSTGRES_PASSWORD=your_password `
  -p 5432:5432 `
  -v recall_pgdata:/var/lib/postgresql/data `
  pgvector/pgvector:pg16
```

This image comes with pgvector pre-installed. Update your `DATABASE_URL` to point at the container. This is the zero-friction path if native Windows installation is problematic, but adds Docker as a dependency.

### Recommendation

**Try Option A first** (pre-built binary). If unavailable for your exact version, **Option B** (build from source) is reliable with the correct Visual Studio setup. **Option C** (Docker) is the escape hatch if you hit issues with native builds. For a personal dev machine, all three are viable.

### Verifying the Installation

After enabling the extension, verify it works:

```sql
-- Test vector operations
SELECT '[1,2,3]'::vector;
SELECT '[1,2,3]'::vector <=> '[4,5,6]'::vector AS cosine_distance;

-- Check version
SELECT extversion FROM pg_extension WHERE extname = 'vector';
-- Should return '0.8.0' or similar
```

---

## 2. Schema Migration Plan

### Migration SQL

Run this against `recall_mvp` after pgvector is installed:

```sql
-- ============================================================
-- Migration: Add pgvector embeddings to extracted_points
-- Prerequisite: pgvector extension installed
-- ============================================================

-- Step 1: Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Step 2: Add embedding column to extracted_points
-- Using 1536 dimensions (text-embedding-3-small default)
ALTER TABLE extracted_points
    ADD COLUMN embedding vector(1536);

-- Step 3: Add full-text search column (for hybrid search later)
ALTER TABLE extracted_points
    ADD COLUMN fts tsvector
    GENERATED ALWAYS AS (to_tsvector('english', content)) STORED;

-- Step 4: Create HNSW index on embeddings
-- Using cosine distance operator class (best for OpenAI normalized embeddings)
-- Only indexes rows WHERE embedding IS NOT NULL (partial index)
CREATE INDEX idx_extracted_points_embedding
    ON extracted_points
    USING hnsw (embedding vector_cosine_ops)
    WHERE embedding IS NOT NULL;

-- Step 5: Create GIN index for full-text search
CREATE INDEX idx_extracted_points_fts
    ON extracted_points
    USING gin (fts);

-- Step 6: Add index on capture_id for fast JOINs during context assembly
-- (captures table already has idx_captures_created)
CREATE INDEX IF NOT EXISTS idx_extracted_points_capture
    ON extracted_points (capture_id);
```

### Why These Choices

| Decision | Rationale |
|----------|-----------|
| `vector(1536)` | Matches `text-embedding-3-small` default output. Fixed dimension enforces consistency. |
| `WHERE embedding IS NOT NULL` partial index | Existing rows have no embeddings yet. Index only includes embedded rows, saves space during backfill. |
| `GENERATED ALWAYS AS` for fts | Auto-updated on INSERT/UPDATE — no application code needed. |
| HNSW over IVFFlat | Can build on empty table. Better recall at small scale. See §7. |
| `vector_cosine_ops` | OpenAI embeddings are normalized, so cosine distance is the standard choice. `<=>` operator. |

### Rollback SQL

```sql
-- If you need to undo the migration:
DROP INDEX IF EXISTS idx_extracted_points_embedding;
DROP INDEX IF EXISTS idx_extracted_points_fts;
ALTER TABLE extracted_points DROP COLUMN IF EXISTS fts;
ALTER TABLE extracted_points DROP COLUMN IF EXISTS embedding;
-- DROP EXTENSION vector;  -- only if no other tables use it
```

### asyncpg: Registering the vector type

asyncpg doesn't know about the `vector` type natively. You must register a custom codec so you can pass Python lists and receive them back:

```python
# Add to backend/db.py — codec registration

import numpy as np
from pgvector.asyncpg import register_vector

async def create_db_pool() -> asyncpg.Pool:
    pool = await asyncpg.create_pool(
        dsn=settings.DATABASE_URL,
        min_size=2,
        max_size=10,
        command_timeout=60,
        init=_init_connection,  # <-- register vector on each connection
    )
    return pool

async def _init_connection(conn: asyncpg.Connection):
    """Register pgvector type codec on each new connection."""
    await register_vector(conn)
```

This requires the `pgvector` Python package:
```
pip install pgvector
```

With the codec registered, you can pass embeddings as Python lists and receive them back as numpy arrays:

```python
# Inserting
await conn.execute(
    "UPDATE extracted_points SET embedding = $1 WHERE id = $2",
    embedding_list,  # plain Python list of floats
    point_id,
)

# Querying
rows = await conn.fetch(
    "SELECT id, content, embedding <=> $1 AS distance FROM extracted_points ORDER BY embedding <=> $1 LIMIT $2",
    query_embedding,  # plain Python list of floats
    limit,
)
```

---

## 3. Embedding Model Selection

### Head-to-Head: text-embedding-3-small vs text-embedding-3-large

| Attribute | text-embedding-3-small | text-embedding-3-large |
|-----------|----------------------|----------------------|
| **Default dimensions** | 1536 | 3072 |
| **Reducible to** | Any lower (e.g. 512, 256) | Any lower (e.g. 1536, 1024, 512) |
| **MTEB score (full dim)** | 62.3% | 64.6% |
| **MTEB score at 512 dim** | ~61% | ~62.5% |
| **Cost per 1M tokens** | $0.02 | $0.13 |
| **Cost ratio** | 1× | 6.5× |
| **Max input tokens** | 8,191 | 8,191 |
| **Normalized output** | Yes | Yes |
| **Matryoshka support** | Yes (`dimensions` param) | Yes (`dimensions` param) |

### Quality vs Cost at ReCall's Scale

For a personal app with <10K records:

| Scenario | 3-small (1536d) | 3-large (3072d) | 3-large (1536d reduced) |
|----------|-----------------|-----------------|------------------------|
| Embed 500 points/month (~100K tokens) | $0.002 | $0.013 | $0.013 |
| 20 searches/day (~12K tokens/month) | $0.0002 | $0.0016 | $0.0016 |
| **Monthly embedding cost** | **~$0.003** | **~$0.015** | **~$0.015** |
| Storage for 5K vectors | ~29 MB | ~59 MB | ~29 MB |
| Index memory | ~35 MB | ~70 MB | ~35 MB |

At these costs, both are essentially free. The real question is: **does the 2.3% MTEB improvement matter for your use case?**

### Recommendation: `text-embedding-3-small` at 1536 dimensions

**Use `text-embedding-3-small` with its default 1536 dimensions.** Here's why:

1. **Quality is sufficient.** At <10K records in a personal knowledge base, retrieval quality is bounded by the quality of your data (extracted facts), not the embedding model. The 2.3% MTEB difference between small and large is a benchmark average across diverse datasets — for short, focused knowledge facts (your typical extracted_point is 1-3 sentences), the gap is negligible.

2. **Cost is already negligible.** At $0.003/month, optimizing further (e.g., 512 dims to save storage) adds complexity for zero practical benefit. 29 MB of vectors is nothing on a local PostgreSQL instance with gigabytes of free disk.

3. **No dimension reduction needed.** Reducing dimensions trades quality for storage savings. With <10K records on a local database, you have no storage pressure. Keep the full 1536 dimensions for maximum retrieval quality.

4. **Simpler migration path.** If you ever want to upgrade to `text-embedding-3-large`, you'd re-embed everything anyway. Starting with `3-small` at full dimensions gives you a clean baseline and the cheapest possible re-embedding cost if needed.

### Using the `dimensions` parameter (future option)

If you later want to reduce dimensions (e.g., for a mobile sync scenario):

```python
response = await openai_client.embeddings.create(
    model="text-embedding-3-small",
    input="Your text here",
    dimensions=512,  # Reduce from 1536 → 512
)
```

**Warning:** You cannot mix dimensions within a single column. If you change dimensions, you must re-embed ALL existing records and alter the column type (`ALTER TABLE ... ALTER COLUMN embedding TYPE vector(512)`). Choose once and stick with it.

---

## 4. RAG Pipeline Design

### End-to-End Flow

```
User Query: "What did I learn about WebSockets?"
    │
    ▼
┌─────────────────────────────────────┐
│ 1. EMBED QUERY                      │
│    text-embedding-3-small(query)    │
│    → [0.012, -0.034, ..., 0.089]    │
│    Latency: ~200ms                  │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 2. VECTOR SIMILARITY SEARCH         │
│    SELECT content, capture_id,      │
│      1 - (embedding <=> $1) AS sim  │
│    FROM extracted_points            │
│    WHERE embedding IS NOT NULL      │
│    ORDER BY embedding <=> $1        │
│    LIMIT 10                         │
│    Latency: ~5-20ms (with HNSW)     │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 3. SCORE THRESHOLD FILTER           │
│    Keep results where               │
│    similarity >= 0.3                │
│    (cosine similarity, not distance)│
│    If 0 results pass → go to step 6│
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 4. CONTEXT ASSEMBLY                 │
│    For each result:                 │
│    • Fetch parent capture metadata  │
│    • Format as numbered context     │
│    • Track source capture IDs       │
│    Max context: ~3000 tokens        │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 5. LLM ANSWER GENERATION           │
│    GPT-4.1-mini with:              │
│    • System: "Answer from KB"       │
│    • User: context + query          │
│    • Structured output with         │
│      answer + source citations      │
│    Latency: ~600-800ms              │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 6. RESPONSE                         │
│    { answer, sources[], confidence }│
│    If no results: "I don't have     │
│    information about that topic."   │
└─────────────────────────────────────┘

Total latency: ~800ms-1.2s
```

### Step-by-Step Implementation

#### Step 1: Embed the Query

```python
# backend/core/embedder.py

from openai import AsyncOpenAI

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536


async def embed_text(client: AsyncOpenAI, text: str) -> list[float]:
    """Embed a single text string. Returns list of floats."""
    response = await client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
    )
    return response.data[0].embedding


async def embed_texts(client: AsyncOpenAI, texts: list[str]) -> list[list[float]]:
    """Embed multiple texts in a single API call (batch). Returns list of embeddings."""
    if not texts:
        return []
    response = await client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts,
    )
    # Sort by index to ensure order matches input
    sorted_data = sorted(response.data, key=lambda x: x.index)
    return [item.embedding for item in sorted_data]
```

#### Step 2: Vector Similarity Search

```python
# backend/core/db_queries.py — add this query

async def search_similar_points(
    pool_or_conn: PoolOrConn,
    query_embedding: list[float],
    limit: int = 10,
    min_similarity: float = 0.3,
) -> list[dict]:
    """
    Search extracted_points by cosine similarity to query embedding.
    Returns points with similarity score, ordered by relevance.
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

**Why `min_similarity = 0.3`?** OpenAI embeddings tend to have relatively high cosine similarity even for unrelated content (often 0.1–0.2 for random pairs). A threshold of 0.3 filters out noise while keeping loosely relevant results. You can tune this:

| Threshold | Behavior |
|-----------|----------|
| 0.2 | Very permissive — includes tangentially related content |
| 0.3 | Balanced — good default for personal KB |
| 0.5 | Strict — only clearly relevant results |
| 0.7+ | Very strict — near-exact semantic match only |

#### Step 3: Context Assembly

```python
# backend/services/knowledge_service.py

def _build_context(results: list[dict], max_tokens: int = 3000) -> tuple[str, list[dict]]:
    """
    Format search results into a numbered context string for the LLM.
    Returns (context_string, source_list_for_citations).
    
    Rough token estimate: 1 token ≈ 4 characters.
    """
    context_parts = []
    sources = []
    estimated_tokens = 0

    for i, result in enumerate(results, 1):
        # Build a context entry with metadata
        entry = (
            f"[{i}] ({result['content_type']}, "
            f"captured {result['capture_created_at'].strftime('%Y-%m-%d')}): "
            f"{result['content']}"
        )
        entry_tokens = len(entry) // 4  # rough estimate

        if estimated_tokens + entry_tokens > max_tokens:
            break

        context_parts.append(entry)
        sources.append({
            "index": i,
            "capture_id": str(result["capture_id"]),
            "content": result["content"],
            "similarity": round(result["similarity"], 3),
            "captured_at": result["capture_created_at"].isoformat(),
        })
        estimated_tokens += entry_tokens

    return "\n".join(context_parts), sources
```

#### Step 4: LLM Answer Generation

```python
# backend/core/llm.py — add this function

SEARCH_SYSTEM_PROMPT = """You are a personal knowledge assistant. The user is searching their own captured knowledge base.

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
    Generate an answer from retrieved context using GPT-4.1-mini.
    Returns { answer: str, has_answer: bool }.
    """
    if not context:
        return {
            "answer": "I don't have any information about that in your knowledge base.",
            "has_answer": False,
        }

    user_message = f"CONTEXT:\n{context}\n\nQUESTION: {query}"

    response = await client.chat.completions.create(
        model=MODEL_MINI,
        messages=[
            {"role": "system", "content": SEARCH_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.3,
        max_tokens=1000,
    )
    answer = response.choices[0].message.content
    return {
        "answer": answer,
        "has_answer": True,
    }
```

#### Step 5: "No Results" Handling

```python
# In KnowledgeService.search():

async def search(self, query: str, limit: int = 5) -> dict:
    # Embed
    query_embedding = await embed_text(self.openai, query)
    
    # Search
    results = await search_similar_points(self.db_pool, query_embedding, limit=limit)
    
    if not results:
        return {
            "answer": "I don't have any information about that in your knowledge base. "
                      "Try capturing some knowledge about this topic first!",
            "sources": [],
            "has_answer": False,
        }
    
    # Build context and generate answer
    context, sources = _build_context(results)
    llm_response = await synthesize_answer(self.openai, query, context)
    
    return {
        "answer": llm_response["answer"],
        "sources": sources,
        "has_answer": llm_response["has_answer"],
    }
```

### Full KnowledgeService Implementation

```python
# backend/services/knowledge_service.py

import logging
from openai import AsyncOpenAI
import asyncpg

from core.embedder import embed_text
from core.db_queries import search_similar_points
from core import llm

logger = logging.getLogger(__name__)


class KnowledgeService:
    def __init__(self, db_pool: asyncpg.Pool, openai_client: AsyncOpenAI):
        self.db_pool = db_pool
        self.openai = openai_client

    async def search(self, query: str, limit: int = 5, min_similarity: float = 0.3) -> dict:
        """
        Full RAG search: embed query → vector search → LLM synthesis → response.
        """
        # 1. Embed the query
        try:
            query_embedding = await embed_text(self.openai, query)
        except Exception as e:
            logger.error(f"Failed to embed query: {e}")
            return {
                "answer": "Search is temporarily unavailable. Please try again.",
                "sources": [],
                "has_answer": False,
            }

        # 2. Vector similarity search
        results = await search_similar_points(
            self.db_pool,
            query_embedding,
            limit=limit,
            min_similarity=min_similarity,
        )

        # 3. Handle no results
        if not results:
            return {
                "answer": "I don't have any information about that topic in your knowledge base.",
                "sources": [],
                "has_answer": False,
            }

        # 4. Build context
        context, sources = _build_context(results)

        # 5. LLM synthesis
        try:
            llm_response = await llm.synthesize_answer(self.openai, query, context)
        except Exception as e:
            logger.error(f"LLM synthesis failed: {e}")
            # Fallback: return raw results without synthesis
            return {
                "answer": "I found relevant information but couldn't synthesize an answer. "
                          "Here are the matching facts from your knowledge base.",
                "sources": sources,
                "has_answer": True,
            }

        return {
            "answer": llm_response["answer"],
            "sources": sources,
            "has_answer": llm_response["has_answer"],
        }


def _build_context(results: list[dict], max_tokens: int = 3000) -> tuple[str, list[dict]]:
    """Format search results into numbered context for LLM."""
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
            "similarity": round(float(result["similarity"]), 3),
            "captured_at": result["capture_created_at"].isoformat(),
        })
        estimated_tokens += entry_tokens

    return "\n".join(context_parts), sources
```

---

## 5. Embedding at Capture Time

### Where to Hook In

The capture pipeline in `capture_service.py` currently follows this flow:

```
LLM extract → LLM questions+technique (parallel) → DB transaction (capture + points + questions)
```

Embeddings should be generated **inside the transaction, after storing extracted points**, and can run in parallel with other operations.

### Modified Capture Flow

```
LLM extract facts
    │
    ├── LLM generate questions (parallel)
    ├── LLM select technique (parallel)  
    │
    ▼
DB Transaction:
    1. Insert capture
    2. Insert extracted_points (get point_ids + content)
    3. Embed all point contents in one batch API call   ←── NEW
    4. UPDATE extracted_points SET embedding = ...       ←── NEW
    5. Insert questions
```

### Implementation

```python
# In CaptureService.process(), inside the transaction block, after inserting points:

# --- NEW: Batch embed all extracted points ---
point_contents = [fact.content for fact in extracted.facts]
try:
    embeddings = await embed_texts(self.openai, point_contents)
    # Update each point with its embedding
    for point_id, embedding in zip(point_ids, embeddings):
        await conn.execute(
            "UPDATE extracted_points SET embedding = $1 WHERE id = $2",
            embedding,
            uuid.UUID(point_id),
        )
    logger.info(f"Embedded {len(embeddings)} points for capture {capture_id}")
except Exception as e:
    logger.warning(f"Embedding failed for capture {capture_id}: {e}")
    # Capture still succeeds — embeddings can be backfilled later
```

### Key Design Decisions

**1. Batch vs Individual Embedding Calls**

Use **batch** (`embed_texts`). The OpenAI embedding API accepts up to 2048 inputs in a single call. A typical capture has 2-5 extracted points — always fits in one batch call. This saves latency (one round-trip instead of 2-5) and reduces rate limit pressure.

**2. Should capture fail if embedding fails?**

**No.** Embedding is a Phase 2 enhancement — the core value of capture (extraction + questions + FSRS) must not break. If the embedding API call fails:

- Log a warning
- The capture succeeds with `embedding = NULL`
- Backfill script (see §6) picks it up later
- Search just won't include this point until it's embedded

This is defensive design. Possible failure modes:
- OpenAI API rate limit → transient, backfill catches it
- OpenAI API down → rare, same approach
- Network error → same approach
- Invalid input (empty string) → guard against this: skip embedding for empty content

**3. Embedding inside vs outside the transaction**

Embed **inside the transaction** is fine here. The embedding API call takes ~200ms, and the transaction holds a connection for that duration. At personal scale with a single user, this is not a concern. For high-concurrency, you'd embed outside the transaction and update afterwards, but that adds complexity for no benefit here.

**4. Parallelization with questions/technique**

The embedding call (~200ms) can run **in parallel** with LLM question generation (~600ms) and technique selection (~400ms). Since questions don't depend on embeddings and vice versa, add the embedding call to the `asyncio.gather`:

```python
# Modified parallel section in CaptureService.process():
questions_task = llm.generate_questions(self.openai, facts_dicts)
technique_task = llm.select_technique(self.openai, facts_dicts)
embed_task = embed_texts(self.openai, [f.content for f in extracted.facts])

questions_result, technique_result, embeddings_result = await asyncio.gather(
    questions_task, technique_task, embed_task,
    return_exceptions=True,
)

if isinstance(embeddings_result, Exception):
    logger.warning(f"Embedding failed: {embeddings_result}")
    embeddings_result = None
```

Then inside the transaction, after inserting points, write the embeddings if available:

```python
if embeddings_result and len(embeddings_result) == len(point_ids):
    for point_id, embedding in zip(point_ids, embeddings_result):
        await conn.execute(
            "UPDATE extracted_points SET embedding = $1 WHERE id = $2",
            embedding,
            uuid.UUID(point_id),
        )
```

This adds **0ms extra latency** to the capture pipeline — the embedding runs concurrently with the already-required LLM calls.

---

## 6. Backfill Strategy

### When Backfill Is Needed

- Existing extracted_points from Phase 1 have `embedding = NULL`
- Failed embedding during capture (network error, rate limit)
- Re-embedding after model change or dimension change

### Backfill Script

```python
# backend/backfill_embeddings.py

"""
One-shot script to backfill embeddings for extracted_points that have NULL embedding.
Run with: python backfill_embeddings.py
"""
import asyncio
import logging
import time
from openai import AsyncOpenAI
import asyncpg

from config import settings
from core.embedder import embed_texts

# pgvector registration
from pgvector.asyncpg import register_vector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BATCH_SIZE = 100  # OpenAI can handle up to 2048 inputs; 100 is conservative
DELAY_BETWEEN_BATCHES = 0.5  # seconds — respect rate limits


async def backfill():
    openai = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    conn = await asyncpg.connect(dsn=settings.DATABASE_URL)
    await register_vector(conn)

    # Count total to backfill
    total = await conn.fetchval(
        "SELECT COUNT(*) FROM extracted_points WHERE embedding IS NULL"
    )
    logger.info(f"Found {total} points without embeddings")

    if total == 0:
        logger.info("Nothing to backfill!")
        await conn.close()
        return

    processed = 0
    errors = 0

    while True:
        # Fetch next batch
        rows = await conn.fetch(
            """
            SELECT id, content
            FROM extracted_points
            WHERE embedding IS NULL
            ORDER BY created_at ASC
            LIMIT $1
            """,
            BATCH_SIZE,
        )

        if not rows:
            break

        # Extract texts
        ids = [row["id"] for row in rows]
        texts = [row["content"] for row in rows]

        # Skip empty content
        valid = [(id_, text) for id_, text in zip(ids, texts) if text and text.strip()]
        if not valid:
            continue

        valid_ids, valid_texts = zip(*valid)

        try:
            embeddings = await embed_texts(openai, list(valid_texts))

            # Update in a transaction
            async with conn.transaction():
                for id_, embedding in zip(valid_ids, embeddings):
                    await conn.execute(
                        "UPDATE extracted_points SET embedding = $1 WHERE id = $2",
                        embedding,
                        id_,
                    )

            processed += len(valid_ids)
            logger.info(f"Progress: {processed}/{total} ({100*processed//total}%)")

        except Exception as e:
            errors += 1
            logger.error(f"Batch failed: {e}")
            if errors > 5:
                logger.error("Too many errors, stopping.")
                break

        # Rate limit courtesy
        await asyncio.sleep(DELAY_BETWEEN_BATCHES)

    logger.info(f"Backfill complete: {processed} embedded, {errors} batch errors")
    await conn.close()


if __name__ == "__main__":
    asyncio.run(backfill())
```

### Backfill Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `BATCH_SIZE` | 100 | Well under OpenAI's 2048 limit. Each batch ≈ 100 × 50 tokens = 5K tokens ≈ $0.0001. Keeps API calls small and retryable. |
| `DELAY_BETWEEN_BATCHES` | 0.5s | Prevents hitting OpenAI Tier 1 rate limits (500 RPM for embeddings). At 0.5s delay, we make 120 requests/min max. |
| Error threshold | 5 consecutive batch errors | Stops the script if the API is persistently down rather than burning through retries. |

### Rate Limit Considerations

OpenAI embedding rate limits (Tier 1):

| Limit | Value |
|-------|-------|
| Requests per minute | 500 RPM |
| Tokens per minute | 1,000,000 TPM |
| Requests per day | 10,000 RPD |

For backfilling 500 existing points at batch size 100 = 5 API calls. This completes in under 5 seconds. Even 10,000 points = 100 batches = ~50 seconds. Rate limits will not be an issue at this scale.

### Progress Tracking

The script uses the `embedding IS NULL` condition as its progress tracker — re-running the script after a failure safely picks up where it left off (idempotent). No separate progress table needed.

---

## 7. Indexing: HNSW vs IVFFlat

### Core Differences

| Attribute | HNSW | IVFFlat |
|-----------|------|---------|
| **Algorithm** | Hierarchical Navigable Small World graph | Inverted File Index with flat quantization |
| **Build on empty table?** | Yes | No — needs data first to compute centroids |
| **Build time** | Slower (but irrelevant at <10K) | Faster |
| **Query time** | Faster, better recall | Slower, lower recall |
| **Memory usage** | Higher (stores graph) | Lower |
| **Update cost** | Moderate | Low (just add to a list) |
| **Index rebuild needed?** | No | Yes, after significant data changes |
| **Tunable parameters** | `m`, `ef_construction`, `ef_search` | `lists`, `probes` |

### Do You Even Need an Index at <10K Records?

**Technically, no.** PostgreSQL performs a sequential scan on `extracted_points` for vector operations without an index. At 5,000 rows × 1536 dimensions:

- **Sequential scan (no index):** ~10-30ms on modern hardware
- **HNSW index:** ~1-3ms

For a personal app where search latency of 30ms vs 3ms is imperceptible (the LLM call takes 600ms+), an index is not strictly necessary. However:

**Create the HNSW index anyway.** The reasons:
1. It's one SQL statement — zero maintenance cost
2. Build time for 5K vectors is <1 second
3. It future-proofs you as data grows
4. It enables the `WHERE embedding IS NOT NULL` partial index pattern, which is useful during backfill
5. PostgreSQL query planner makes better decisions with an index present

### Recommended HNSW Parameters

```sql
CREATE INDEX idx_extracted_points_embedding
    ON extracted_points
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64)
    WHERE embedding IS NOT NULL;

-- At query time, set search quality:
SET hnsw.ef_search = 40;  -- default, fine for <10K records
```

| Parameter | Default | What It Controls | Recommendation for <10K |
|-----------|---------|-----------------|------------------------|
| `m` | 16 | Max connections per node in the graph. Higher = better recall, more memory. | **16** (default). At <10K records, even `m=8` would work fine. |
| `ef_construction` | 64 | Search width during index build. Higher = better quality index, slower build. | **64** (default). Build takes <1s regardless. |
| `ef_search` | 40 | Search width at query time. Higher = better recall, slower query. | **40** (default). Increase to 100 only if you notice missed results. |

### When to Consider IVFFlat

**Never, at this scale.** IVFFlat's advantage is faster build time at large scale (millions of vectors). Below 100K vectors, HNSW dominates on every metric. The pgvector documentation itself recommends HNSW as the default.

The only scenario for IVFFlat: if you had >1M vectors and needed to rebuild the index frequently (e.g., after bulk deletes). Not applicable to ReCall.

### Index Size Estimate

For 10K vectors at 1536 dimensions with HNSW (m=16):

$$\text{Index size} \approx n \times d \times 4 + n \times m \times 2 \times 8$$

$$= 10{,}000 \times 1{,}536 \times 4 + 10{,}000 \times 16 \times 2 \times 8$$

$$= 61.4\text{MB} + 2.56\text{MB} = \sim64\text{MB}$$

This fits comfortably in memory on any machine.

---

## 8. Hybrid Search

### When Hybrid Search Helps

| Scenario | Pure Vector | Hybrid (Vector + FTS) |
|----------|-------------|----------------------|
| "What did I learn about WebSockets?" | ✅ Great | ✅ Great |
| "Error code ECONNREFUSED" | ❌ Misses — model doesn't understand error codes well | ✅ Keyword match finds it |
| "Notes from April 10th" | ❌ Dates aren't semantic | ⚠️ FTS doesn't search dates either — use SQL filter |
| "JavaScript vs Python comparison" | ✅ Good | ✅ Good (boosted by keyword match) |
| "meetings with Sarah" | ❌ Names embed poorly | ✅ Keyword match finds "Sarah" |
| Typos in query | ✅ Embeddings are typo-tolerant | ❌ FTS requires exact match |

**Bottom line:** Hybrid search is most valuable when queries contain proper nouns, technical terms, error codes, or specific identifiers that embedding models handle poorly. For a personal knowledge base, this is common enough to be worth implementing.

### Implementation: Reciprocal Rank Fusion (RRF)

RRF combines rankings from two search methods without needing to normalize scores across different scales.

$$\text{RRF}(d) = \sum_{r \in R} \frac{1}{k + r(d)}$$

where $k$ is a constant (typically 60), $R$ is the set of rankers, and $r(d)$ is the rank of document $d$ in ranker $r$.

```sql
-- backend/schema.sql — hybrid search function

CREATE OR REPLACE FUNCTION hybrid_search(
    query_text TEXT,
    query_embedding vector(1536),
    match_count INT DEFAULT 5,
    text_weight FLOAT DEFAULT 1.0,
    vector_weight FLOAT DEFAULT 1.0,
    rrf_k INT DEFAULT 60
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    content_type TEXT,
    capture_id UUID,
    created_at TIMESTAMPTZ,
    rrf_score FLOAT
)
LANGUAGE sql STABLE
AS $$
WITH vector_search AS (
    SELECT
        ep.id,
        row_number() OVER (ORDER BY ep.embedding <=> query_embedding) AS rank_ix
    FROM extracted_points ep
    WHERE ep.embedding IS NOT NULL
    ORDER BY ep.embedding <=> query_embedding
    LIMIT LEAST(match_count * 4, 100)
),
text_search AS (
    SELECT
        ep.id,
        row_number() OVER (ORDER BY ts_rank_cd(ep.fts, websearch_to_tsquery('english', query_text)) DESC) AS rank_ix
    FROM extracted_points ep
    WHERE ep.fts @@ websearch_to_tsquery('english', query_text)
    ORDER BY rank_ix
    LIMIT LEAST(match_count * 4, 100)
)
SELECT
    ep.id,
    ep.content,
    ep.content_type,
    ep.capture_id,
    ep.created_at,
    (
        COALESCE(1.0 / (rrf_k + vs.rank_ix), 0.0) * vector_weight +
        COALESCE(1.0 / (rrf_k + ts.rank_ix), 0.0) * text_weight
    ) AS rrf_score
FROM vector_search vs
FULL OUTER JOIN text_search ts ON vs.id = ts.id
JOIN extracted_points ep ON COALESCE(vs.id, ts.id) = ep.id
ORDER BY rrf_score DESC
LIMIT match_count;
$$;
```

### Using Hybrid Search from Python

```python
# backend/core/db_queries.py — add hybrid search query

async def hybrid_search_points(
    pool_or_conn: PoolOrConn,
    query_text: str,
    query_embedding: list[float],
    limit: int = 5,
) -> list[dict]:
    """
    Hybrid search combining vector similarity and full-text search via RRF.
    Falls back gracefully if query_text produces no FTS matches.
    """
    async with await _acquire(pool_or_conn) as conn:
        rows = await conn.fetch(
            """
            SELECT hs.*, c.raw_text AS capture_raw_text,
                   c.source_type AS capture_source_type,
                   c.created_at AS capture_created_at
            FROM hybrid_search($1, $2::vector, $3) hs
            JOIN captures c ON c.id = hs.capture_id
            """,
            query_text,
            query_embedding,
            limit,
        )
        return [dict(row) for row in rows]
```

### When to Use Which

```python
# In KnowledgeService.search():

async def search(self, query: str, limit: int = 5, min_similarity: float = 0.3) -> dict:
    query_embedding = await embed_text(self.openai, query)

    # Use hybrid search by default — it's never worse than pure vector
    results = await hybrid_search_points(
        self.db_pool, query, query_embedding, limit=limit,
    )

    # ... rest of pipeline (context assembly → LLM synthesis)
```

**Recommendation:** Use hybrid search as the default. It never degrades results compared to pure vector search (the RRF fusion gracefully handles the case where FTS returns no matches — vector results still surface). The only cost is a slightly more complex query, which at this scale adds negligible latency.

### Phased Approach

1. **Phase 2a:** Implement pure vector search first (simpler, faster to ship)
2. **Phase 2b:** Add the `fts` column and `hybrid_search` function
3. **Phase 2c:** Switch the search service to use hybrid by default

The `fts` column is added in the migration SQL (§2), so the schema is ready from day one. You just switch the query function when ready.

---

## 9. Search API Design

### Endpoint: `POST /api/knowledge/search`

Using POST (not GET) because the query may be long (voice transcription) and we want a JSON body.

### Request

```json
POST /api/knowledge/search
Content-Type: application/json

{
    "query": "What did I learn about WebSockets?",
    "limit": 5,
    "min_similarity": 0.3
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `query` | string (required) | — | The search query. 1–500 characters. |
| `limit` | integer | 5 | Max results to retrieve. Range: 1–20. |
| `min_similarity` | float | 0.3 | Minimum cosine similarity threshold. Range: 0.0–1.0. |

### Response — Success with Results

```json
{
    "answer": "You learned that WebSockets enable full-duplex communication between client and server over a single TCP connection [1]. They use an HTTP upgrade handshake to establish the connection [2], and are ideal for real-time apps like chat and live updates [1][3].",
    "sources": [
        {
            "index": 1,
            "capture_id": "a1b2c3d4-...",
            "content": "WebSockets provide full-duplex communication channels over a single TCP connection, ideal for real-time applications.",
            "similarity": 0.847,
            "captured_at": "2026-04-15T10:30:00Z"
        },
        {
            "index": 2,
            "capture_id": "e5f6g7h8-...",
            "content": "WebSocket connections start as an HTTP request with an Upgrade header, then switch protocols.",
            "similarity": 0.791,
            "captured_at": "2026-04-12T14:20:00Z"
        },
        {
            "index": 3,
            "capture_id": "a1b2c3d4-...",
            "content": "Real-time features like chat, notifications, and live dashboards benefit most from WebSocket connections.",
            "similarity": 0.723,
            "captured_at": "2026-04-15T10:30:00Z"
        }
    ],
    "has_answer": true,
    "result_count": 3
}
```

### Response — No Results

```json
{
    "answer": "I don't have any information about that topic in your knowledge base.",
    "sources": [],
    "has_answer": false,
    "result_count": 0
}
```

### Response — Error

```json
{
    "detail": "Search is temporarily unavailable. Please try again."
}
```

(Standard FastAPI HTTPException with 503 status code.)

### Router Implementation

```python
# backend/routers/knowledge.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    limit: int = Field(default=5, ge=1, le=20)
    min_similarity: float = Field(default=0.3, ge=0.0, le=1.0)


class SearchSource(BaseModel):
    index: int
    capture_id: str
    content: str
    similarity: float
    captured_at: str


class SearchResponse(BaseModel):
    answer: str
    sources: list[SearchSource]
    has_answer: bool
    result_count: int


@router.post("/search", response_model=SearchResponse)
async def search_knowledge(request: SearchRequest):
    """Search your knowledge base using semantic similarity."""
    knowledge_service = get_knowledge_service()  # dependency injection pattern
    
    result = await knowledge_service.search(
        query=request.query,
        limit=request.limit,
        min_similarity=request.min_similarity,
    )

    return SearchResponse(
        answer=result["answer"],
        sources=[SearchSource(**s) for s in result["sources"]],
        has_answer=result["has_answer"],
        result_count=len(result["sources"]),
    )
```

### Pagination Consideration

For a personal knowledge base, pagination is unnecessary. The typical search returns 3-10 results, the LLM synthesizes them into an answer, and the user reads one response. If you later want to browse all results without synthesis, add a separate endpoint:

```
GET /api/knowledge/browse?query=...&offset=0&limit=20
```

But for MVP, the single search endpoint is sufficient.

---

## 10. Cost Estimate

### Assumptions

| Metric | Monthly Volume |
|--------|---------------|
| Captures | ~100 |
| Extracted points per capture | ~5 (avg) |
| New extracted points | ~500/month |
| Avg tokens per extracted point | ~50 |
| Searches per day | ~20 |
| Searches per month | ~600 |
| Avg query tokens | ~20 |

### Embedding Costs (OpenAI text-embedding-3-small)

| Operation | Tokens/Month | Cost/Month |
|-----------|-------------|------------|
| Embed new extracted points | 500 × 50 = 25,000 | $0.0005 |
| Embed search queries | 600 × 20 = 12,000 | $0.0002 |
| **Total embedding** | 37,000 | **$0.0007** |

### LLM Costs for Search (GPT-4.1-mini)

| Operation | Per Search | Monthly (600 searches) |
|-----------|-----------|----------------------|
| Input tokens (context + query) | ~500 tokens | 300,000 tokens |
| Output tokens (answer) | ~200 tokens | 120,000 tokens |
| Cost (input: $0.40/1M, output: $1.60/1M) | $0.0005 | **$0.31** |

### Existing LLM Costs (Capture Pipeline, Already Incurred)

| Operation | Model | Per Capture | Monthly (100 captures) |
|-----------|-------|-----------|----------------------|
| Extract facts | GPT-4.1-nano | ~$0.0005 | $0.05 |
| Generate questions | GPT-4.1-nano | ~$0.0004 | $0.04 |
| Select technique | GPT-4.1-nano | ~$0.0003 | $0.03 |
| **Capture subtotal** | | | **$0.12** |

### Review LLM Costs (Already Incurred)

| Operation | Model | Per Review | Monthly (est. 300 reviews) |
|-----------|-------|-----------|---------------------------|
| Evaluate answer | GPT-4.1-mini | ~$0.0006 | **$0.18** |

### PostgreSQL Cost

**$0.** Running locally on Windows. No hosting cost.

### Total Monthly Cost

| Category | Cost/Month |
|----------|-----------|
| Embeddings (capture + search) | $0.001 |
| Search LLM (GPT-4.1-mini synthesis) | $0.31 |
| Capture LLM (existing) | $0.12 |
| Review LLM (existing) | $0.18 |
| PostgreSQL + pgvector | $0.00 |
| **Total** | **~$0.61/month** |

### Cost Sensitivity Analysis

| If you... | Cost Impact |
|-----------|-------------|
| Double captures (200/month) | +$0.12 → $0.73/month |
| Triple searches (60/day) | +$0.62 → $1.23/month |
| Switch to text-embedding-3-large | +$0.005 → still negligible |
| Switch search LLM to GPT-4.1 (full) | +$5-10/month → only if synthesis quality is insufficient |
| Reach 10K extracted points | Backfill cost: ~$0.01 one-time |

**Bottom line:** At personal scale, the total cost of adding RAG search is approximately **$0.30/month** incremental (the search LLM synthesis calls). Embedding costs are rounding errors.

---

## Summary: Implementation Checklist

### Phase 2a — Core Vector Search (Ship First)

- [ ] Install pgvector on Windows PostgreSQL 16 (§1)
- [ ] Run schema migration SQL (§2)
- [ ] Add `pgvector` Python package to `requirements.txt`
- [ ] Register vector codec in `db.py` pool init (§2)
- [ ] Implement `embedder.py` with `embed_text()` and `embed_texts()` (§4)
- [ ] Add `search_similar_points()` to `db_queries.py` (§4)
- [ ] Implement `KnowledgeService.search()` with full RAG pipeline (§4)
- [ ] Add `synthesize_answer()` to `llm.py` (§4)
- [ ] Add embedding to capture pipeline (§5)
- [ ] Run backfill script for existing data (§6)
- [ ] Create `/api/knowledge/search` endpoint (§9)
- [ ] Add search UI in frontend

### Phase 2b — Enhancements (After Core Works)

- [ ] Add `hybrid_search()` SQL function (§8)
- [ ] Switch to hybrid search by default
- [ ] Add `hnsw.ef_search` tuning if needed (§7)
- [ ] Add search analytics (query logging, result quality tracking)

### Configuration Additions

```python
# backend/config.py — add these settings

class Settings(BaseSettings):
    # ... existing settings ...
    
    # Embeddings
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536
    
    # Search
    SEARCH_DEFAULT_LIMIT: int = 5
    SEARCH_MIN_SIMILARITY: float = 0.3
    SEARCH_MAX_CONTEXT_TOKENS: int = 3000
```

### Dependencies to Add

```
# requirements.txt — add:
pgvector>=0.3.6
```

No other new dependencies — `openai` and `asyncpg` are already installed. The `pgvector` Python package provides only the asyncpg/psycopg type registration — it does not include the PostgreSQL extension itself (that's installed separately per §1).
