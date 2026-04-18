# Vector Database & RAG System Research
## For Personal Knowledge Base / Voice-First Memory Assistant

> **Research Date:** April 2026  
> **Use Case:** Store extracted knowledge from voice/text captures, enable semantic search, find concept connections  
> **Scale:** Personal use — 1K to 50K vectors (not millions)

---

## 1. Overview

| Aspect | Scope |
|--------|-------|
| **Purpose** | Store & retrieve captured knowledge from voice transcriptions and text inputs |
| **Core Queries** | "What did I learn about WebSockets?", "Connect concepts from last week's meetings" |
| **Data Types** | Facts, concepts, meeting notes, ideas, learnings, code snippets |
| **Scale** | 1K–50K items (personal, not enterprise) |
| **Architecture Goal** | Unified DB preferred for solo-dev MVP; minimize infrastructure |

---

## 2. Indexed Structure — Vector Database Comparison

### 2.1 pgvector (via Supabase)

#### Setup & Integration
- **Supabase makes it trivial**: Enable `vector` extension with one click in Dashboard → Extensions → search "vector" → enable
- pgvector is a **Postgres extension** — vectors live alongside your structured data (users, sessions, metadata) in one DB
- Supports Postgres 13+, current version **0.8.2**
- Available via Docker, Homebrew, PGXN, APT, Yum, conda-forge, Postgres.app, and all major hosted providers

#### Table Setup
```sql
CREATE EXTENSION vector;

CREATE TABLE knowledge_items (
  id bigserial PRIMARY KEY,
  content text NOT NULL,
  source_type text,           -- 'voice', 'text', 'meeting', 'note'
  tags text[],
  created_at timestamptz DEFAULT now(),
  fts tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
  embedding vector(1536)      -- match your embedding model dimensions
);
```

#### Indexing Options — HNSW vs IVFFlat

| Feature | HNSW | IVFFlat |
|---------|------|---------|
| **Query Performance** | Better speed-recall tradeoff | Lower speed-recall tradeoff |
| **Build Time** | Slower | Faster |
| **Memory Usage** | Higher | Lower |
| **Can build on empty table?** | Yes | No — needs data first |
| **Default params** | `m=16, ef_construction=64` | `lists = rows/1000` |
| **Best for personal scale?** | **YES — recommended** | Overkill to optimize at this scale |

**Recommendation for personal scale (1K–50K vectors):** Use **HNSW**. At this scale, build time is negligible (seconds), and HNSW provides better query performance. You can even skip indexing entirely for <5K vectors — exact nearest neighbor search on small tables is fast enough.

```sql
-- HNSW index for cosine distance (most common for normalized embeddings)
CREATE INDEX ON knowledge_items USING hnsw (embedding vector_cosine_ops);

-- Tune search quality (default 40, increase for better recall)
SET hnsw.ef_search = 100;
```

IVFFlat guideline: `lists = rows / 1000` for up to 1M rows. For 10K items, that's just 10 lists — barely worth it. **HNSW is the clear winner at personal scale.**

#### Query Patterns

**Semantic similarity search:**
```sql
-- Find 5 most similar items to a query embedding
SELECT id, content, source_type,
       1 - (embedding <=> query_embedding) AS similarity
FROM knowledge_items
ORDER BY embedding <=> query_embedding
LIMIT 5;
```

**Hybrid search (text + vector) with Reciprocal Rank Fusion:**
```sql
CREATE OR REPLACE FUNCTION hybrid_search(
  query_text text,
  query_embedding vector(1536),
  match_count int,
  full_text_weight float = 1,
  semantic_weight float = 1,
  rrf_k int = 50
)
RETURNS SETOF knowledge_items
LANGUAGE sql
AS $$
WITH full_text AS (
  SELECT id,
    row_number() OVER(ORDER BY ts_rank_cd(fts, websearch_to_tsquery(query_text)) DESC) AS rank_ix
  FROM knowledge_items
  WHERE fts @@ websearch_to_tsquery(query_text)
  ORDER BY rank_ix
  LIMIT least(match_count, 30) * 2
),
semantic AS (
  SELECT id,
    row_number() OVER (ORDER BY embedding <#> query_embedding) AS rank_ix
  FROM knowledge_items
  ORDER BY rank_ix
  LIMIT least(match_count, 30) * 2
)
SELECT knowledge_items.*
FROM full_text
FULL OUTER JOIN semantic ON full_text.id = semantic.id
JOIN knowledge_items ON coalesce(full_text.id, semantic.id) = knowledge_items.id
ORDER BY
  coalesce(1.0 / (rrf_k + full_text.rank_ix), 0.0) * full_text_weight +
  coalesce(1.0 / (rrf_k + semantic.rank_ix), 0.0) * semantic_weight
  DESC
LIMIT least(match_count, 30)
$$;
```

**Filtered search (by source type, date range):**
```sql
-- pgvector 0.8.0+ supports iterative scans for filtered queries
SET hnsw.iterative_scan = strict_order;

SELECT * FROM knowledge_items
WHERE source_type = 'meeting'
  AND created_at > now() - interval '7 days'
ORDER BY embedding <=> query_embedding
LIMIT 5;
```

#### Distance Functions
| Operator | Function | Use Case |
|----------|----------|----------|
| `<->` | L2 (Euclidean) distance | General purpose |
| `<=>` | Cosine distance | **Best for normalized embeddings (OpenAI)** |
| `<#>` | Negative inner product | Fastest for normalized vectors |
| `<+>` | L1 (taxicab) distance | Sparse data |

**For OpenAI embeddings** (which are normalized to length 1): use inner product `<#>` for best performance, or cosine `<=>` for simplicity. Rankings will be identical.

#### Performance at Personal Scale (1K–50K)
- **Without index**: Exact search on 50K vectors with 1536 dimensions takes ~10-50ms on Supabase free tier. Perfectly usable.
- **With HNSW index**: Sub-millisecond queries. The index for 50K × 1536-dim vectors fits easily in memory (~300MB).
- **Storage**: Each vector takes `4 × dimensions + 8` bytes. 50K × 1536-dim = ~295MB raw vector data.
- **Supabase free tier has 500MB DB** — enough for ~80K vectors with 1536 dimensions (vectors only), or ~30-40K items with content + metadata + vectors.

#### Full-Stack Capability
**This is pgvector's killer feature for MVP.** One database stores:
- User authentication (Supabase Auth)
- Structured data (knowledge items, tags, categories, sessions)
- Vector embeddings
- Full-text search indexes
- Relationships between concepts (via SQL JOINs and foreign keys)

No separate vector DB to manage, sync, or pay for.

#### Cost on Supabase Free Tier
| Resource | Free Tier |
|----------|-----------|
| Database size | 500 MB |
| API requests | Unlimited |
| Edge Functions | 500K invocations |
| Auth users | 50K MAU |
| Egress | 5 GB |
| Projects | 2 active (paused after 1 week inactivity) |
| Compute | Shared CPU, 500MB RAM |

**Pro Plan ($25/mo)**: 8GB disk, no pausing, email support, daily backups. The Micro compute ($10/mo included in Pro) gives 1GB RAM / 2-core ARM — more than enough for personal RAG.

**Verdict**: Free tier is sufficient for MVP development. Pro Plan ($25/mo) for production.

---

### 2.2 Pinecone

#### Architecture
- **Fully managed serverless** vector database — no infrastructure to manage
- Backed by distributed object storage for scalable, highly available indexes
- Supports dense and sparse vectors (hybrid search with sparse+dense)

#### Free Tier (Starter Plan)
| Resource | Limit |
|----------|-------|
| Storage | Up to 2 GB |
| Write Units | Up to 2M/month |
| Read Units | Up to 1M/month |
| Indexes | Up to 5 |
| Namespaces per Index | 100 |
| Cloud | AWS us-east-1 only |
| Projects | 1 |
| Users | Up to 2 |

Includes free inference: 5M tokens/mo for embedding models (llama-text-embed-v2, multilingual-e5-large), 500 requests/mo for reranking.

#### What You Can Build on Starter Plan
Per Pinecone's own estimates (using 1024 dimensions):
- **Semantic search**: ~30K documents, ~15K searches/day
- **RAG bot**: 10 categories, ~130K category-scoped chats/day
- **Recommendations**: ~50K products, ~44K recommendations/day

#### Paid Plans
- **Usage-based pricing**: $50/month minimum applied to usage
- Billed per storage (GB), write units, read units
- Also available via AWS/GCP/Azure marketplaces

#### Query Patterns & Metadata Filtering
- Semantic search with dense vectors
- Hybrid search with dense + sparse vectors
- Metadata filtering (filter by key-value pairs attached to vectors)
- Reranking via Pinecone Inference (built-in reranking models)

#### When Is Pinecone Overkill?
**For a personal knowledge base: Pinecone is overkill.** Here's why:
1. You don't need serverless auto-scaling — you're one user
2. You don't need distributed object storage — your data fits in a single Postgres table
3. You lose the ability to JOIN vectors with structured data in one query
4. The free tier works, but you're locked to AWS us-east-1
5. Going beyond free means $50/month minimum — 2× the cost of Supabase Pro
6. You'd need a separate database for structured data anyway (authentication, user profiles, metadata relationships)

**Best for**: Teams building production apps expecting millions of vectors with variable load.  
**Not ideal for**: Solo developer personal knowledge base.

---

### 2.3 ChromaDB

#### Architecture
- **Open-source** AI data infrastructure (Apache 2.0)
- Designed for simplicity — built-in embedding, storage, search
- Three client modes:

| Mode | Description | Data Persistence | Use Case |
|------|-------------|-----------------|----------|
| **In-Memory (`Client()`)** | Server runs in-process | Lost on exit | Experiments, notebooks |
| **Persistent (`PersistentClient`)** | SQLite + local files | Saved to disk | Local apps, MVP |
| **Client-Server** | Separate Chroma server | Server-side | Production, multi-client |
| **Cloud (`CloudClient`)** | Managed Chroma Cloud | Managed | Production SaaS |

#### Client-Side vs Server Mode

**Client-side (PersistentClient):**
```python
import chromadb
client = chromadb.PersistentClient(path="./chroma_data")
collection = client.get_or_create_collection(name="knowledge_base")

# Add documents — Chroma handles embedding automatically
collection.upsert(
    documents=["WebSockets enable real-time bidirectional communication"],
    ids=["item_1"],
    metadatas=[{"source": "voice", "topic": "networking"}]
)

# Query — Chroma embeds the query for you
results = collection.query(
    query_texts=["What did I learn about WebSockets?"],
    n_results=5
)
```

**Server mode:**
```bash
# Run Chroma server
chroma run --host localhost --port 8000

# Connect from client
client = chromadb.HttpClient(host="localhost", port=8000)
```

#### Self-Hosted Infrastructure
- **Minimal**: Just `pip install chromadb` and use PersistentClient — zero infra
- **Server mode**: Docker container or `chroma run` — single process
- **Production**: Docker + persistent volume. No complex clustering needed at personal scale
- Chroma Cloud is also available (usage-based, starts free with $5 credits)

#### Embedding Handling
- **Built-in**: Uses `all-MiniLM-L6-v2` by default (384 dimensions) — downloads automatically
- **BYO embeddings**: Pass pre-computed embeddings via `embeddings` parameter
- **Custom embedding functions**: Plug in OpenAI, Cohere, HuggingFace models via `embedding_function` parameter

#### Python API Surface
```python
# Core API — extremely simple
collection = client.create_collection("name")
collection = client.get_or_create_collection("name")
collection.add(ids, documents, embeddings, metadatas)
collection.upsert(ids, documents, embeddings, metadatas)
collection.query(query_texts, query_embeddings, n_results, where, where_document)
collection.get(ids, where, where_document)
collection.update(ids, documents, embeddings, metadatas)
collection.delete(ids, where, where_document)
collection.count()
```

Key features:
- Metadata filtering with `where` clauses
- Document content filtering with `where_document`
- Dense and sparse vector search
- Built-in distance metrics (L2, cosine, inner product)

#### ChromaDB Cloud Pricing
| Metric | Cost |
|--------|------|
| Write | $2.50 per GiB written |
| Storage | $0.33 per GiB/month |
| Query | $0.0075 per TiB queried |
| Network | $0.09 per GiB returned |
| Starter plan | $0/mo + $5 free credits |

Example: 1M docs (1536-dim, 8KB each) stored + 10M queries = ~$79/month. For personal scale (10K docs, 100 queries/day) = **well under $5/month**.

#### Good for MVP?
**Yes — ChromaDB is excellent for MVP / prototyping.** Reasons:
1. Zero infrastructure with PersistentClient
2. Built-in embedding model (no external API needed for prototyping)
3. Simplest API of any vector DB
4. Python-native, great for rapid iteration
5. Can start local, migrate to Cloud later

**Limitations for production:**
- No built-in authentication or authorization
- No SQL — can't JOIN with structured data
- No hybrid search (keyword + semantic) as robust as pgvector's tsvector integration
- Self-hosted server mode is single-process, no HA
- Scaling beyond single machine requires Chroma Cloud

---

### 2.4 Qdrant

#### Architecture
- **Open-source** vector search engine written in Rust (high performance)
- REST API (port 6333) and gRPC API (port 6334)
- Built-in Web UI dashboard
- Rich filtering system with payload indexes

#### Self-Hosted vs Cloud

**Self-hosted:**
```bash
docker pull qdrant/qdrant
docker run -p 6333:6333 -p 6334:6334 \
    -v $(pwd)/qdrant_storage:/qdrant/storage \
    qdrant/qdrant
```

**Qdrant Cloud free tier:**
| Resource | Limit |
|----------|-------|
| Compute | 0.5 vCPU |
| Memory | 1 GB RAM |
| Disk | 4 GB |
| Setup | Single node cluster |
| Inference | Free with selected models |
| Duration | Free forever |

**Standard tier**: Usage-based (billed hourly per vCPU, GB RAM, GB storage). Includes dedicated resources, HA, backups.

#### Python Client
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

client = QdrantClient(url="http://localhost:6333")

# Create collection
client.create_collection(
    collection_name="knowledge",
    vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
)

# Upsert with payload (metadata)
client.upsert(
    collection_name="knowledge",
    points=[
        PointStruct(id=1, vector=[...], payload={"source": "voice", "topic": "websockets"}),
    ],
)

# Search with filter
results = client.query_points(
    collection_name="knowledge",
    query=[0.1, 0.2, ...],
    query_filter=Filter(
        must=[FieldCondition(key="source", match=MatchValue(value="voice"))]
    ),
    with_payload=True,
    limit=5,
).points
```

#### Performance Claims
- Written in Rust — significantly faster than Python-based solutions
- Custom HNSW implementation with quantization (scalar, product, binary)
- Supports on-disk storage with in-memory index for large datasets on limited RAM
- Multitenancy support for serving many users from one cluster
- GPU indexing support

#### When to Use Over pgvector
| Scenario | Use Qdrant | Use pgvector |
|----------|-----------|-------------|
| Need best-in-class vector search performance | ✅ | |
| Already using Postgres for everything else | | ✅ |
| Billion-scale vectors | ✅ | |
| Solo dev, want one database | | ✅ |
| Need rich payload filtering + vector search | ✅ | ✅ (with SQL) |
| Advanced quantization techniques | ✅ | |
| Distributed deployment across nodes | ✅ | Via Citus (complex) |

**For personal knowledge base**: Qdrant is more powerful than needed. The Rust performance advantage is irrelevant at <50K vectors — pgvector handles this effortlessly. Use Qdrant if you expect to scale to millions of vectors or need sub-millisecond latency at scale.

---

### 2.5 Weaviate

#### Overview (for comparison, not primary recommendation)
- Open-source AI-native vector database
- Supports semantic + hybrid search out of the box
- Built-in model provider integrations
- Rich ecosystem: Weaviate Cloud, Weaviate Agents, Weaviate Embeddings
- **Multi-modal**: supports text, images, and more
- Deployment: Docker, Kubernetes, Weaviate Cloud, Embedded Weaviate

#### When to consider
- Multi-modal search (text + images)
- Enterprise features (RAG with permissions, agents)
- Managed cloud with zero-downtime updates

**For personal knowledge base**: Same as Qdrant — more powerful than needed. Adds operational complexity. Skip for MVP.

---

## 3. Embedding Models Comparison

### 3.1 Model Specs

| Model | Provider | Dimensions | Max Tokens | Cost (per 1M tokens) | Quality (MTEB) |
|-------|----------|-----------|------------|-------------------|----|
| **text-embedding-3-small** | OpenAI | 1536 (default) | 8192 | ~$0.02 | 62.3% |
| **text-embedding-3-large** | OpenAI | 3072 (default) | 8192 | ~$0.13 | 64.6% |
| **text-embedding-ada-002** | OpenAI | 1536 | 8192 | ~$0.10 | 61.0% (legacy) |
| **embed-v3** | Cohere | 1024 | 512 | ~$0.10 | ~64% |
| **all-MiniLM-L6-v2** | HuggingFace (OSS) | 384 | 256 | **Free** (self-hosted) | ~56% |
| **nomic-embed-text-v1.5** | Nomic (OSS) | 768 | 8192 | **Free** (self-hosted) | ~62% |

### 3.2 Dimension Reduction

OpenAI's v3 models support **native dimension reduction** via the `dimensions` parameter:
- `text-embedding-3-small`: can be reduced from 1536 to any lower value (e.g., 512, 256)
- `text-embedding-3-large`: can be reduced from 3072 to any lower value (e.g., 1024, 512)
- This uses Matryoshka Representation Learning — the first N dimensions carry the most information
- Supabase's own research confirms: **fewer dimensions perform better** in practice for most use cases

### 3.3 Cost Analysis for Personal Knowledge Base

Assumptions: 50K items, average 200 tokens per item for initial embedding, 100 queries/day

| Model | Initial Embed Cost | Daily Query Cost | Monthly Total |
|-------|-------------------|-----------------|---------------|
| text-embedding-3-small | $0.20 (10M tokens) | ~$0.0004 | ~$0.21 |
| text-embedding-3-large | $1.30 (10M tokens) | ~$0.003 | ~$1.39 |
| Cohere embed-v3 | $1.00 (10M tokens) | ~$0.002 | ~$1.06 |
| all-MiniLM-L6-v2 | **Free** | **Free** | **Free** |
| nomic-embed-text | **Free** | **Free** | **Free** |

**At personal scale, embedding costs are negligible.** Even text-embedding-3-large costs ~$1.39/month for 50K items.

### 3.4 Dimension Size Tradeoffs

| Dimensions | Storage (50K vectors) | Index Size | Query Speed | Quality |
|------------|----------------------|------------|-------------|---------|
| 384 (MiniLM) | ~74 MB | Small | Fastest | Lower |
| 512 (reduced) | ~98 MB | Small | Fast | Good |
| 768 (nomic) | ~147 MB | Medium | Fast | Good |
| 1024 (Cohere) | ~196 MB | Medium | Good | Good |
| 1536 (OpenAI small) | ~295 MB | Large | Good | Better |
| 3072 (OpenAI large) | ~590 MB | XL | Slower | Best |

Storage formula: `4 bytes × dimensions × num_vectors + 8 bytes × num_vectors`

### 3.5 Recommendation for Personal Knowledge Base

**Best overall: `text-embedding-3-small` at 1536 dimensions (or reduced to 512)**

Reasoning:
1. **Cost**: ~$0.02/1M tokens — essentially free at personal scale
2. **Quality**: 62.3% on MTEB, significantly better than free models
3. **Dimension reduction**: Can reduce to 512 dims and save 66% storage with minimal quality loss
4. **Max tokens**: 8192 tokens — handles long voice transcriptions
5. **API simplicity**: One API call, no self-hosting
6. **Normalized outputs**: Works with any distance function (cosine, dot product, L2)

**Runner-up for zero-cost**: `nomic-embed-text-v1.5` — 768 dims, 8192 token context, competitive quality, fully local. Good if you want no external API dependencies.

**Avoid**: `all-MiniLM-L6-v2` — only 256 token context length is too short for voice transcriptions and meeting notes.

---

## 4. RAG Architecture Patterns

### 4.1 Simple RAG (Start Here)

```
User Query → Embed Query → Vector Search → Top-K Results → LLM Prompt → Response
```

**Implementation:**
1. User asks: "What did I learn about WebSockets?"
2. Embed the question with `text-embedding-3-small`
3. Query pgvector for top 5 most similar knowledge items
4. Construct prompt: `CONTEXT: {results} \n QUESTION: {query}`
5. Send to LLM (GPT-4, Claude, etc.)
6. Return answer with source citations

**When simple RAG is enough:** Personal knowledge base with <50K items, single content type, straightforward retrieval queries.

### 4.2 Advanced RAG (When Needed)

```
User Query → Query Rewriting → Hybrid Search (vector + keyword) → Reranking → Context Assembly → LLM → Response
```

**Enhancements over simple RAG:**

| Enhancement | What It Does | When to Add |
|-------------|-------------|-------------|
| **Hybrid search** | Combines keyword (tsvector) + semantic (vector) search via RRF | When exact terms matter (error codes, names, acronyms) |
| **Reranking** | Cross-encoder re-scores top results for better relevance | When top-K results include noise |
| **Query rewriting** | LLM rewrites user query for better retrieval | Vague or conversational queries |
| **Chunk expansion** | Retrieves surrounding context around matched chunks | When chunks are too small for full understanding |
| **Multi-query** | Generates multiple query variants, merges results | Complex questions spanning multiple topics |

**Recommendation**: Start with simple RAG + hybrid search (pgvector makes this easy). Add reranking only if retrieval quality is insufficient.

### 4.3 Chunking Strategies for Captured Knowledge

Different content types need different chunking:

| Content Type | Chunking Strategy | Chunk Size | Overlap |
|-------------|-------------------|------------|---------|
| **Voice transcription** | Sentence-level with timestamp boundaries | 3-5 sentences | 1 sentence |
| **Meeting notes** | Topic/section boundaries | 1 topic block | None |
| **Facts / learnings** | Keep as whole item (usually short) | Full item | N/A |
| **Concepts / explanations** | Paragraph-level | 200-500 tokens | 50 tokens |
| **Code snippets** | Function/block level | Full function | None |

**Key insight for personal knowledge base**: Most captured knowledge items will be short (a voice memo is typically 1-3 paragraphs). You likely **don't need chunking at all** — store each capture as a single item with its full embedding. Chunking becomes necessary only for long documents (>8192 tokens for OpenAI models).

### 4.4 Context Window Management

```python
def build_rag_prompt(query: str, results: list, max_context_tokens: int = 3000):
    """Assemble context from search results, respecting token limits."""
    context_parts = []
    total_tokens = 0
    
    for item in results:
        item_tokens = count_tokens(item['content'])
        if total_tokens + item_tokens > max_context_tokens:
            break
        context_parts.append(f"[{item['source_type']}] {item['content']}")
        total_tokens += item_tokens
    
    return f"""Based on my personal knowledge base, answer this question.

CONTEXT:
{chr(10).join(context_parts)}

QUESTION: {query}

Answer based on the context above. If the context doesn't contain enough 
information, say so. Cite which items you referenced."""
```

Guidelines:
- Reserve 60-70% of context window for retrieved content
- Order results by relevance (most relevant first)
- Include metadata (source type, date) for the LLM to reference
- Set a hard token limit to avoid exceeding the model's context window and control costs

### 4.5 Building a Simple Knowledge Graph with Vectors

You don't need a dedicated graph database. Use pgvector + SQL:

```sql
-- Find conceptually related items (concept connections)
CREATE OR REPLACE FUNCTION find_connections(item_id bigint, threshold float = 0.8)
RETURNS TABLE (related_id bigint, content text, similarity float)
LANGUAGE sql AS $$
  SELECT k2.id, k2.content, 
         1 - (k1.embedding <=> k2.embedding) as similarity
  FROM knowledge_items k1, knowledge_items k2
  WHERE k1.id = item_id AND k2.id != item_id
    AND 1 - (k1.embedding <=> k2.embedding) > threshold
  ORDER BY k1.embedding <=> k2.embedding
  LIMIT 10;
$$;

-- Explicit relationship table for user-defined connections
CREATE TABLE concept_links (
  id bigserial PRIMARY KEY,
  source_id bigint REFERENCES knowledge_items(id),
  target_id bigint REFERENCES knowledge_items(id),
  relationship text,  -- 'builds_on', 'contradicts', 'related_to', 'example_of'
  created_at timestamptz DEFAULT now()
);

-- Combine implicit (vector similarity) + explicit relationships
CREATE OR REPLACE FUNCTION knowledge_graph(item_id bigint)
RETURNS TABLE (related_id bigint, content text, connection_type text, strength float)
LANGUAGE sql AS $$
  -- Implicit connections via vector similarity
  SELECT k2.id, k2.content, 'similar' as connection_type,
         1 - (k1.embedding <=> k2.embedding) as strength
  FROM knowledge_items k1, knowledge_items k2
  WHERE k1.id = item_id AND k2.id != item_id
    AND 1 - (k1.embedding <=> k2.embedding) > 0.75
  UNION ALL
  -- Explicit user-defined connections
  SELECT k.id, k.content, cl.relationship, 1.0
  FROM concept_links cl
  JOIN knowledge_items k ON k.id = cl.target_id
  WHERE cl.source_id = item_id
  ORDER BY strength DESC
  LIMIT 20;
$$;
```

This gives you a lightweight knowledge graph without Neo4j or any graph DB.

---

## 5. Key Decision: Unified DB (pgvector) vs Dedicated Vector DB

### 5.1 When Does pgvector Break?

| Factor | pgvector Limit | When It Matters |
|--------|---------------|-----------------|
| **Vector count** | ~5-10M with HNSW on single node | Never for personal use |
| **Dimensions** | 2,000 for vector (4,000 for halfvec) | Only if using very high-dim models |
| **Query latency** | ~1-5ms at 100K vectors with HNSW | More than fast enough |
| **Concurrent writes** | Postgres MVCC overhead | Only at high-throughput ingestion |
| **Advanced vector ops** | No built-in quantization, multi-vector | Only for billion-scale optimization |

**pgvector will NOT break for personal scale.** The limits that matter (5M+ vectors, sub-millisecond latency requirements, sharding) are enterprise concerns.

### 5.2 Maintenance Overhead

| Aspect | pgvector (Supabase) | Dedicated Vector DB |
|--------|-------------------|-------------------|
| **Infrastructure** | 1 service (Supabase) | 2 services (app DB + vector DB) |
| **Data sync** | N/A — same DB | Must sync metadata between DBs |
| **Backups** | 1 backup strategy | 2 backup strategies |
| **Authentication** | Supabase Auth + RLS | Separate auth for each service |
| **Cost** | $0–$25/mo | $0–$50/mo+ for vector DB alone |
| **Schema migrations** | 1 migration system | Structured data migrations + vector DB collection management |
| **Monitoring** | 1 dashboard | Multiple dashboards |
| **Failure modes** | 1 service can fail | Either service can fail, app degrades differently |

### 5.3 Head-to-Head for Solo Developer MVP

| Criteria | pgvector (Supabase) | Pinecone | ChromaDB | Qdrant |
|----------|-------------------|----------|----------|--------|
| **Setup time** | 5 min (enable extension) | 5 min (create index) | 1 min (pip install) | 5 min (docker pull) |
| **SQL + vectors in one query** | ✅ Yes | ❌ No | ❌ No | ❌ No |
| **Hybrid search** | ✅ tsvector + vector | ✅ sparse + dense | ⚠️ Basic | ⚠️ Payload filtering |
| **Auth built-in** | ✅ Supabase Auth | ❌ | ❌ | ❌ |
| **Free tier for MVP** | ✅ 500MB DB | ✅ 2GB storage | ✅ PersistentClient (free, local) | ✅ 1GB RAM cloud |
| **Production cost** | $25/mo (everything) | $50/mo minimum | $0 (self-host) or usage | $0 (self-host) or usage |
| **Can store structured data** | ✅ Full Postgres | ❌ Metadata only | ❌ Metadata only | ❌ Payload only |
| **Scale ceiling** | ~5M vectors (single node) | Billions | Millions (cloud) | Billions |
| **Operational complexity** | Low (managed) | Lowest (fully managed) | Low (local) | Low-Medium |
| **Best language support** | Any (Postgres client) | Python, JS, Go, Java | Python, JS, Rust | Python, JS, Rust, Go, Java, C# |

---

## 6. Cross-Link Relationships

| Concept | Connected To | Relationship |
|---------|-------------|-------------|
| pgvector HNSW index | Qdrant HNSW | Same algorithm, Qdrant adds custom quantization |
| Supabase hybrid search | Pinecone hybrid search | Both use RRF-like fusion; Supabase uses tsvector, Pinecone uses sparse vectors |
| ChromaDB built-in embedding | OpenAI text-embedding-3-small | ChromaDB uses all-MiniLM by default but can switch to OpenAI |
| pgvector cosine distance `<=>` | OpenAI normalized embeddings | OpenAI outputs are normalized, so cosine = dot product rankings |
| Supabase free tier 500MB | pgvector storage formula | 50K × 1536-dim ≈ 295MB vectors — fits in free tier without metadata |
| Supabase Edge Functions | Embedding generation | Can generate embeddings via built-in gte-small model (384 dims, no external API) |

---

## 7. Gaps & Issues Identified

1. **Supabase AI Quickstarts page returned 404** — the URL structure may have changed. Content was recovered via individual subpages (generate-text-embeddings).

2. **Pinecone "What is RAG" original URL returned 404** — content was found at the updated URL `/learn/retrieval-augmented-generation/`.

3. **OpenAI embedding pricing page redirects** — exact per-token pricing requires checking openai.com/api/pricing/ directly. The page at developers.openai.com/api/docs/guides/embeddings shows pages per dollar (~62,500 pages for text-embedding-3-small, ~9,615 for 3-large) but not exact per-token rates.

4. **Cohere embed-v3 specifics** — not directly researched from Cohere docs. Pricing/specs based on publicly known benchmarks. Context window is notably shorter (512 tokens) than OpenAI (8192 tokens), which is a significant limitation for voice transcriptions.

5. **ChromaDB Cloud is relatively new** — pricing model is clear but production track record is shorter than Pinecone or Supabase.

6. **Weaviate** — included for awareness but its documentation redirected from the original URL. It's a valid option but adds complexity beyond what a personal MVP needs.

---

## 8. Final Summary & Recommendations

### The Clear MVP Winner: pgvector on Supabase

**For a solo developer building a voice-first memory assistant, pgvector on Supabase is the unambiguous best choice.** Here's why:

1. **One database for everything**: Vectors, structured data, auth, real-time subscriptions, edge functions — all in one place
2. **Hybrid search built-in**: tsvector (keyword) + pgvector (semantic) with RRF fusion, implemented as a single SQL function
3. **Free to start, cheap to run**: Free tier → $25/mo Pro when ready for production
4. **No sync headaches**: No need to keep a separate vector DB in sync with your app database
5. **Knowledge graph via SQL**: JOINs and relationship tables give you concept connections without a graph DB
6. **Indexing is trivial**: HNSW index creation is one SQL statement, and at <50K vectors you barely need one

### Embedding Model: text-embedding-3-small (512 or 1536 dims)

- Use 1536 dims if storage isn't a concern (it won't be at personal scale)
- Use 512 dims (via `dimensions` parameter) if you want faster queries and smaller storage
- Cost is negligible: <$1/month for all your embeddings

### Architecture: Start Simple

```
Voice/Text Input
    → Transcribe (Whisper API or local)
    → Extract key knowledge (LLM summarization)
    → Generate embedding (text-embedding-3-small)
    → Store in Supabase (content + embedding + metadata)
    
Query Flow:
    User Question
    → Embed question
    → Hybrid search (hybrid_search function in Supabase)
    → Top-K results as context
    → LLM generates answer with citations
    → Return to user
```

### When to Upgrade

| Signal | Action |
|--------|--------|
| Need sub-millisecond latency | Add a dedicated Qdrant cluster |
| >100K vectors | Still fine with pgvector, add HNSW tuning |
| >1M vectors | Consider Qdrant or Pinecone alongside pgvector |
| Multi-modal search (images + text) | Consider Weaviate |
| Need offline-first | ChromaDB PersistentClient for local storage |

### Critical Takeaways

1. **Don't over-engineer.** At personal scale, any vector DB works. The difference is operational simplicity.
2. **pgvector's superpower is being Postgres.** You get ACID, JOINs, full-text search, auth, backups — for free.
3. **Embedding model choice matters more than vector DB choice** at this scale.
4. **Hybrid search** (keyword + semantic) significantly improves retrieval quality — and pgvector + tsvector makes it trivial.
5. **Skip chunking** for most personal knowledge items. They're short enough to embed whole.
6. **Build the knowledge graph with SQL**, not a dedicated graph database. Vector similarity + explicit relationship tables = lightweight but effective concept connections.
