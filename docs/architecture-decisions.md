# ReCall — Architecture & Technical Decisions
**Date:** April 17, 2026
**Status:** Finalized — ready to build

---

## Decisions Locked

| Decision | Choice | Rationale |
|---|---|---|
| **Architecture** | FastAPI (Python) backend + Next.js frontend | Python ecosystem (py-fsrs, Deepgram SDK, OpenAI SDK). You know FastAPI. Two servers but clear separation. |
| **LLM Provider** | OpenAI only (GPT-4.1-nano + GPT-4.1-mini) | One SDK, structured outputs (100% schema adherence), cheapest viable option. |
| **FSRS Rating** | 4-button (Again / Hard / Good / Easy) | Standard FSRS-6 scale, no mapping needed. |
| **MVP Scope** | Full voice conversation included | Text-first core (week 1), voice layer on top (week 2). Never build voice without working text foundation. |
| **Deployment** | Local first (run on your machine) | No cloud config overhead. Both servers run locally during development. |
| **Database** | PostgreSQL + pgvector (Supabase later, local first) | Unified DB for structured data + vectors + full-text search. One DB for everything. |
| **Spaced Repetition** | FSRS-6 via py-fsrs | State-of-the-art algorithm. Python reference implementation. MIT license. |
| **Voice Pipeline** | Deepgram Voice Agent API (Phase 3) | Single API. Sub-300ms latency. BYO LLM. $4.50/hr. Native turn detection + barge-in. |
| **Embeddings** | OpenAI text-embedding-3-small (1536-dim) | $0.02/1M tokens (≈free). 8192 token context handles long transcriptions. |
| **Frontend** | Next.js 15 + Tailwind + shadcn/ui | PWA-capable. WebRTC for voice in browser. Fast to build. |
| **MCP** | Not in MVP. Expose as MCP server in Phase 5. | MCP adds no value internally (single-client system). Value is as a distribution channel — lets Claude/ChatGPT/VS Code query your knowledge base. Design service functions as clean async with typed I/O so MCP wrapping is trivial later. |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  FRONTEND (Next.js 15 + Tailwind + shadcn/ui)               │
│  • Dashboard, capture UI, review session, voice WebRTC       │
│  • PWA for mobile                                            │
│  • Deploy: Vercel (later) / localhost:3000 (dev)             │
└────────────────────────┬────────────────────────────────────┘
                         │ REST + WebSocket
┌────────────────────────▼────────────────────────────────────┐
│  BACKEND (FastAPI)                                           │
│  • /api/captures — capture + extraction pipeline             │
│  • /api/reviews — FSRS scheduling + review session           │
│  • /api/knowledge — semantic search + PA queries             │
│  • /ws/voice — Deepgram voice agent WebSocket (Phase 3)      │
│  • py-fsrs — spaced repetition engine                        │
│  • OpenAI SDK — extraction, questions, evaluation            │
│  • Deploy: Railway (later) / localhost:8000 (dev)            │
└────────────────────────┬────────────────────────────────────┘
                         │ SQL + pgvector
┌────────────────────────▼────────────────────────────────────┐
│  DATABASE (PostgreSQL + pgvector)                            │
│  • users, captures, extracted_points, questions              │
│  • FSRS state on questions table (due, stability, etc.)      │
│  • review_logs (history for optimizer + analytics)           │
│  • embeddings (vector(1536)) + full-text search (tsvector)   │
│  • Deploy: Supabase (later) / local PostgreSQL (dev)         │
└─────────────────────────────────────────────────────────────┘
```

---

## LLM Model Tiering

| Task | Model | Cost/call | Why |
|---|---|---|---|
| Fact extraction | GPT-4.1-nano | $0.0002 | Structured output, cheap, fast (0.59s TTFT) |
| Question generation | GPT-4.1-nano | $0.0003 | Formulaic task, nano handles it |
| Technique selection | GPT-4.1-nano | $0.0001 | Classification task |
| Answer evaluation | GPT-4.1-mini | $0.0006 | Needs nuanced judgment |
| Knowledge queries | GPT-4.1-mini | $0.0005 | Retrieval + synthesis |
| Conversational teaching | GPT-4.1-mini | $0.002 | OpenAI-only constraint |

**Monthly LLM cost (personal use): ~$0.30 – $0.90**

---

## MCP Strategy

**Decision:** MCP is NOT used internally. It IS used as a distribution/integration layer in Phase 5.

| Question | Answer | When |
|---|---|---|
| Use MCP as internal architecture? | **No** — unnecessary abstraction for single-client system | Never |
| Expose ReCall as MCP server? | **Yes** — distribution channel for Claude/ChatGPT/VS Code | Phase 5 |
| Consume other MCP servers? | **Maybe** — Calendar/Email/Slack integration | Phase 5+ |

**Design principle (apply from Day 1):** Write all service functions as clean, self-contained async functions with typed inputs/outputs (Pydantic models). This makes MCP wrapping trivial later:

```python
# Day 1: called directly from FastAPI endpoint
async def search_knowledge(query: str, timeframe: str = "all") -> list[KnowledgeItem]:
    embedding = await get_embedding(query)
    return await db.search_vectors(embedding, timeframe)

# Phase 5: wrapped as MCP tool with zero changes to the function
@mcp.tool()
async def search_knowledge(query: str, timeframe: str = "all") -> list[KnowledgeItem]:
    embedding = await get_embedding(query)
    return await db.search_vectors(embedding, timeframe)
```

**Phase 5 MCP server (mounted on existing FastAPI):**
```python
from mcp.server.fastmcp import FastMCP

mcp_server = FastMCP("ReCall", stateless_http=True, json_response=True)

@mcp_server.tool()
async def search_knowledge(query: str, timeframe: str = "all"): ...

@mcp_server.tool()
async def capture_knowledge(text: str, why_it_matters: str = ""): ...

@mcp_server.tool()
async def get_due_reviews() -> dict: ...

@mcp_server.resource("knowledge://summary/today")
async def today_summary() -> str: ...

# Mount on existing FastAPI app
app.mount("/mcp", mcp_server.streamable_http_app())
```

---

## Orchestration Patterns

### Capture Pipeline
```
Voice/Text → Extract Facts (nano, structured output)
                  ↓
    ┌─────────────┼─────────────┐
    ↓                           ↓
Generate Questions (nano)   Select Technique (nano)
    ↓                           ↓
    └─────────────┬─────────────┘
                  ↓
           Store in DB + Embed
```
**Total latency:** ~2.2s (STT + extract + parallel questions/technique)

### Review Session
```
FSRS picks next due card (no LLM) → Present question → User answers
   → Evaluate answer (mini, structured output) → User rates (1-4)
   → FSRS updates card state → Next card
```

### Knowledge Query
```
User asks → Embed query → pgvector similarity search → Top 5 results
   → Synthesize answer with context (mini) → Return
```

---

## Database Schema

```sql
CREATE EXTENSION IF NOT EXISTS vector;

-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Raw captures (voice or text input)
CREATE TABLE captures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    raw_text TEXT NOT NULL,
    source_type TEXT NOT NULL,           -- 'voice' | 'text' | 'url'
    why_it_matters TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- AI-extracted knowledge points
CREATE TABLE extracted_points (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    capture_id UUID REFERENCES captures(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    content_type TEXT NOT NULL,          -- 'fact' | 'concept' | 'list' | 'comparison' | 'procedure'
    embedding VECTOR(1536),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Auto-generated review questions (one point → many questions)
-- FSRS card state lives directly on this table
CREATE TABLE questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    extracted_point_id UUID REFERENCES extracted_points(id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    answer_text TEXT NOT NULL,
    question_type TEXT NOT NULL,         -- 'recall' | 'cloze' | 'explain' | 'connect' | 'apply'
    technique_used TEXT,                 -- 'chunking' | 'mnemonic' | 'elaboration' etc.
    mnemonic_hint TEXT,

    -- FSRS state (per question = per card)
    due TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    stability FLOAT NOT NULL DEFAULT 0,
    difficulty FLOAT NOT NULL DEFAULT 0,
    elapsed_days INT NOT NULL DEFAULT 0,
    scheduled_days INT NOT NULL DEFAULT 0,
    reps INT NOT NULL DEFAULT 0,
    lapses INT NOT NULL DEFAULT 0,
    state SMALLINT NOT NULL DEFAULT 0,   -- 0=New, 1=Learning, 2=Review, 3=Relearning
    last_review TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Review history (for FSRS optimizer + analytics)
CREATE TABLE review_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id UUID REFERENCES questions(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id),
    rating SMALLINT NOT NULL,            -- 1=Again, 2=Hard, 3=Good, 4=Easy
    state SMALLINT NOT NULL,             -- Card state at review time
    stability FLOAT NOT NULL,
    difficulty FLOAT NOT NULL,
    elapsed_days INT NOT NULL,
    scheduled_days INT NOT NULL,
    user_answer TEXT,
    ai_feedback TEXT,
    reviewed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Daily reflections
CREATE TABLE daily_reflections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_questions_due ON questions (state, due);
CREATE INDEX idx_extracted_points_embedding ON extracted_points
    USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_review_logs_question ON review_logs (question_id, reviewed_at);
```

### "Due Today" Query
```sql
SELECT * FROM questions
WHERE state IN (0, 1, 3)           -- New, Learning, Relearning (always due)
   OR (state = 2 AND due <= NOW()) -- Review cards that are due
ORDER BY
    CASE state
        WHEN 3 THEN 1  -- Relearning first
        WHEN 1 THEN 2  -- Learning second
        WHEN 0 THEN 3  -- New third
        WHEN 2 THEN 4  -- Review last
    END,
    due ASC
LIMIT 20;
```

---

## Monthly Cost (Personal Use)

| Component | Dev (Local) | Production |
|---|---|---|
| PostgreSQL | $0 (local) | $25 (Supabase Pro) |
| Next.js | $0 (localhost) | $0 (Vercel free) |
| FastAPI | $0 (localhost) | $5 (Railway) |
| LLM APIs | ~$0.50 | ~$0.90 |
| Deepgram (15min/day) | $200 free credit | ~$2.25/mo |
| Embeddings | ~$0.01 | ~$0.02 |
| **Total** | **~$0.50** | **~$33/mo** |

---

## Execution Plan

### Phase 1: Text-First Core (Days 1-7)
- [ ] FastAPI project setup + PostgreSQL + pgvector
- [ ] Database schema + migrations
- [ ] Capture endpoint: text in → GPT-4.1-nano extracts facts → generates questions → stores
- [ ] FSRS integration (py-fsrs): card creation, review scheduling
- [ ] Review endpoint: get due cards → present question → rate → update FSRS
- [ ] Next.js frontend: capture form, review session UI, dashboard
- [ ] "Why does this matter?" prompt at capture
- [ ] **End-to-end test: capture → extract → review → rate → next due date works**

### Phase 2: Voice Layer (Days 8-14)
- [ ] Deepgram Voice Agent API integration (WebSocket)
- [ ] Voice capture: mic → Deepgram STT → extraction pipeline
- [ ] Voice review: AI speaks question (TTS) → user answers (STT) → evaluate → TTS feedback
- [ ] Barge-in handling (Deepgram built-in)
- [ ] Browser mic access (WebRTC)
- [ ] Basic PWA setup

### Phase 3: Smart Features (Days 15-21)
- [ ] Semantic search (pgvector): "What did I learn about X?"
- [ ] Connection questions in review sessions
- [ ] Evening reflection prompt
- [ ] Teach-me mode (conversational teaching with recall checks)
- [ ] Interleaved review sessions (shuffle across topics)

### Phase 4: Polish (Day 22+)
- [ ] Push notifications for review reminders
- [ ] Analytics dashboard (retention rate, streaks, weak areas)
- [ ] URL ingestion
- [ ] Mnemonic auto-generation
- [ ] Cloud deployment (Vercel + Railway + Supabase)

### Phase 5: MCP Distribution Layer (Post-launch)
- [ ] Mount FastMCP server on existing FastAPI app at `/mcp`
- [ ] Expose tools: `search_knowledge`, `capture_knowledge`, `get_due_reviews`
- [ ] Expose resources: `knowledge://summary/today`, `knowledge://tags/{tag}`
- [ ] Stateless HTTP transport + OAuth 2.1 auth
- [ ] Publish on Smithery + mcp.so marketplaces
- [ ] Test with Claude Desktop, ChatGPT, VS Code Copilot
- [ ] Optional: consume external MCP servers (Google Calendar, Slack, GitHub) for integrations

---

## Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Voice WebSocket complexity derails week 2 | HIGH | Text core must be 100% working first. Voice is additive, not foundational. |
| AI question quality is poor | MEDIUM | Add edit/delete/flag for questions. Iterate prompts weekly. |
| You stop doing daily reviews | HIGH | Build streak counter. Keep sessions under 5 min. |
| Over-engineering before using | HIGH | Use real data from day 7. No dummy data. |
| Two-server CORS/sync issues | MEDIUM | Set up CORS on day 1. Use consistent API versioning. |
| FSRS params not tuned for voice | LOW | Start with defaults. Optimizer needs 500+ reviews to train custom params. |

---

## Key Prompt Templates

### Extraction Prompt (GPT-4.1-nano)
```
You are a knowledge extraction engine for a spaced repetition memory system.
Extract SPECIFIC, TESTABLE facts from the user's voice capture.

Rules:
- Each fact must be a single, atomic piece of knowledge
- Include specific numbers, names, dates, relationships — not vague summaries
- "The mitochondria produces ATP through oxidative phosphorylation" ✓
- "Mitochondria are important for cells" ✗ (too vague)
- Extract causal relationships: "X causes Y because Z"
- Extract definitions: "X is defined as Y"
- Extract comparisons: "X differs from Y in that Z"
- Ignore filler words, greetings, meta-commentary
- If the capture contains no extractable knowledge, return empty facts array
```

### Question Generation Prompt (GPT-4.1-nano)
```
Generate review questions for spaced repetition from the extracted facts.
Create a mix of question types:

1. RECALL (40%): "What is [concept]?" — tests basic retrieval
2. CLOZE (20%): "[Fact with _____ blank]" — fill-in-the-blank
3. EXPLAIN (20%): "Explain why/how [process works]" — tests understanding
4. CONNECT (10%): "How does [concept A] relate to [concept B]?" — tests integration
5. APPLY (10%): "Given [scenario], what would happen?" — tests transfer

Rules:
- Questions must be answerable from the extracted facts alone
- Include the expected answer for each question
- Each question should test exactly ONE fact or connection
```

### Answer Evaluation Prompt (GPT-4.1-mini)
```
Compare the user's answer against the expected answer.

Scoring (map to FSRS ratings):
- CORRECT: Contains all key elements, demonstrates understanding → suggest "Good" or "Easy"
- PARTIAL: Contains some correct elements but missing key aspects → suggest "Hard"
- WRONG: Incorrect or completely off-topic → suggest "Again"

Rules:
- Accept semantic equivalence (different wording, same meaning = correct)
- Accept additional correct details beyond the expected answer
- Do NOT penalize for informal language or incomplete sentences
- DO penalize for factual errors
- Provide brief feedback: what was correct, what was missing
- Be encouraging but honest
```

### Technique Selection Prompt (GPT-4.1-nano)
```
Select the optimal memory technique for the given facts.

Available techniques:
- CHUNKING: For lists, sequences, grouped information (>3 related items)
- MNEMONIC: For arbitrary associations, foreign words, codes
- ELABORATION: For concepts needing deep understanding, cause-effect chains
- VISUALIZATION: For spatial, anatomical, or process-based knowledge
- ANALOGY: For abstract concepts that map to familiar domains
- NONE: For simple facts that just need spaced repetition

Return the technique name + specific instructions for applying it.
```
