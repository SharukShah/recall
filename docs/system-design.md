# ReCall — System Design
**Version:** 1.0
**Date:** April 17, 2026
**Status:** Ready to build
**Architecture type:** Monolith (two-process: FastAPI + Next.js, one logical app)

---

## 1. Final System Architecture

### Component Map

```
┌──────────────────────────────────────────────────────────────────────┐
│                         NEXT.JS FRONTEND                             │
│                        (localhost:3000)                               │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────┐  │
│  │  Capture Page │  │ Review Page  │  │  Dashboard   │  │ Search  │  │
│  │  • text input │  │ • Q&A flow   │  │ • due count  │  │ • query │  │
│  │  • why prompt │  │ • rating btns│  │ • streak     │  │ • results│ │
│  │  • mic button │  │ • feedback   │  │ • recent     │  │         │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └─────────┘  │
│                                                                      │
│  Voice (Phase 2): WebRTC mic → WebSocket to backend                  │
└───────────────────────────┬──────────────────────────────────────────┘
                            │ HTTP (REST) + WebSocket (voice)
                            │
┌───────────────────────────▼──────────────────────────────────────────┐
│                         FASTAPI BACKEND                              │
│                        (localhost:8000)                               │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                        API LAYER (routers)                      │ │
│  │  /api/captures    /api/reviews    /api/knowledge    /api/stats  │ │
│  └──────────┬────────────┬───────────────┬──────────────┬─────────┘ │
│             │            │               │              │           │
│  ┌──────────▼────────────▼───────────────▼──────────────▼─────────┐ │
│  │                     SERVICE LAYER                               │ │
│  │                                                                 │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐     │ │
│  │  │ CaptureService│  │ReviewService │  │ KnowledgeService   │     │ │
│  │  │ • process()   │  │ • get_due()  │  │ • search()         │     │ │
│  │  │ • extract()   │  │ • submit()   │  │ • query()          │     │ │
│  │  │ • store()     │  │ • evaluate() │  │                    │     │ │
│  │  └──────┬───────┘  └──────┬───────┘  └────────┬───────────┘     │ │
│  │         │                 │                    │                 │ │
│  │  ┌──────▼─────────────────▼────────────────────▼───────────┐     │ │
│  │  │                  CORE MODULES                           │     │ │
│  │  │  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │     │ │
│  │  │  │ LLM     │  │  FSRS    │  │ Embedder │  │   DB    │ │     │ │
│  │  │  │ Client  │  │  Engine  │  │          │  │  Layer  │ │     │ │
│  │  │  │(OpenAI) │  │(py-fsrs) │  │(OpenAI)  │  │(asyncpg)│ │     │ │
│  │  │  └─────────┘  └──────────┘  └──────────┘  └─────────┘ │     │ │
│  │  └─────────────────────────────────────────────────────────┘     │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  Phase 2: /ws/voice — Deepgram WebSocket proxy                       │
│  Phase 5: /mcp — FastMCP server mounted as sub-app                   │
└───────────────────────────┬──────────────────────────────────────────┘
                            │ SQL + pgvector
┌───────────────────────────▼──────────────────────────────────────────┐
│                    POSTGRESQL + pgvector                              │
│                    (localhost:5432)                                   │
│                                                                      │
│  Tables: users, captures, extracted_points, questions,               │
│          review_logs, daily_reflections                               │
│  Extensions: vector (pgvector), uuid-ossp                            │
│  Indexes: HNSW on embeddings, B-tree on questions(state, due)        │
└──────────────────────────────────────────────────────────────────────┘
```

### What Each Component Does

| Component | Responsibility | Technology | What it does NOT do |
|---|---|---|---|
| **Next.js Frontend** | UI rendering, user interaction, voice mic access | Next.js 15, Tailwind, shadcn/ui | No business logic. No LLM calls. No DB access. |
| **FastAPI Backend** | ALL business logic, LLM orchestration, FSRS, DB access | FastAPI, py-fsrs, OpenAI SDK, asyncpg | No UI rendering. No static file serving (in dev). |
| **PostgreSQL** | Data persistence, vector search, full-text search | PostgreSQL 16 + pgvector 0.8 | No business logic. No caching. |
| **OpenAI API** | Extraction, question gen, evaluation, embeddings | GPT-4.1-nano, GPT-4.1-mini, text-embedding-3-small | External service. Not self-hosted. |
| **Deepgram API** (Phase 2) | STT + TTS + turn detection | Deepgram Voice Agent API | External service. Not in MVP Phase 1. |

---

## 2. Data Flow — Step by Step

### Flow 1: CAPTURE (text input)

```
User types text           Frontend sends POST /api/captures
  in capture form    →      { raw_text, source_type: "text" }
                                        │
                                        ▼
                              Backend: CaptureService.process()
                                        │
                    ┌───────────────────┤
                    ▼                   │
             1. Store raw capture       │
                in captures table       │
                    │                   │
                    ▼                   │
             2. LLM: Extract facts      │
                (GPT-4.1-nano)          │
                structured output →     │
                ExtractedFacts model    │
                    │                   │
                    ▼                   │
             3. Store extracted_points  │
                + generate embedding    │
                (text-embedding-3-small)│
                    │                   │
          ┌────────┤ (parallel)        │
          ▼        ▼                   │
    4a. LLM:    4b. LLM:              │
    Generate    Select                 │
    Questions   Technique              │
    (nano)      (nano)                 │
          │        │                   │
          └───┬────┘                   │
              ▼                        │
        5. Store questions             │
           with FSRS initial state     │
           (due=NOW, state=New)        │
              │                        │
              ▼                        │
        6. Return response             │
           { capture_id,               │
             facts_count,              │
             questions_count }         │
```

**Latency breakdown:**
| Step | Time | Blocking? |
|---|---|---|
| Store raw capture | ~5ms | Yes |
| LLM extract facts | ~600ms | Yes (everything depends on this) |
| Generate embedding | ~200ms | Can run parallel with step 4 |
| LLM generate questions | ~600ms | Parallel with 4b |
| LLM select technique | ~400ms | Parallel with 4a |
| Store questions + FSRS init | ~10ms | Yes |
| **Total** | **~1.4s** | |

### Flow 2: REVIEW SESSION

```
User opens review page       Frontend sends GET /api/reviews/due
                                        │
                                        ▼
                              Backend: ReviewService.get_due()
                                        │
                                        ▼
                              SQL query: questions WHERE
                                state IN (0,1,3) OR
                                (state=2 AND due <= NOW())
                              ORDER BY priority, due ASC
                              LIMIT 20
                                        │
                                        ▼
                              Return question list
                              (question_text, question_type,
                               mnemonic_hint, technique_used)
                                        │
                                        ▼
                    ┌─── FOR EACH QUESTION ──────────────────┐
                    │                                        │
                    │  Frontend shows question               │
                    │    ↓                                    │
                    │  User types/speaks answer               │
                    │    ↓                                    │
                    │  Frontend sends POST /api/reviews/submit│
                    │    { question_id, user_answer }         │
                    │    ↓                                    │
                    │  Backend: ReviewService.evaluate()      │
                    │    ↓                                    │
                    │  LLM evaluates answer (GPT-4.1-mini)   │
                    │    → { score, feedback, suggested_rating }
                    │    ↓                                    │
                    │  Frontend shows:                       │
                    │    • correct answer                    │
                    │    • AI feedback                       │
                    │    • rating buttons (Again/Hard/Good/Easy)
                    │    ↓                                    │
                    │  User clicks rating                    │
                    │    ↓                                    │
                    │  Frontend sends POST /api/reviews/rate  │
                    │    { question_id, rating: 1-4 }         │
                    │    ↓                                    │
                    │  Backend: ReviewService.rate()          │
                    │    1. py-fsrs: scheduler.review_card()  │
                    │    2. Update questions row (FSRS state) │
                    │    3. Insert review_logs row            │
                    │    4. Return { next_due, interval_days }│
                    │    ↓                                    │
                    │  Frontend shows next question           │
                    └────────────────────────────────────────┘
```

**Key detail:** The LLM evaluation (step 5) and the FSRS update (step 7) are separate calls. The LLM *suggests* a rating. The user *chooses* the final rating. FSRS only sees the user's rating.

### Flow 3: KNOWLEDGE QUERY

```
User types: "What did I learn       Frontend sends POST /api/knowledge/search
  about WebSockets?"           →      { query: "WebSockets" }
                                        │
                                        ▼
                              Backend: KnowledgeService.search()
                                        │
                              1. Embed query
                                 (text-embedding-3-small)
                                        │
                              2. pgvector similarity search
                                 SELECT * FROM extracted_points
                                 ORDER BY embedding <=> query_embedding
                                 LIMIT 5
                                        │
                              3. LLM synthesize answer
                                 (GPT-4.1-mini)
                                 Input: query + top 5 results
                                 Output: natural language answer
                                        │
                                        ▼
                              Return { answer, sources[] }
```

### Flow 4: VOICE CAPTURE (Phase 2)

```
User clicks mic button       Frontend opens WebSocket to /ws/voice
                                        │
                                        ▼
                              Backend opens connection to
                              Deepgram Voice Agent API
                                        │
                              Audio streams: Browser → Backend → Deepgram
                              Transcripts:   Deepgram → Backend → Browser
                                        │
                              On speech end (Deepgram turn detection):
                                        │
                              Backend runs CaptureService.process()
                              with transcribed text
                                        │
                              (Same as text capture flow from here)
```

### Flow 5: VOICE REVIEW (Phase 2)

```
User starts voice review     Frontend opens WebSocket to /ws/voice
                                        │
                              Backend: get due questions
                                        │
                              FOR EACH question:
                                │
                                ├─ Backend → Deepgram TTS: speak question
                                │    (audio streams to browser)
                                │
                                ├─ User speaks answer
                                │    (audio streams to Deepgram STT)
                                │
                                ├─ Deepgram returns transcript
                                │
                                ├─ Backend: LLM evaluate answer
                                │    → feedback text
                                │
                                ├─ Backend → Deepgram TTS: speak feedback
                                │
                                ├─ Backend → Deepgram TTS: "How did you do?
                                │    Again, Hard, Good, or Easy?"
                                │
                                ├─ User speaks rating
                                │    (STT → parse to 1-4)
                                │
                                └─ Backend: FSRS update
```

---

## 3. Component Responsibilities

### Backend Module Structure

```
backend/
├── main.py                    # FastAPI app, CORS, lifespan, router mounting
├── config.py                  # Settings (DB URL, API keys, FSRS params)
├── db.py                      # Database connection pool (asyncpg)
│
├── routers/                   # API Layer — HTTP endpoints only
│   ├── captures.py            #   POST /api/captures
│   ├── reviews.py             #   GET /api/reviews/due, POST /submit, POST /rate
│   ├── knowledge.py           #   POST /api/knowledge/search
│   └── stats.py               #   GET /api/stats/dashboard
│
├── services/                  # Service Layer — all business logic
│   ├── capture_service.py     #   process(), extract_facts(), generate_questions()
│   ├── review_service.py      #   get_due(), evaluate_answer(), rate()
│   └── knowledge_service.py   #   search(), query()
│
├── core/                      # Core Modules — shared infrastructure
│   ├── llm.py                 #   OpenAI client wrapper, structured output helpers
│   ├── fsrs_engine.py         #   py-fsrs Scheduler wrapper, card serialization
│   ├── embedder.py            #   text-embedding-3-small wrapper
│   └── db_queries.py          #   Raw SQL queries (no ORM)
│
├── models/                    # Pydantic models — request/response + LLM schemas
│   ├── capture_models.py      #   CaptureRequest, ExtractedFacts, GeneratedQuestions
│   ├── review_models.py       #   ReviewQuestion, AnswerEvaluation, RatingRequest
│   ├── knowledge_models.py    #   SearchRequest, SearchResult, KnowledgeItem
│   └── common.py              #   Shared types (ContentType, QuestionType, etc.)
│
└── prompts/                   # System prompts (loaded as strings)
    ├── extraction.txt
    ├── question_generation.txt
    ├── answer_evaluation.txt
    └── technique_selection.txt
```

### What Logic Lives Where

| Logic | Module | Why here |
|---|---|---|
| HTTP request parsing, validation | `routers/*` | Framework's job. Thin layer. |
| Capture processing pipeline | `services/capture_service.py` | Core business logic. Orchestrates LLM calls, DB writes, embedding. |
| FSRS card state management | `services/review_service.py` + `core/fsrs_engine.py` | Service decides *what* to review. Engine handles *how* FSRS works. |
| LLM calls (all of them) | `core/llm.py` | Single module wrapping OpenAI SDK. All prompts, model selection, structured output in one place. |
| Embedding generation | `core/embedder.py` | Thin wrapper. Called by capture_service and knowledge_service. |
| SQL queries | `core/db_queries.py` | All raw SQL in one file. No ORM — just asyncpg + parameterized queries. |
| Pydantic schemas for LLM output | `models/capture_models.py` | Defines ExtractedFacts, GeneratedQuestions — used by OpenAI Structured Outputs. |
| System prompts | `prompts/*.txt` | Separate files so you can iterate prompts without touching code. |

### What Each Service Handles

#### CaptureService

```python
class CaptureService:
    async def process(self, raw_text: str, source_type: str, why_it_matters: str | None) -> CaptureResult:
        """Full capture pipeline: store → extract → embed → generate questions → store."""

    async def extract_facts(self, text: str) -> ExtractedFacts:
        """LLM call: raw text → structured facts. GPT-4.1-nano with structured output."""

    async def generate_questions(self, facts: list[Fact]) -> list[Question]:
        """LLM call: facts → review questions. GPT-4.1-nano with structured output."""

    async def select_technique(self, facts: list[Fact]) -> str:
        """LLM call: facts → memory technique name. GPT-4.1-nano."""
```

#### ReviewService

```python
class ReviewService:
    async def get_due(self, user_id: str, limit: int = 20) -> list[ReviewQuestion]:
        """Query questions due for review. No LLM — pure SQL + FSRS state check."""

    async def evaluate_answer(self, question_id: str, user_answer: str) -> AnswerEvaluation:
        """LLM call: compare user answer vs expected. GPT-4.1-mini. Returns score + feedback."""

    async def rate(self, question_id: str, rating: int) -> RatingResult:
        """Apply FSRS rating. Updates question row + inserts review_log. No LLM."""

    async def get_session_stats(self, user_id: str) -> SessionStats:
        """Count due items, streak, today's reviews. Pure SQL."""
```

#### KnowledgeService

```python
class KnowledgeService:
    async def search(self, query: str, limit: int = 5) -> list[KnowledgeItem]:
        """Embed query → pgvector similarity search. No LLM synthesis."""

    async def query(self, query: str) -> QueryResult:
        """search() + LLM synthesis. GPT-4.1-mini generates natural language answer."""
```

### Frontend Page Structure

```
frontend/
├── app/
│   ├── page.tsx               # Dashboard (due count, streak, recent captures)
│   ├── capture/
│   │   └── page.tsx           # Capture form (text input + why prompt + submit)
│   ├── review/
│   │   └── page.tsx           # Review session (question → answer → feedback → rate)
│   ├── search/
│   │   └── page.tsx           # Knowledge search (query → results)
│   └── layout.tsx             # Nav bar, global layout
│
├── components/
│   ├── CaptureForm.tsx        # Text area + "why does this matter?" + submit
│   ├── ReviewCard.tsx         # Shows question, answer input, feedback, rating buttons
│   ├── RatingButtons.tsx      # Again / Hard / Good / Easy (4 buttons)
│   ├── DashboardStats.tsx     # Due count, streak counter, retention %
│   ├── SearchBar.tsx          # Query input + search button
│   └── SearchResults.tsx      # List of matching knowledge items
│
└── lib/
    └── api.ts                 # fetch() wrappers for all backend endpoints
```

---

## 4. API Design

### Captures

| Method | Endpoint | Purpose | Request Body | Response |
|---|---|---|---|---|
| `POST` | `/api/captures` | Create a new capture (trigger full pipeline) | `{ raw_text, source_type, why_it_matters? }` | `{ capture_id, facts_count, questions_count, processing_time_ms }` |
| `GET` | `/api/captures` | List recent captures | Query: `?limit=20&offset=0` | `[ { id, raw_text, source_type, facts_count, created_at } ]` |
| `GET` | `/api/captures/{id}` | Get capture with extracted facts + questions | — | `{ capture, facts[], questions[] }` |

### Reviews

| Method | Endpoint | Purpose | Request Body | Response |
|---|---|---|---|---|
| `GET` | `/api/reviews/due` | Get questions due for review | Query: `?limit=20` | `[ { question_id, question_text, question_type, mnemonic_hint, technique_used } ]` |
| `POST` | `/api/reviews/evaluate` | Evaluate user's answer with LLM | `{ question_id, user_answer }` | `{ correct_answer, score, feedback, suggested_rating }` |
| `POST` | `/api/reviews/rate` | Apply FSRS rating (user's final choice) | `{ question_id, rating }` (1-4) | `{ next_due, interval_days, state }` |

### Knowledge

| Method | Endpoint | Purpose | Request Body | Response |
|---|---|---|---|---|
| `POST` | `/api/knowledge/search` | Semantic search over captured knowledge | `{ query, limit? }` | `[ { content, similarity, capture_date, source_type } ]` |
| `POST` | `/api/knowledge/query` | Search + LLM synthesis (PA mode) | `{ query }` | `{ answer, sources[] }` |

### Stats

| Method | Endpoint | Purpose | Response |
|---|---|---|---|
| `GET` | `/api/stats/dashboard` | Dashboard data | `{ due_today, streak_days, total_captures, total_questions, retention_rate, reviews_today }` |

### Request/Response Models

```python
# --- Captures ---
class CaptureRequest(BaseModel):
    raw_text: str
    source_type: Literal["text", "voice", "url"] = "text"
    why_it_matters: str | None = None

class CaptureResponse(BaseModel):
    capture_id: str
    facts_count: int
    questions_count: int
    processing_time_ms: int

# --- Reviews ---
class ReviewQuestion(BaseModel):
    question_id: str
    question_text: str
    question_type: Literal["recall", "cloze", "explain", "connect", "apply"]
    mnemonic_hint: str | None
    technique_used: str | None

class EvaluateRequest(BaseModel):
    question_id: str
    user_answer: str

class EvaluateResponse(BaseModel):
    correct_answer: str
    score: Literal["correct", "partial", "wrong"]
    feedback: str
    suggested_rating: int  # 1-4

class RateRequest(BaseModel):
    question_id: str
    rating: int  # 1=Again, 2=Hard, 3=Good, 4=Easy

class RateResponse(BaseModel):
    next_due: str  # ISO datetime
    interval_days: float
    state: int  # 0=New, 1=Learning, 2=Review, 3=Relearning

# --- Knowledge ---
class SearchRequest(BaseModel):
    query: str
    limit: int = 5

class KnowledgeItem(BaseModel):
    content: str
    similarity: float
    capture_date: str
    source_type: str

class QueryResponse(BaseModel):
    answer: str
    sources: list[KnowledgeItem]

# --- LLM Structured Output Schemas ---
class Fact(BaseModel):
    content: str
    content_type: Literal["fact", "concept", "list", "comparison", "procedure"]

class ExtractedFacts(BaseModel):
    topic: str
    facts: list[Fact]

class GeneratedQuestion(BaseModel):
    question_text: str
    answer_text: str
    question_type: Literal["recall", "cloze", "explain", "connect", "apply"]

class GeneratedQuestions(BaseModel):
    questions: list[GeneratedQuestion]

class TechniqueSelection(BaseModel):
    technique: Literal["chunking", "mnemonic", "elaboration", "visualization", "analogy", "none"]
    instructions: str

class AnswerEvaluation(BaseModel):
    score: Literal["correct", "partial", "wrong"]
    feedback: str
    suggested_rating: int
```

---

## 5. Simplified MVP Architecture

### What's IN the MVP (Phase 1 only)

```
┌────────────────────────────────┐
│  NEXT.JS FRONTEND              │
│  localhost:3000                 │
│                                │
│  4 pages:                      │
│  • / (dashboard)               │
│  • /capture (text capture)     │
│  • /review (review session)    │
│  • /search (knowledge search)  │
│                                │
│  NO voice. NO PWA. NO push     │
│  notifications. Just forms     │
│  and buttons.                  │
└───────────┬────────────────────┘
            │ REST (fetch)
┌───────────▼────────────────────┐
│  FASTAPI BACKEND               │
│  localhost:8000                 │
│                                │
│  6 endpoints:                  │
│  POST /api/captures            │
│  GET  /api/captures            │
│  GET  /api/reviews/due         │
│  POST /api/reviews/evaluate    │
│  POST /api/reviews/rate        │
│  GET  /api/stats/dashboard     │
│                                │
│  3 services:                   │
│  • CaptureService              │
│  • ReviewService               │
│  • (no KnowledgeService yet)   │
│                                │
│  4 core modules:               │
│  • llm.py (OpenAI wrapper)     │
│  • fsrs_engine.py (py-fsrs)    │
│  • embedder.py (embeddings)    │
│  • db_queries.py (SQL)         │
└───────────┬────────────────────┘
            │ SQL
┌───────────▼────────────────────┐
│  POSTGRESQL + pgvector         │
│  localhost:5432                 │
│                                │
│  4 tables (MVP):               │
│  • users (single user for now) │
│  • captures                    │
│  • extracted_points            │
│  • questions (with FSRS state) │
│  • review_logs                 │
│                                │
│  Skip for MVP:                 │
│  • daily_reflections           │
│  • concept_links               │
│  • HNSW index (exact search    │
│    is fast enough at <1K rows) │
└────────────────────────────────┘
```

### What's OUT of MVP

| Feature | Why It's Out | When It Comes In |
|---|---|---|
| Voice capture / review | Adds WebSocket, mic, Deepgram complexity | Phase 2 (day 8-14) |
| Knowledge search / PA mode | Nice to have, not core loop | Phase 3 (day 15-21) |
| Evening reflection prompt | Needs scheduling / notifications | Phase 3 |
| Teach-me mode | Complex agent loop | Phase 3 |
| Connection questions | Needs enough data first | Phase 3 |
| Push notifications | Needs PWA + service worker | Phase 4 |
| Analytics dashboard | Build after 2+ weeks of review data | Phase 4 |
| MCP server | Distribution play, not core | Phase 5 |
| URL ingestion | Content extraction from URLs | Phase 4 |
| Mnemonic generation | Enhancement to capture pipeline | Phase 4 |

### MVP Data Flow (Simplified)

```
CAPTURE:
  User types text → POST /api/captures → Extract (nano) → Questions (nano) → Store → Done

REVIEW:
  User opens /review → GET /api/reviews/due → Show question →
  User types answer → POST /api/reviews/evaluate → Show feedback →
  User clicks rating → POST /api/reviews/rate → FSRS updates → Next question

DASHBOARD:
  User opens / → GET /api/stats/dashboard → Show due count + streak
```

### MVP: Minimum Files to Build

```
backend/
├── main.py                      # FastAPI app + CORS
├── config.py                    # DB URL + OpenAI key
├── db.py                        # asyncpg pool
├── routers/
│   ├── captures.py              # 2 endpoints
│   ├── reviews.py               # 3 endpoints
│   └── stats.py                 # 1 endpoint
├── services/
│   ├── capture_service.py       # process + extract + generate
│   └── review_service.py        # get_due + evaluate + rate
├── core/
│   ├── llm.py                   # OpenAI wrapper
│   ├── fsrs_engine.py           # py-fsrs wrapper
│   ├── embedder.py              # embedding wrapper
│   └── db_queries.py            # all SQL
├── models/
│   ├── capture_models.py        # Pydantic schemas
│   └── review_models.py         # Pydantic schemas
├── prompts/
│   ├── extraction.txt           # system prompt
│   ├── question_generation.txt  # system prompt
│   └── answer_evaluation.txt    # system prompt
└── requirements.txt             # fastapi, uvicorn, asyncpg, openai, fsrs

frontend/
├── app/
│   ├── page.tsx                 # Dashboard
│   ├── capture/page.tsx         # Capture form
│   ├── review/page.tsx          # Review session
│   └── layout.tsx               # Nav bar
├── components/
│   ├── CaptureForm.tsx
│   ├── ReviewCard.tsx
│   ├── RatingButtons.tsx
│   └── DashboardStats.tsx
├── lib/
│   └── api.ts                   # Backend API client
└── package.json

schema.sql                       # Database schema (run once)
```

**Total: ~25 files. That's the entire MVP.**

---

## Summary: What to Build First

```
Day 1:  backend/main.py, config.py, db.py, schema.sql
        → FastAPI runs, DB connected, tables created

Day 2:  core/llm.py, core/embedder.py, prompts/*.txt, models/capture_models.py
        → Can call OpenAI extraction + question gen

Day 3:  services/capture_service.py, routers/captures.py, core/db_queries.py
        → POST /api/captures works end-to-end

Day 4:  core/fsrs_engine.py, models/review_models.py
        → FSRS scheduler wrapper working

Day 5:  services/review_service.py, routers/reviews.py
        → GET /due + POST /evaluate + POST /rate works

Day 6:  routers/stats.py
        → Dashboard stats endpoint works
        → TEST FULL LOOP: capture → extract → review → rate → next due

Day 7:  frontend/ (all 4 pages + components)
        → Usable UI connected to backend
        → START CAPTURING REAL DATA
```
