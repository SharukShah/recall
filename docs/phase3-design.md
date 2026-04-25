# Phase 3: Smart Features — System Architecture
**Version:** 1.0  
**Date:** April 18, 2026  
**Status:** Ready to implement  
**Depends on:** Existing MVP (captures, reviews, knowledge search, voice TTS proxy)

---

## Overview

Six features that deepen the learning experience by adding interactive teaching, cross-concept connections, daily reflection habits, mnemonic aids, URL-based capture, and explain-back evaluation.

**Design principles:**
- Reuse existing patterns: service classes, `db_pool` from `app.state`, `core/llm.py` for all LLM calls, `core/db_queries.py` for all SQL
- GPT-4.1-nano for generation tasks, GPT-4.1-mini for evaluation tasks
- No new external dependencies beyond existing stack
- All endpoints under `/api/` prefix

---

## Table of Contents

1. [Teach Me Mode](#1-teach-me-mode)
2. [Connection Questions](#2-connection-questions)
3. [Evening Reflection](#3-evening-reflection)
4. [Mnemonic Generation](#4-mnemonic-generation)
5. [URL Ingestion](#5-url-ingestion)
6. [Explain-Back Mode](#6-explain-back-mode)
7. [Schema Migration SQL](#schema-migration-sql)
8. [New Files to Create](#new-files-to-create)
9. [Integration Points](#integration-points)
10. [Key Architecture Decisions](#key-architecture-decisions)

---

## 1. Teach Me Mode

### What It Does
User says "Teach me about X" → AI teaches using chunking + elaboration + active recall checks. A multi-step interactive lesson delivered chunk by chunk, with comprehension checks between chunks.

### API Endpoints

| Method | Path | Purpose | LLM Model |
|---|---|---|---|
| `POST` | `/api/teach/start` | Start a teaching session on a topic | GPT-4.1-nano |
| `POST` | `/api/teach/respond` | Submit answer to recall check, get next chunk or feedback | GPT-4.1-mini (eval), GPT-4.1-nano (next chunk) |
| `GET`  | `/api/teach/{session_id}` | Resume/get current state of a teaching session | None |

#### Request/Response Models

```python
# --- Start ---
class TeachStartRequest(BaseModel):
    topic: str = Field(..., min_length=2, max_length=500)

class TeachChunk(BaseModel):
    chunk_index: int           # 0-based
    title: str                 # e.g. "What is Binary Search?"
    content: str               # Teaching content (2-4 paragraphs)
    analogy: str | None        # Elaboration analogy if applicable
    recall_question: str       # Active recall check after this chunk

class TeachPlan(BaseModel):
    topic: str
    total_chunks: int          # 3-5 chunks
    chunks: list[TeachChunk]

class TeachStartResponse(BaseModel):
    session_id: str
    topic: str
    total_chunks: int
    current_chunk: int         # 0
    chunk_title: str
    chunk_content: str
    chunk_analogy: str | None
    recall_question: str

# --- Respond ---
class TeachRespondRequest(BaseModel):
    session_id: str
    answer: str = Field(..., min_length=1, max_length=5000)

class TeachRespondResponse(BaseModel):
    feedback: str              # AI eval of answer
    score: Literal["correct", "partial", "wrong"]
    is_complete: bool          # True if this was the last chunk
    # If not complete, next chunk:
    current_chunk: int | None
    chunk_title: str | None
    chunk_content: str | None
    chunk_analogy: str | None
    recall_question: str | None
    # If complete, summary:
    summary: str | None        # Final recap of everything taught
    capture_id: str | None     # Auto-created capture from the session

# --- Resume ---
class TeachSessionResponse(BaseModel):
    session_id: str
    topic: str
    total_chunks: int
    current_chunk: int
    chunk_title: str
    chunk_content: str
    chunk_analogy: str | None
    recall_question: str
    is_complete: bool
```

### Data Flow

```
POST /api/teach/start { topic: "binary search" }
│
├─ 1. LLM: Generate teaching plan (GPT-4.1-nano)
│     Input: topic
│     Output: TeachPlan (3-5 chunks, each with title, content, analogy, recall_question)
│     Structured output via Pydantic
│
├─ 2. Store session in teach_sessions table
│     status = "in_progress", current_chunk = 0
│     plan_json = full TeachPlan serialized
│
├─ 3. Return first chunk + recall question
│
└─ Response: { session_id, topic, chunk_title, chunk_content, recall_question }

POST /api/teach/respond { session_id, answer }
│
├─ 1. Fetch session from DB (validate session_id, check not complete)
│
├─ 2. LLM: Evaluate answer against current chunk's recall_question (GPT-4.1-mini)
│     Input: recall_question, expected_knowledge (chunk content), user_answer
│     Output: { score, feedback }
│
├─ 3. Increment current_chunk in DB
│
├─ 4. IF more chunks remain:
│     └─ Return feedback + next chunk + next recall question
│
├─ 5. IF last chunk completed:
│     ├─ Auto-capture: Run existing CaptureService.process() with the full
│     │   teaching content concatenated as raw_text
│     │   → Creates extracted_points + questions for FSRS scheduling
│     ├─ Mark session complete in DB
│     └─ Return feedback + summary + capture_id
│
└─ Response: { feedback, score, is_complete, next_chunk_or_summary }
```

### Database Changes

```sql
CREATE TABLE teach_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic TEXT NOT NULL,
    plan_json JSONB NOT NULL,           -- Full TeachPlan serialized
    current_chunk INT NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'in_progress',  -- 'in_progress' | 'complete' | 'abandoned'
    capture_id UUID REFERENCES captures(id),     -- Auto-created capture on completion
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### LLM Prompts

1. **teach_plan_generation.txt** — System prompt for GPT-4.1-nano. Instructions: Given a topic, produce a structured teaching plan with 3-5 chunks. Each chunk should build on the previous. Use chunking (break complex topic into digestible pieces), elaboration (analogies to familiar concepts), and end each chunk with an active recall question. The plan should go from foundational → advanced.

2. **teach_answer_evaluation.txt** — System prompt for GPT-4.1-mini. Instructions: Evaluate whether the user's answer to a recall check demonstrates understanding of the chunk content. Score as correct/partial/wrong. Give encouraging, specific feedback. If partial, indicate what was missed.

### Frontend Components

- **New page:** `app/teach/page.tsx` — Topic input form, "Teach me about..." prompt
- **New component:** `components/teach/TeachSession.tsx` — Renders chunks progressively, shows recall questions, accepts answers, shows feedback, progresses to next chunk
- **New component:** `components/teach/ChunkCard.tsx` — Displays a single chunk (title, content, analogy highlight)
- **New component:** `components/teach/RecallCheck.tsx` — Text input for answering recall question + submit button
- **Nav integration:** Add "Teach" link to `DesktopSidebar.tsx` and `MobileTabBar.tsx`

### Decision Logic

- **Chunk count:** LLM decides 3-5 chunks based on topic complexity. Simple topic (e.g., "what is a variable") → 3 chunks. Complex topic (e.g., "how does DNS work") → 5 chunks.
- **Auto-capture:** On session completion, concatenate all chunk contents into a single raw_text and run through existing capture pipeline. This creates FSRS-scheduled review questions automatically.
- **Abandoned sessions:** If user navigates away, session stays `in_progress`. GET endpoint allows resuming. No timeout — sessions persist.
- **Error: LLM fails on plan generation** → Return 500 with "Failed to generate teaching plan. Try a different topic."
- **Error: LLM fails on answer evaluation** → Fallback: score as "partial", feedback = "Could not evaluate. Review the chunk content above."
- **Edge case: Topic too vague** (e.g., "everything") → LLM prompt instructs it to narrow to a specific sub-topic and note this in the first chunk title.

---

## 2. Connection Questions

### What It Does
During reviews, AI identifies concepts from *different* captures that are related and asks relationship questions. "How does X (from capture A) relate to Y (from capture B)?" This implements the **interleaving** and **elaboration** memory techniques.

### API Endpoints

No new endpoints. Connection questions integrate into the existing review flow.

| Existing Endpoint | Change |
|---|---|
| `GET /api/reviews/due` | Include connection questions in the returned list |
| `POST /api/reviews/evaluate` | Handle `question_type = "connection"` evaluation |

### Data Flow

```
GET /api/reviews/due
│
├─ 1. Existing logic: Fetch standard due questions (unchanged)
│
├─ 2. NEW: Generate connection questions (if enough data exists)
│     ├─ Query: Find pairs of extracted_points from DIFFERENT captures
│     │   that have high embedding similarity (cosine > 0.75)
│     │   AND have not been connected before (check connection_questions table)
│     │
│     ├─ IF 0 pairs found → skip, return only standard questions
│     │
│     ├─ Pick top 1-2 pairs (limit connection questions per session)
│     │
│     ├─ LLM: Generate connection question (GPT-4.1-nano)
│     │   Input: point_a.content, point_b.content
│     │   Output: { question_text, answer_text }
│     │   Example: "How does [TCP's 3-way handshake] relate to [WebSocket's
│     │            persistent connection]?"
│     │
│     ├─ Store generated connection question in questions table
│     │   question_type = "connection"
│     │   Link to one of the extracted_points (point_a)
│     │   Store point_b reference in connection_questions table
│     │
│     └─ Insert into the due question list (interleaved, not at the end)
│
├─ 3. Return merged list (standard + connection questions)
│
└─ Response: existing DueResponse format (connection questions have
   question_type="connection", mnemonic_hint contains the second concept)
```

### Database Changes

```sql
CREATE TABLE connection_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id UUID NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    point_a_id UUID NOT NULL REFERENCES extracted_points(id) ON DELETE CASCADE,
    point_b_id UUID NOT NULL REFERENCES extracted_points(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(point_a_id, point_b_id)  -- Don't create duplicate connections
);
```

### LLM Prompts

1. **connection_question_generation.txt** — System prompt for GPT-4.1-nano. Instructions: Given two related concepts from different learning sessions, generate a question that asks the user to explain how they relate. The question should require understanding of both concepts. Also generate an ideal answer that describes the relationship. Keep the question open-ended, not yes/no.

### Frontend Components

No new pages or components needed. Connection questions render in the existing `QuestionCard.tsx` with `question_type = "connection"`. The only UI difference:
- Show a "Connection" badge on the question card
- Display `mnemonic_hint` which will contain a brief note like "Relates to: [other concept]"

### Decision Logic

- **Minimum data threshold:** Only attempt connection questions if there are ≥10 extracted_points from ≥3 different captures. Otherwise, skip — not enough knowledge to connect.
- **Frequency cap:** Max 2 connection questions per review session. They're harder and should be a supplement, not the majority.
- **Similarity threshold:** Cosine similarity > 0.75 but < 0.95. Too similar (>0.95) means they're likely duplicates, not interesting connections.
- **Deduplication:** The UNIQUE constraint on `(point_a_id, point_b_id)` prevents re-asking the same connection. Also check `(point_b_id, point_a_id)` since order doesn't matter.
- **FSRS integration:** Connection questions get standard FSRS scheduling. They enter the review queue like any other question.
- **Error: LLM fails** → Skip connection questions for this session. No error surfaced to user.
- **Error: No embeddings on points** → Skip those points for similarity search. Only compare points that have embeddings.

---

## 3. Evening Reflection

### What It Does
Daily prompt: "What did you learn today?" User submits a free-text reflection. AI extracts facts, generates questions, and schedules reviews — using the existing capture pipeline. Also tracks reflection streaks.

### API Endpoints

| Method | Path | Purpose | LLM Model |
|---|---|---|---|
| `POST` | `/api/reflections` | Submit evening reflection | Same as capture pipeline (GPT-4.1-nano) |
| `GET`  | `/api/reflections` | List past reflections | None |
| `GET`  | `/api/reflections/status` | Check if today's reflection is done | None |

#### Request/Response Models

```python
class ReflectionRequest(BaseModel):
    content: str = Field(..., min_length=5, max_length=10000)

class ReflectionResponse(BaseModel):
    reflection_id: str
    capture_id: str | None    # Links to auto-created capture
    facts_count: int
    questions_count: int
    streak_days: int           # Consecutive days with reflections
    message: str | None

class ReflectionStatusResponse(BaseModel):
    completed_today: bool
    streak_days: int
    last_reflection_at: str | None

class ReflectionListItem(BaseModel):
    id: str
    content: str
    capture_id: str | None
    created_at: str
```

### Data Flow

```
POST /api/reflections { content: "Today I learned about..." }
│
├─ 1. Store reflection in reflections table
│
├─ 2. Run existing CaptureService.process() with:
│     raw_text = content
│     source_type = "reflection"
│     why_it_matters = None
│     → Returns capture_id, facts_count, questions_count
│
├─ 3. Link reflection to capture (update reflection row with capture_id)
│
├─ 4. Calculate reflection streak (consecutive days)
│
└─ Response: { reflection_id, capture_id, facts_count, questions_count, streak_days }

GET /api/reflections/status
│
├─ 1. Check reflections table for today's date
│
├─ 2. Calculate streak
│
└─ Response: { completed_today, streak_days, last_reflection_at }
```

### Database Changes

```sql
CREATE TABLE reflections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    capture_id UUID REFERENCES captures(id),   -- Links to auto-created capture
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add 'reflection' as valid source_type for captures (no schema change needed,
-- source_type is TEXT, just document the new value)
```

### LLM Prompts

No new prompts. Reflections reuse the existing extraction pipeline (`extraction.txt`, `question_generation.txt`, `technique_selection.txt`). The only difference is `source_type = "reflection"`.

### Frontend Components

- **New page:** `app/reflect/page.tsx` — Text area with "What did you learn today?" prompt, submit button, shows result (facts extracted, questions generated)
- **New component:** `components/reflect/ReflectionForm.tsx` — Large text area, submit, loading state
- **New component:** `components/reflect/ReflectionResult.tsx` — Shows facts/questions count after submission, streak badge
- **Dashboard integration:** Add reflection status to dashboard — show "Reflect" CTA if not done today, show streak if done
- **Nav integration:** Add "Reflect" link to sidebar/tab bar

### Decision Logic

- **One per day:** Only one reflection per calendar day. If already submitted today, POST returns 409 with "Already reflected today."
- **Streak calculation:** Count consecutive days with reflections going backwards from today. Same pattern as review streak in `get_dashboard_stats`.
- **Empty extraction:** If the reflection text yields 0 extractable facts (e.g., "nothing really"), still store the reflection but skip capture creation. Return `facts_count: 0, message: "Reflection saved! No specific facts to review."`.
- **source_type:** The auto-created capture uses `source_type = "reflection"` to differentiate from manual captures in the history view.
- **Dashboard CTA timing:** The frontend can show the reflection prompt starting at 6 PM local time (client-side check, no server involvement).

---

## 4. Mnemonic Generation

### What It Does
During capture, AI auto-generates mnemonics (acronyms, analogies, visual hooks) for facts that benefit from them. Mnemonics are stored alongside questions and shown during review as hints.

### API Endpoints

No new endpoints. Mnemonic generation integrates into the existing capture pipeline (`POST /api/captures`).

| Existing Endpoint | Change |
|---|---|
| `POST /api/captures` | Enhanced: generate per-fact mnemonics alongside questions |

### Data Flow

```
POST /api/captures (existing endpoint, enhanced)
│
├─ Steps 1-2: Existing extraction + embedding (unchanged)
│
├─ Step 3: ENHANCED parallel LLM calls
│     ├─ Task A: Generate questions (existing, unchanged)
│     ├─ Task B: Select technique (existing, unchanged)
│     ├─ Task C: Generate embeddings (existing, unchanged)
│     └─ Task D: NEW — Generate mnemonics (GPT-4.1-nano)
│           Input: list of extracted facts
│           Output: MnemonicSet { mnemonics: list[FactMnemonic] }
│           Each FactMnemonic: { fact_index, mnemonic_type, mnemonic_text }
│           mnemonic_type: "acronym" | "analogy" | "visual_hook" | "rhyme" | "none"
│
├─ Step 4: Store questions with per-fact mnemonic_hint
│     ├─ Previously: all questions got the same technique-level mnemonic
│     └─ Now: each question gets a fact-specific mnemonic from Task D
│           IF Task D produced a mnemonic for that fact → use it
│           ELSE → fall back to technique-level mnemonic (existing behavior)
│
└─ Response: unchanged CaptureResponse
```

### Database Changes

No schema changes. The existing `questions.mnemonic_hint` column (TEXT, nullable) already stores mnemonics. The change is in *what* gets stored — fact-specific mnemonics instead of generic technique instructions.

Additionally, store mnemonics on extracted_points for reuse:

```sql
ALTER TABLE extracted_points ADD COLUMN mnemonic_hint TEXT;
```

### LLM Prompts

1. **mnemonic_generation.txt** — System prompt for GPT-4.1-nano. Instructions: Given a list of facts, generate a memorable mnemonic for each fact that would benefit from one. Use the most appropriate type: acronym (for lists), analogy (for concepts), visual hook (for abstract ideas), rhyme (for sequences/rules). Skip facts that are already simple and memorable. For each mnemonic, explain in one sentence why it helps. Return `mnemonic_type: "none"` for facts that don't need mnemonics.

#### Structured Output Model

```python
class FactMnemonic(BaseModel):
    fact_index: int
    mnemonic_type: Literal["acronym", "analogy", "visual_hook", "rhyme", "none"]
    mnemonic_text: str | None  # None when type is "none"

class MnemonicSet(BaseModel):
    mnemonics: list[FactMnemonic]
```

### Frontend Components

No new pages. Enhancement to existing components:
- **`QuestionCard.tsx`** — Already shows `mnemonic_hint`. The hint will now be more specific and useful (e.g., "Acronym: TCP = Transmission Control Protocol, like a Traffic Control Point").
- **`CaptureResult.tsx`** — Optionally show generated mnemonics in the capture result view.

### Decision Logic

- **Selective generation:** The LLM decides which facts benefit from mnemonics. Not every fact gets one — simple facts like "Python is interpreted" don't need a mnemonic.
- **Fallback:** If mnemonic generation fails, the capture pipeline continues without mnemonics. Non-fatal — existing behavior preserved.
- **Priority order:** Per-fact mnemonic > technique-level mnemonic > no mnemonic.
- **Parallel execution:** Mnemonic generation runs in `asyncio.gather` alongside questions, technique, and embeddings. Adds ~400ms latency but runs in parallel so no total time increase.
- **Storage:** Mnemonic stored on `extracted_points.mnemonic_hint` for reuse, and copied to `questions.mnemonic_hint` for display during review.

---

## 5. URL Ingestion

### What It Does
User pastes a URL → backend fetches the article → extracts readable text → runs through the existing capture pipeline (extract facts → generate questions → FSRS schedule).

### API Endpoints

| Method | Path | Purpose | LLM Model |
|---|---|---|---|
| `POST` | `/api/captures/url` | Ingest URL content as a capture | GPT-4.1-nano (extraction) |

#### Request/Response Models

```python
class URLCaptureRequest(BaseModel):
    url: str = Field(..., max_length=2000)
    why_it_matters: str | None = Field(default=None, max_length=1000)

# Response: existing CaptureResponse (same shape)
```

### Data Flow

```
POST /api/captures/url { url: "https://example.com/article", why_it_matters: "..." }
│
├─ 1. Validate URL (scheme must be http/https, no private IPs)
│
├─ 2. Fetch URL content
│     ├─ HTTP GET with timeout (10s), max response size (500KB)
│     ├─ Follow redirects (max 3)
│     ├─ User-Agent: "ReCall/1.0 (knowledge capture)"
│     └─ IF fetch fails → return 422 { error: "Could not fetch URL" }
│
├─ 3. Extract readable text from HTML
│     ├─ Strip HTML tags, scripts, styles, nav, footer
│     ├─ Extract: title, main content (article body / <main> / largest text block)
│     ├─ Use a lightweight HTML-to-text approach (no heavy dependencies)
│     └─ Truncate to 20,000 chars if longer
│
├─ 4. Run existing CaptureService.process() with:
│     raw_text = f"{title}\n\n{extracted_text}"
│     source_type = "url"
│     why_it_matters = request.why_it_matters
│     (source_url stored separately — see schema change)
│
├─ 5. Update capture row with source_url
│
└─ Response: CaptureResponse { capture_id, facts_count, questions_count, ... }
```

### Database Changes

The `captures` table already has a `source_url` column in the product plan's data model but it's missing from the actual schema. Add it:

```sql
ALTER TABLE captures ADD COLUMN source_url TEXT;
```

### LLM Prompts

No new prompts. URL content goes through the existing extraction pipeline. The raw_text sent to extraction includes the article title as context.

### Frontend Components

- **Enhancement to `CaptureForm.tsx`:** Add a URL input tab/toggle. When URL mode is active, show a URL text field instead of the raw_text textarea. The "Why does this matter?" field stays.
- **New component:** `components/capture/URLCaptureTab.tsx` — URL input field + submit button + loading state with "Fetching article..." message

### Decision Logic

- **URL validation:** Must be `http://` or `https://` scheme. Reject `file://`, `ftp://`, `javascript:`, `data:` schemes. Reject private/internal IPs (127.0.0.1, 10.x, 192.168.x, 172.16-31.x) to prevent SSRF.
- **Fetch timeout:** 10 seconds. If the server doesn't respond, return 422.
- **Max content size:** 500KB raw response. Larger articles are truncated.
- **Text extraction:** After HTML stripping, if extracted text is < 50 chars, return 422 "Could not extract readable content from this URL."
- **Truncation:** If extracted text > 20,000 chars, truncate to 20,000 (the LLM extraction prompt handles large inputs well, and this is under the 50,000 char limit for `raw_text`).
- **Rate limiting:** Apply existing `rate_limit(10)` — same as text captures.
- **Error: DNS failure / connection refused** → 422 "Could not reach this URL."
- **Error: Non-HTML response (PDF, image)** → 422 "Only web pages are supported. PDFs and images are not yet supported."
- **Duplicate URL:** No deduplication enforced. User can capture the same URL multiple times (content may have changed).

### Security

- **SSRF prevention:** Validate URL host against private IP ranges before fetching. Use DNS resolution and check the resolved IP, not just the hostname (prevents DNS rebinding).
- **No credential forwarding:** Do not send cookies or auth headers when fetching URLs.
- **Content sanitization:** Strip all HTML before passing to LLM. No script execution.

---

## 6. Explain-Back Mode

### What It Does
A question type where the user must explain a concept in their own words. Uses a dedicated evaluation rubric that checks for comprehension depth, not just factual accuracy. Different from standard `recall` questions which check if you remember specific facts.

### API Endpoints

No new endpoints. Explain-back questions integrate into the existing review flow.

| Existing Endpoint | Change |
|---|---|
| `POST /api/captures` | Generate `explain_back` question type (in addition to existing types) |
| `POST /api/reviews/evaluate` | Use dedicated rubric for `question_type = "explain_back"` |

### Data Flow

```
During capture (enhanced question generation):
│
├─ Existing question types: recall, cloze, explain, connect, apply
├─ New question type: "explain_back"
│
├─ The question_generation prompt is updated to sometimes produce
│   explain_back questions for concept-type and procedure-type facts
│   Example: "Explain how DNS resolution works in your own words"
│
└─ Stored in questions table with question_type = "explain_back"

During review (enhanced evaluation):
│
├─ POST /api/reviews/evaluate { question_id, user_answer }
│
├─ IF question.question_type == "explain_back":
│     ├─ Use explain_back_evaluation.txt prompt (GPT-4.1-mini)
│     ├─ Rubric evaluates:
│     │   1. Accuracy — Are the core facts correct?
│     │   2. Completeness — Are key components mentioned?
│     │   3. Own words — Did they rephrase (not just parrot)?
│     │   4. Depth — Do they show understanding beyond surface level?
│     ├─ Score: correct (3-4 criteria met), partial (1-2 met), wrong (0 met)
│     └─ Feedback references specific rubric dimensions
│
├─ ELSE: Use existing evaluation logic (unchanged)
│
└─ Response: existing EvaluateResponse format
```

### Database Changes

No schema changes. The `questions.question_type` column is TEXT and already accepts arbitrary values. Add `"explain_back"` as a new valid type.

Update the common types:

```python
# In models/common.py — extend QuestionType
QuestionType = Literal["recall", "cloze", "explain", "connect", "apply", "explain_back"]
```

### LLM Prompts

1. **explain_back_evaluation.txt** — System prompt for GPT-4.1-mini. Instructions: You are evaluating a user's explanation of a concept. They were asked to explain it in their own words. Evaluate on 4 dimensions: (1) Accuracy — are core facts correct? (2) Completeness — are key components covered? (3) Own Words — did they use their own phrasing, not just repeat the textbook definition? (4) Depth — do they show causal understanding, not just surface recall? Score as correct (strong on 3+/4), partial (adequate on 1-2/4), wrong (inaccurate or empty). Provide specific feedback referencing each dimension.

2. **Update `question_generation.txt`** — Add instruction: For `concept` and `procedure` content types, generate one `explain_back` question in addition to other types. The question should ask the user to explain the concept in their own words, not just recall facts. Example format: "In your own words, explain how [concept] works and why it matters."

### Frontend Components

No new pages. Enhancement to existing review components:
- **`QuestionCard.tsx`** — When `question_type === "explain_back"`, show a larger text area (encourage longer answers) and a label: "Explain in your own words"
- **`FeedbackCard.tsx`** — When `question_type === "explain_back"`, show rubric-style feedback with the 4 dimensions

### Decision Logic

- **Frequency:** Max 1 explain_back question per 5 generated questions per capture. They're cognitively expensive.
- **Content type filter:** Only generate explain_back for `concept` and `procedure` facts. Not for simple `fact` or `comparison` types.
- **Evaluation model:** Always use GPT-4.1-mini for explain_back evaluation (higher reasoning needed for rubric evaluation).
- **Minimum answer length:** If `user_answer` < 20 chars for an explain_back question, the LLM eval will naturally score it as "wrong" (incomplete explanation). No hard validation needed.
- **FSRS:** Explain-back questions use standard FSRS scheduling, same as all other question types.

---

## Schema Migration SQL

All database changes in a single migration block:

```sql
-- Phase 3 Migration: Smart Features
-- Run after existing schema is in place

-- 1. Teach Me Mode: teaching sessions
CREATE TABLE teach_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic TEXT NOT NULL,
    plan_json JSONB NOT NULL,
    current_chunk INT NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'in_progress',
    capture_id UUID REFERENCES captures(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Connection Questions: track which points have been connected
CREATE TABLE connection_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id UUID NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    point_a_id UUID NOT NULL REFERENCES extracted_points(id) ON DELETE CASCADE,
    point_b_id UUID NOT NULL REFERENCES extracted_points(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(point_a_id, point_b_id)
);

-- 3. Evening Reflection: daily reflections
CREATE TABLE reflections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    capture_id UUID REFERENCES captures(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Mnemonic Generation: per-fact mnemonic storage
ALTER TABLE extracted_points ADD COLUMN mnemonic_hint TEXT;

-- 5. URL Ingestion: source URL on captures
ALTER TABLE captures ADD COLUMN source_url TEXT;

-- 6. Explain-Back Mode: no schema changes (question_type is TEXT)

-- Indexes
CREATE INDEX idx_teach_sessions_status ON teach_sessions (status, created_at DESC);
CREATE INDEX idx_reflections_created ON reflections (created_at DESC);
CREATE INDEX idx_connection_questions_points ON connection_questions (point_a_id, point_b_id);
```

---

## New Files to Create

### Backend

```
backend/
├── routers/
│   ├── teach.py              # POST /start, POST /respond, GET /{session_id}
│   └── reflections.py        # POST /, GET /, GET /status
│
├── services/
│   ├── teach_service.py      # TeachService: start(), respond(), get_session()
│   ├── reflection_service.py # ReflectionService: create(), list(), status()
│   └── url_service.py        # URLService: fetch_and_capture()
│
├── models/
│   └── teach_models.py       # TeachStartRequest/Response, TeachRespondRequest/Response,
│                              # TeachPlan, TeachChunk, TeachSessionResponse
│   └── reflection_models.py  # ReflectionRequest/Response, ReflectionStatusResponse,
│                              # ReflectionListItem
│   └── mnemonic_models.py    # FactMnemonic, MnemonicSet (LLM structured output)
│
├── prompts/
│   ├── teach_plan_generation.txt
│   ├── teach_answer_evaluation.txt
│   ├── connection_question_generation.txt
│   ├── mnemonic_generation.txt
│   └── explain_back_evaluation.txt
│
└── core/
    └── url_fetcher.py        # fetch_url(), extract_text_from_html(), validate_url()
```

### Frontend

```
frontend/
├── app/
│   ├── teach/
│   │   └── page.tsx          # Teach Me Mode page
│   └── reflect/
│       └── page.tsx          # Evening Reflection page
│
├── components/
│   ├── teach/
│   │   ├── TeachSession.tsx   # Multi-step teaching session UI
│   │   ├── ChunkCard.tsx      # Single teaching chunk display
│   │   └── RecallCheck.tsx    # Recall question input + feedback
│   ├── reflect/
│   │   ├── ReflectionForm.tsx # "What did you learn?" text area
│   │   └── ReflectionResult.tsx # Post-submit result display
│   └── capture/
│       └── URLCaptureTab.tsx  # URL input for capture form
│
├── hooks/
│   ├── useTeachSession.ts    # State management for teach flow
│   └── useReflection.ts      # Reflection status + submission
│
├── lib/
│   └── api.ts                # Add: startTeach(), teachRespond(), getTeachSession(),
│                              #      submitReflection(), getReflectionStatus(),
│                              #      captureURL()
│
└── types/
    └── api.ts                # Add: TeachStartResponse, TeachRespondResponse,
                              #      ReflectionResponse, ReflectionStatusResponse,
                              #      URLCaptureRequest
```

---

## Integration Points

### How New Features Connect to Existing Code

| New Feature | Integrates With | How |
|---|---|---|
| **Teach Me Mode** | `CaptureService.process()` | On session completion, calls existing capture pipeline to create FSRS-scheduled review questions from teaching content |
| **Teach Me Mode** | `core/llm.py` | Add `generate_teach_plan()` and `evaluate_teach_answer()` functions following existing patterns |
| **Connection Questions** | `ReviewService.get_due()` | Enhance existing method to optionally append connection questions to the due list |
| **Connection Questions** | `core/db_queries.py` | Add `find_similar_point_pairs()` and `insert_connection_question()` queries |
| **Connection Questions** | `core/embedder.py` | Uses existing embedding infrastructure for similarity search |
| **Evening Reflection** | `CaptureService.process()` | Reflection content runs through existing capture pipeline (source_type="reflection") |
| **Evening Reflection** | Dashboard (`GET /api/stats/dashboard`) | Add `reflection_completed_today` and `reflection_streak` to dashboard stats response |
| **Mnemonic Generation** | `CaptureService.process()` | Add mnemonic generation as a 4th parallel task in the existing `asyncio.gather` call |
| **Mnemonic Generation** | `core/llm.py` | Add `generate_mnemonics()` function |
| **URL Ingestion** | `CaptureService.process()` | URL text goes through existing capture pipeline after HTML extraction |
| **URL Ingestion** | `captures.py` router | Add new endpoint in existing captures router OR create separate router |
| **Explain-Back Mode** | `question_generation.txt` prompt | Update prompt to include explain_back question type |
| **Explain-Back Mode** | `ReviewService.evaluate_answer()` | Branch on question_type to use appropriate evaluation prompt |
| **Explain-Back Mode** | `models/common.py` | Add "explain_back" to QuestionType literal |

### Router Registration in `main.py`

```python
# Add to existing router imports and mounts:
from routers import teach, reflections

app.include_router(teach.router, prefix="/api/teach", tags=["teach"])
app.include_router(reflections.router, prefix="/api/reflections", tags=["reflections"])

# URL ingestion endpoint goes in existing captures router (no new router needed)
# Connection questions and explain-back integrate into existing review router
```

### Dashboard Stats Enhancement

Extend `GET /api/stats/dashboard` response to include:

```python
# Add to DashboardStats response:
class DashboardStats(BaseModel):
    # ... existing fields ...
    reflection_completed_today: bool
    reflection_streak: int
    active_teach_session: str | None  # session_id if there's an in-progress session
```

### Frontend API Client Extensions

```typescript
// Add to lib/api.ts:

export async function startTeachSession(topic: string): Promise<TeachStartResponse> {
  return request<TeachStartResponse>("/api/teach/start", {
    method: "POST",
    body: JSON.stringify({ topic }),
  });
}

export async function respondToTeach(sessionId: string, answer: string): Promise<TeachRespondResponse> {
  return request<TeachRespondResponse>("/api/teach/respond", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, answer }),
  });
}

export async function getTeachSession(sessionId: string): Promise<TeachSessionResponse> {
  return request<TeachSessionResponse>(`/api/teach/${encodeURIComponent(sessionId)}`);
}

export async function submitReflection(content: string): Promise<ReflectionResponse> {
  return request<ReflectionResponse>("/api/reflections/", {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}

export async function getReflectionStatus(): Promise<ReflectionStatusResponse> {
  return request<ReflectionStatusResponse>("/api/reflections/status");
}

export async function captureURL(url: string, whyItMatters?: string): Promise<CaptureResponse> {
  return request<CaptureResponse>("/api/captures/url", {
    method: "POST",
    body: JSON.stringify({ url, why_it_matters: whyItMatters }),
  });
}
```

---

## Key Architecture Decisions

### 1. Teach Me: Stateful Sessions in DB (not LLM conversation history)

**Decision:** Store the full teaching plan as JSON in the DB on session start. Each `/respond` call reads the plan from DB, evaluates the answer, and returns the next pre-planned chunk.

**Why:** Simpler than maintaining LLM conversation history. The plan is deterministic after generation. No risk of the AI "drifting" mid-session. Resumable — user can close the browser and come back.

**Alternative rejected:** Streaming conversation with LLM memory — complex, non-resumable, expensive (every interaction requires full context window).

### 2. Connection Questions: Generated On-Demand During Review Fetch

**Decision:** Connection questions are generated lazily when `GET /api/reviews/due` is called, not pre-generated on capture.

**Why:** On capture, there may not be enough data for meaningful connections. Connections become interesting as the knowledge base grows. Lazy generation ensures we always use the latest knowledge.

**Alternative rejected:** Pre-compute all connections on capture — too early, most connections would be meaningless with few data points.

### 3. Evening Reflection: Reuses Capture Pipeline

**Decision:** Reflections create a capture with `source_type = "reflection"` using the existing `CaptureService.process()`.

**Why:** Maximum code reuse. Reflections are semantically identical to captures — user provides text, AI extracts and generates questions. No reason to build a parallel pipeline.

**Alternative rejected:** Separate reflection processing pipeline — duplicates capture logic without benefit.

### 4. Mnemonic Generation: Parallel LLM Call Added to Capture

**Decision:** Add mnemonic generation as a 4th parallel `asyncio.gather` task alongside questions, technique, and embeddings.

**Why:** Runs concurrently so no additional latency. Simple addition to existing pipeline.

**Alternative rejected:** Post-capture background job — adds complexity (job queue, status polling) for minimal benefit.

### 5. URL Ingestion: Server-Side Fetch with SSRF Protection

**Decision:** Backend fetches the URL, extracts text, then processes through capture pipeline.

**Why:** Frontend can't reliably fetch arbitrary URLs (CORS). Server-side fetching allows content extraction and sanitization.

**Security note:** SSRF prevention is critical — validate against private IPs, use DNS resolution checks, enforce timeout and size limits.

**Alternative rejected:** Client-side fetch + paste content — breaks on CORS, can't handle most URLs.

### 6. Explain-Back: Dedicated Evaluation Rubric, Not a New Endpoint

**Decision:** Explain-back is a question type, not a separate flow. It uses the existing `/reviews/evaluate` endpoint with a branch on `question_type`.

**Why:** Minimizes API surface. The review flow already handles multiple question types. Adding a rubric-based evaluation is just a prompt switch.

**Alternative rejected:** Separate `/api/explain-back/evaluate` endpoint — unnecessary API fragmentation.

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              NEXT.JS FRONTEND                                │
│                                                                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ ┌────────┐  │
│  │ Capture  │ │ Review   │ │Dashboard │ │ Search   │ │ Teach  │ │Reflect │  │
│  │ (+ URL)  │ │(+connect │ │(+reflect │ │          │ │ Me     │ │        │  │
│  │          │ │ +explain)│ │ status)  │ │          │ │        │ │        │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └───┬────┘ └───┬────┘  │
│       │            │            │            │           │           │        │
└───────┼────────────┼────────────┼────────────┼───────────┼───────────┼────────┘
        │ REST       │            │            │           │           │
┌───────▼────────────▼────────────▼────────────▼───────────▼───────────▼────────┐
│                              FASTAPI BACKEND                                  │
│                                                                               │
│  ROUTERS                                                                      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐  │
│  │ captures.py  │ │ reviews.py   │ │ teach.py │ │reflect.py│ │knowledge.py│  │
│  │ +POST /url   │ │ (connection  │ │ /start   │ │ POST /   │ │ (existing) │  │
│  │              │ │  +explain    │ │ /respond │ │ GET /    │ │            │  │
│  │              │ │  integrated) │ │ GET /:id │ │ /status  │ │            │  │
│  └──────┬───────┘ └──────┬───────┘ └────┬─────┘ └────┬─────┘ └──────┬─────┘  │
│         │                │              │            │              │         │
│  SERVICES                                                                     │
│  ┌──────▼───────┐ ┌──────▼───────┐ ┌────▼─────┐ ┌────▼──────┐               │
│  │CaptureService│ │ReviewService │ │TeachSvc  │ │ReflectSvc │               │
│  │ +mnemonics   │ │+connections  │ │start()   │ │create()   │               │
│  │ +url_fetch   │ │+explain_eval │ │respond() │ │status()   │               │
│  └──────┬───────┘ └──────┬───────┘ └────┬─────┘ └────┬──────┘               │
│         │                │              │            │                        │
│  CORE   │                │              │            │                        │
│  ┌──────▼────────────────▼──────────────▼────────────▼─────────────────────┐  │
│  │ llm.py (+teach_plan, +teach_eval, +connection_gen, +mnemonics,         │  │
│  │         +explain_back_eval)                                             │  │
│  │ db_queries.py (+teach sessions, +reflections, +connections,             │  │
│  │               +similar points)                                          │  │
│  │ embedder.py (unchanged)                                                 │  │
│  │ fsrs_engine.py (unchanged)                                              │  │
│  │ url_fetcher.py (NEW — fetch, extract text, validate URL)                │  │
│  └─────────────────────────────────┬───────────────────────────────────────┘  │
│                                    │                                          │
└────────────────────────────────────┼──────────────────────────────────────────┘
                                     │ SQL + pgvector
┌────────────────────────────────────▼──────────────────────────────────────────┐
│                         POSTGRESQL + pgvector                                 │
│                                                                               │
│  EXISTING:  captures, extracted_points, questions, review_logs                │
│  NEW:       teach_sessions, connection_questions, reflections                 │
│  ALTERED:   captures (+source_url), extracted_points (+mnemonic_hint)         │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Summary Per Feature

| Feature | Trigger | Key Steps | Ends With |
|---|---|---|---|
| **Teach Me** | User submits topic | LLM plan → store session → chunk-by-chunk with eval → auto-capture on complete | FSRS questions scheduled |
| **Connection Questions** | User opens review | Find similar point pairs → LLM generates question → inject into due list | Question reviewed via standard flow |
| **Evening Reflection** | User submits reflection | Store → run capture pipeline → calculate streak | FSRS questions scheduled |
| **Mnemonic Generation** | User submits capture | Additional parallel LLM call → per-fact mnemonic stored | Mnemonics shown during review |
| **URL Ingestion** | User pastes URL | Validate → fetch → extract text → run capture pipeline | FSRS questions scheduled |
| **Explain-Back** | During review eval | Branch on question_type → rubric-based LLM evaluation | Score + dimensional feedback |
