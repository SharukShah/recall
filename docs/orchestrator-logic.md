# ReCall — Orchestrator Logic Blueprint
**Version:** 1.0  
**Date:** April 17, 2026  
**Purpose:** Complete decision-making and behavioral logic for direct implementation  

---

## 1. High-Level Flow Overview

The system has **4 user-facing operations** and **1 background operation**:

```
USER ACTION               →  SYSTEM OPERATION        →  CORE DEPENDENCY
─────────────────────────────────────────────────────────────────────────
Submit text/voice         →  CAPTURE FLOW             →  LLM + DB + Embedder
Open review page          →  REVIEW FLOW              →  FSRS + LLM + DB
Type a question           →  QUERY FLOW               →  Embedder + LLM + DB
Open dashboard            →  STATS FLOW               →  DB only
(Phase 2) Speak into mic  →  VOICE ORCHESTRATOR       →  Deepgram + all above
```

**Every request enters through a router, hits exactly one service, and returns a typed response. There is no cross-flow within a single HTTP request. The frontend decides which flow to invoke — the backend never auto-detects intent in Phase 1.**

```
HTTP Request
    │
    ├── POST /api/captures         → CaptureService.process()     → CAPTURE FLOW
    ├── GET  /api/reviews/due      → ReviewService.get_due()      → REVIEW FLOW (fetch)
    ├── POST /api/reviews/evaluate → ReviewService.evaluate()     → REVIEW FLOW (eval)
    ├── POST /api/reviews/rate     → ReviewService.rate()         → REVIEW FLOW (rate)
    ├── POST /api/knowledge/search → KnowledgeService.search()    → QUERY FLOW (search)
    ├── POST /api/knowledge/query  → KnowledgeService.query()     → QUERY FLOW (synthesize)
    ├── GET  /api/stats/dashboard  → StatsService.dashboard()     → STATS FLOW
    └── GET  /api/captures         → CaptureService.list()        → LIST FLOW
```

---

## 2. Decision Tree

### 2.1 Router-Level Decision (Phase 1 — REST only)

In Phase 1, **there is no intent detection**. The frontend explicitly calls the correct endpoint. The decision tree at the backend is simply URL routing:

```
REQUEST arrives at FastAPI
│
├─ path starts with /api/captures
│   ├─ method == POST  → CaptureService.process()
│   └─ method == GET   → CaptureService.list()
│
├─ path starts with /api/reviews
│   ├─ /due (GET)      → ReviewService.get_due()
│   ├─ /evaluate (POST)→ ReviewService.evaluate_answer()
│   └─ /rate (POST)    → ReviewService.rate()
│
├─ path starts with /api/knowledge
│   ├─ /search (POST)  → KnowledgeService.search()
│   └─ /query (POST)   → KnowledgeService.query()
│
├─ path starts with /api/stats
│   └─ /dashboard (GET)→ StatsService.get_dashboard()
│
└─ else → 404
```

### 2.2 Voice Orchestrator Decision (Phase 2 — WebSocket)

In Phase 2, voice input requires **intent detection** because the user speaks freely into a mic. The backend must decide what to do with the transcript.

```
VOICE TRANSCRIPT arrives via WebSocket
│
├─ IF session_mode == "review"
│   │
│   ├─ IF awaiting_answer == True
│   │   └─ Treat transcript as ANSWER → ReviewService.evaluate_answer()
│   │
│   ├─ IF awaiting_rating == True
│   │   ├─ Parse transcript for rating keyword
│   │   │   ├─ "again" | "forgot" | "no" | "1"        → rating = 1
│   │   │   ├─ "hard" | "difficult" | "barely" | "2"  → rating = 2
│   │   │   ├─ "good" | "got it" | "yes" | "3"        → rating = 3
│   │   │   ├─ "easy" | "obvious" | "trivial" | "4"   → rating = 4
│   │   │   └─ ELSE → TTS: "Sorry, I didn't catch that. Again, Hard, Good, or Easy?"
│   │   │              → stay in awaiting_rating state
│   │   └─ ReviewService.rate(rating)
│   │
│   └─ IF awaiting_command == True
│       ├─ "skip" | "next"          → skip current question, get_next()
│       ├─ "stop" | "done" | "end"  → end session, return stats
│       ├─ "repeat"                 → TTS: re-speak current question
│       └─ ELSE → TTS: "I didn't understand. You can say your answer, skip, or stop."
│
├─ IF session_mode == "capture"
│   └─ Treat transcript as raw capture text → CaptureService.process()
│
├─ IF session_mode == "query"
│   └─ Treat transcript as query → KnowledgeService.query()
│
└─ IF session_mode == None (fresh connection)
    │
    ├─ Classify intent via keyword matching (NOT LLM — too slow for voice):
    │   ├─ starts with "remember" | "save" | "note" | "capture" | "I learned"
    │   │   → session_mode = "capture"
    │   │   → strip trigger word, process remainder as raw_text
    │   │
    │   ├─ starts with "quiz me" | "review" | "test me" | "start review"
    │   │   → session_mode = "review"
    │   │   → begin review session
    │   │
    │   ├─ starts with "what" | "when" | "how" | "why" | "tell me" | "search"
    │   │   → session_mode = "query"
    │   │   → process as knowledge query
    │   │
    │   └─ ELSE (ambiguous)
    │       → TTS: "Would you like to capture something, start a review, or search your knowledge?"
    │       → session_mode stays None, wait for next transcript
    │
    └─ After mode is set, process the input in that mode
```

### 2.3 Frontend Decision Tree (what the UI does)

```
USER navigates to a page
│
├─ / (Dashboard)
│   ├─ Fetch GET /api/stats/dashboard
│   ├─ IF due_today > 0 → show "Review Now" button (prominent)
│   ├─ IF due_today == 0 → show "All caught up!" message
│   └─ Always show: streak, recent captures, total stats
│
├─ /capture
│   ├─ Show text area + "Why does this matter?" field
│   ├─ On submit:
│   │   ├─ IF raw_text is empty → show client-side error, block submit
│   │   ├─ IF raw_text.length < 10 → show warning "That's very short. Add more detail?"
│   │   │   (still allow submit)
│   │   └─ ELSE → POST /api/captures, show spinner, show result
│   └─ On result:
│       ├─ Show "Captured! X facts extracted, Y questions generated"
│       ├─ IF questions_count == 0 → show "No reviewable facts found. Try being more specific."
│       └─ Clear form for next capture
│
├─ /review
│   ├─ Fetch GET /api/reviews/due
│   ├─ IF questions.length == 0 → show "No reviews due. Capture something first!"
│   ├─ IF questions.length > 0 → enter review loop:
│   │   │
│   │   │  STATE MACHINE (frontend):
│   │   │  ┌─────────────────┐
│   │   │  │  SHOW_QUESTION  │ ← initial state
│   │   │  │  (question_text) │
│   │   │  └────────┬────────┘
│   │   │           │ user types answer + clicks "Check"
│   │   │  ┌────────▼────────┐
│   │   │  │  EVALUATING     │ (spinner, POST /evaluate)
│   │   │  └────────┬────────┘
│   │   │           │ response arrives
│   │   │  ┌────────▼────────┐
│   │   │  │  SHOW_FEEDBACK  │
│   │   │  │  (correct answer │
│   │   │  │   + AI feedback  │
│   │   │  │   + 4 rating btns│)
│   │   │  └────────┬────────┘
│   │   │           │ user clicks rating (1-4)
│   │   │  ┌────────▼────────┐
│   │   │  │  RATING         │ (POST /rate)
│   │   │  └────────┬────────┘
│   │   │           │
│   │   │  ┌────────▼────────┐
│   │   │  │  more questions? │
│   │   │  │  YES → SHOW_QUESTION (next)
│   │   │  │  NO  → SESSION_COMPLETE
│   │   │  └─────────────────┘
│   │   │
│   │   └─ SESSION_COMPLETE: show summary (total, correct %, time, streak)
│   │
│   └─ User can click "End Session" at any time → show partial summary
│
└─ /search
    ├─ Show search bar
    ├─ On submit:
    │   ├─ IF query is empty → block submit
    │   └─ ELSE → POST /api/knowledge/query
    └─ Show: synthesized answer + source cards (fact + capture date)
```

---

## 3. Detailed Flow Definitions

### 3A. CAPTURE FLOW

**Trigger:** `POST /api/captures` with `{ raw_text, source_type, why_it_matters? }`

```
STEP 1: VALIDATE INPUT
│
├─ IF raw_text is None or empty string (after .strip())
│   → return 422 { error: "raw_text is required" }
│
├─ IF raw_text.strip().length > 50_000 characters
│   → return 422 { error: "Input too long. Max 50,000 characters." }
│
├─ IF source_type not in ["text", "voice", "url"]
│   → return 422 { error: "Invalid source_type" }
│
├─ Sanitize: raw_text = raw_text.strip()
├─ Sanitize: why_it_matters = why_it_matters.strip() if provided, else None
│
└─ Input is valid → proceed

STEP 2: STORE RAW CAPTURE
│
├─ INSERT INTO captures (user_id, raw_text, source_type, why_it_matters)
├─ capture_id = returned UUID
│
└─ IF insert fails → return 500 { error: "Failed to save capture" }
    (DB error — let it propagate, FastAPI exception handler catches it)

STEP 3: EXTRACT FACTS (LLM)
│
├─ Build prompt:
│   system = load("prompts/extraction.txt")
│   user_message = raw_text
│   IF why_it_matters is not None:
│       user_message += "\n\nContext (why this matters to me): " + why_it_matters
│
├─ Call OpenAI GPT-4.1-nano with structured output:
│   response_format = ExtractedFacts (Pydantic model)
│   temperature = 0.3 (low creativity — extraction is deterministic)
│   max_tokens = 2000
│
├─ Parse response → ExtractedFacts { topic: str, facts: list[Fact] }
│
├─ IF LLM call fails (API error, timeout, rate limit):
│   ├─ Log error with capture_id
│   ├─ Mark capture as status="extraction_failed" in DB
│   └─ Return 200 { capture_id, facts_count: 0, questions_count: 0,
│                     status: "extraction_failed",
│                     message: "Saved but extraction failed. Will retry." }
│     (Do NOT return 500 — the capture itself was saved successfully)
│
├─ IF facts array is empty (LLM found nothing extractable):
│   ├─ Mark capture as status="no_facts"
│   └─ Return 200 { capture_id, facts_count: 0, questions_count: 0,
│                     status: "no_facts",
│                     message: "No reviewable facts found. Try being more specific." }
│
└─ facts.length >= 1 → proceed with valid facts

STEP 4: STORE FACTS + GENERATE EMBEDDINGS
│
├─ FOR EACH fact in facts:
│   ├─ Generate embedding: embedder.embed(fact.content)
│   │   → float[1536]
│   ├─ INSERT INTO extracted_points (capture_id, content, content_type, embedding)
│   └─ Store returned point_id
│
├─ IF embedding call fails for any fact:
│   ├─ Store fact WITHOUT embedding (embedding = NULL)
│   ├─ Log warning (missing embedding is not fatal — fact is still usable)
│   └─ Continue processing remaining facts
│
└─ point_ids = list of all stored extracted_point IDs

STEP 5: GENERATE QUESTIONS + SELECT TECHNIQUE (PARALLEL)
│
├─ PARALLEL TASK A: Generate Questions (LLM)
│   ├─ system = load("prompts/question_generation.txt")
│   ├─ user_message = JSON of all extracted facts
│   ├─ Call GPT-4.1-nano with structured output → GeneratedQuestions
│   ├─ temperature = 0.5 (some variety in question phrasing)
│   │
│   ├─ IF LLM fails → questions = [] (continue with technique, store facts-only)
│   └─ IF questions is empty → questions = [] (nothing to review, but facts are stored)
│
├─ PARALLEL TASK B: Select Technique (LLM)
│   ├─ system = load("prompts/technique_selection.txt")
│   ├─ user_message = JSON of all extracted facts
│   ├─ Call GPT-4.1-nano with structured output → TechniqueSelection
│   ├─ temperature = 0.2
│   │
│   ├─ IF LLM fails → technique = { technique: "none", instructions: "" }
│   └─ Valid response → use technique name + instructions
│
├─ AWAIT BOTH tasks (asyncio.gather)
│
└─ Merge results: each question gets the technique and mnemonic_hint

STEP 6: STORE QUESTIONS WITH FSRS INITIAL STATE
│
├─ FOR EACH question in generated_questions:
│   │
│   ├─ Map question to its source extracted_point:
│   │   ├─ IF question references a specific fact → use that point_id
│   │   └─ IF ambiguous → use first point_id (best-effort)
│   │
│   ├─ Create FSRS initial card state:
│   │   due = NOW()
│   │   stability = 0
│   │   difficulty = 0
│   │   elapsed_days = 0
│   │   scheduled_days = 0
│   │   reps = 0
│   │   lapses = 0
│   │   state = 0 (New)
│   │   last_review = NULL
│   │
│   ├─ INSERT INTO questions (
│   │     extracted_point_id, question_text, answer_text,
│   │     question_type, technique_used, mnemonic_hint,
│   │     due, stability, difficulty, elapsed_days,
│   │     scheduled_days, reps, lapses, state, last_review
│   │   )
│   │
│   └─ IF insert fails for this question → log error, continue with rest
│
└─ questions_stored = count of successfully inserted questions

STEP 7: RETURN RESPONSE
│
└─ Return 200 {
     capture_id: uuid,
     facts_count: len(facts),
     questions_count: questions_stored,
     status: "complete",
     processing_time_ms: elapsed_ms
   }
```

**Summary of capture flow outcomes:**

| Scenario | HTTP Status | status field | User sees |
|---|---|---|---|
| Normal (facts + questions) | 200 | "complete" | "Captured! X facts, Y questions" |
| No facts extracted | 200 | "no_facts" | "No reviewable facts found" |
| LLM extraction failed | 200 | "extraction_failed" | "Saved but extraction failed" |
| Empty input | 422 | — | Validation error |
| DB failure | 500 | — | Server error |

---

### 3B. PROCESSING LOGIC (Extraction Rules)

**Extraction behavior — what the LLM should produce:**

```
INPUT TEXT                          →  EXPECTED EXTRACTION
───────────────────────────────────────────────────────────
"Python lists are mutable."        →  1 fact: { content: "Python lists are mutable",
                                         content_type: "fact" }

"TCP uses 3-way handshake:         →  1 fact: { content: "TCP 3-way handshake:
 SYN, SYN-ACK, ACK"                     SYN → SYN-ACK → ACK",
                                         content_type: "procedure" }

"React vs Vue: React uses JSX,     →  1 fact: { content: "React uses JSX for
 Vue uses templates"                     templating; Vue uses HTML templates",
                                         content_type: "comparison" }

"I had a meeting today"            →  0 facts (no extractable knowledge)

"haha lol okay"                    →  0 facts

"Steps to deploy: 1. Build         →  1 fact: { content: "Deploy steps:
 2. Push 3. Deploy"                     1. Build 2. Push 3. Deploy",
                                         content_type: "list" }
```

**Question generation logic — type distribution:**

```
FOR EACH fact, generate 1-3 questions based on richness:

fact.content_type == "fact"       → 1 RECALL question (always)
                                  → 1 EXPLAIN question (if causal)

fact.content_type == "concept"    → 1 RECALL question
                                  → 1 EXPLAIN question

fact.content_type == "list"       → 1 CLOZE question (fill in missing item)
                                  → 1 RECALL question (name all items)

fact.content_type == "comparison" → 1 RECALL question (what's the difference?)
                                  → 1 CONNECT question (relate A and B)

fact.content_type == "procedure"  → 1 RECALL question (what are the steps?)
                                  → 1 APPLY question (given scenario, what step?)

LIMIT: max 5 questions per capture (to avoid overwhelming)
  IF more than 5 generated → keep first 5 (ordered by type priority:
     recall > cloze > explain > connect > apply)
```

**Technique selection logic:**

```
IF facts contain 4+ related items (list, sequence)
  → technique = "chunking"
  → instructions = "Group the [N] items into sets of 3-4. Name each group."

IF facts contain arbitrary associations (names↔dates, terms↔codes)
  → technique = "mnemonic"
  → instructions = "Create an acronym or memorable phrase connecting [items]."

IF facts contain cause-effect or deep concepts
  → technique = "elaboration"
  → instructions = "Explain this in your own words. Ask: why? how? what if?"

IF facts contain spatial/anatomical/process-based info
  → technique = "visualization"
  → instructions = "Picture [subject] in your mind. Walk through it step by step."

IF facts contain abstract concepts
  → technique = "analogy"
  → instructions = "This is like [familiar thing] because [shared property]."

ELSE
  → technique = "none"
  → instructions = ""
```

---

### 3C. REVIEW FLOW

**3 separate endpoints, called in sequence by the frontend:**

#### Step 1: GET DUE QUESTIONS

**Trigger:** `GET /api/reviews/due?limit=20`

```
STEP 1: QUERY DATABASE
│
├─ SQL:
│   SELECT q.id, q.question_text, q.answer_text, q.question_type,
│          q.technique_used, q.mnemonic_hint, q.state, q.due
│   FROM questions q
│   WHERE q.state IN (0, 1, 3)           -- New, Learning, Relearning: always due
│      OR (q.state = 2 AND q.due <= NOW())  -- Review: only if due date passed
│   ORDER BY
│       CASE q.state
│           WHEN 3 THEN 1   -- Relearning FIRST (failed cards need reinforcement)
│           WHEN 1 THEN 2   -- Learning SECOND (still in initial learning)
│           WHEN 0 THEN 3   -- New THIRD (introduce new cards after handling old)
│           WHEN 2 THEN 4   -- Review LAST (mature cards can wait)
│       END,
│       q.due ASC           -- Within same priority, oldest due first
│   LIMIT {limit}
│
├─ IF result is empty → return 200 { questions: [], total_due: 0 }
│
└─ Return 200 {
     questions: [ { question_id, question_text, question_type,
                    mnemonic_hint, technique_used } ],
     total_due: (SELECT COUNT(*) from same WHERE clause)
   }
```

**Why `answer_text` is fetched but NOT returned to frontend here:** The answer is needed by the backend for evaluation, but the frontend should not show it before the user answers. The answer is only revealed in the evaluate response.

#### Step 2: EVALUATE ANSWER

**Trigger:** `POST /api/reviews/evaluate` with `{ question_id, user_answer }`

```
STEP 1: VALIDATE
│
├─ IF question_id is not a valid UUID → 422
├─ IF user_answer is None or empty → 422 { error: "Answer is required" }
├─ IF user_answer.strip().length > 10_000 → 422 { error: "Answer too long" }
│
├─ Fetch question from DB:
│   SELECT question_text, answer_text FROM questions WHERE id = question_id
│
├─ IF question not found → 404 { error: "Question not found" }
│
└─ Valid → proceed

STEP 2: LLM EVALUATION
│
├─ system = load("prompts/answer_evaluation.txt")
├─ user_message = format:
│     "Question: {question_text}"
│     "Expected answer: {answer_text}"
│     "User's answer: {user_answer}"
│
├─ Call GPT-4.1-mini with structured output → AnswerEvaluation
│   temperature = 0.2 (evaluation should be consistent)
│
├─ IF LLM fails:
│   ├─ Fallback: exact string comparison
│   │   ├─ IF user_answer.lower() contains 80%+ of answer_text.lower() words
│   │   │   → score = "partial", feedback = "Could not evaluate with AI. Partial match detected."
│   │   └─ ELSE
│   │   │   → score = "partial", feedback = "Could not evaluate with AI. Compare with the correct answer."
│   ├─ suggested_rating = 2 (Hard — user should self-assess)
│   └─ Proceed with fallback evaluation
│
└─ Return 200 {
     correct_answer: answer_text,   -- NOW revealed to user
     score: "correct" | "partial" | "wrong",
     feedback: "Your explanation of X was accurate. You missed Y.",
     suggested_rating: 1-4
   }

EVALUATION SCORING RULES (embedded in prompt, enforced by structured output):

  "correct"  → user_answer captures ALL key elements of answer_text
               (semantic equivalence accepted, exact wording NOT required)
               → suggested_rating = 3 (Good) or 4 (Easy, if answer was immediate/effortless)

  "partial"  → user_answer captures SOME key elements but misses important parts
               → suggested_rating = 2 (Hard)

  "wrong"    → user_answer is factually incorrect OR completely off-topic OR empty
               → suggested_rating = 1 (Again)
```

#### Step 3: RATE (FSRS Update)

**Trigger:** `POST /api/reviews/rate` with `{ question_id, rating }`

```
STEP 1: VALIDATE
│
├─ IF question_id is not a valid UUID → 422
├─ IF rating not in [1, 2, 3, 4] → 422 { error: "Rating must be 1-4" }
│
├─ Fetch current FSRS state from questions table:
│   SELECT due, stability, difficulty, elapsed_days, scheduled_days,
│          reps, lapses, state, last_review
│   FROM questions WHERE id = question_id
│
├─ IF question not found → 404
│
└─ Valid → proceed

STEP 2: APPLY FSRS ALGORITHM
│
├─ Reconstruct py-fsrs Card object from DB row:
│   card = Card()
│   card.due = row.due
│   card.stability = row.stability
│   card.difficulty = row.difficulty
│   card.elapsed_days = row.elapsed_days
│   card.scheduled_days = row.scheduled_days
│   card.reps = row.reps
│   card.lapses = row.lapses
│   card.state = State(row.state)        -- 0=New, 1=Learning, 2=Review, 3=Relearning
│   card.last_review = row.last_review
│
├─ Map rating integer to py-fsrs Rating:
│   1 → Rating.Again
│   2 → Rating.Hard
│   3 → Rating.Good
│   4 → Rating.Easy
│
├─ Call py-fsrs scheduler:
│   scheduler = Scheduler()      -- uses default FSRS-6 parameters
│   now = datetime.now(timezone.utc)
│   result = scheduler.review_card(card, rating, now)
│   → returns (updated_card, review_log)
│
└─ updated_card contains new FSRS state (due, stability, difficulty, etc.)

STEP 3: PERSIST FSRS STATE
│
├─ UPDATE questions
│   SET due = updated_card.due,
│       stability = updated_card.stability,
│       difficulty = updated_card.difficulty,
│       elapsed_days = updated_card.elapsed_days,
│       scheduled_days = updated_card.scheduled_days,
│       reps = updated_card.reps,
│       lapses = updated_card.lapses,
│       state = updated_card.state.value,
│       last_review = now
│   WHERE id = question_id
│
├─ INSERT INTO review_logs (
│       question_id, user_id, rating, state,
│       stability, difficulty, elapsed_days, scheduled_days,
│       reviewed_at
│   ) VALUES (
│       question_id, user_id, rating, old_state,
│       old_stability, old_difficulty, old_elapsed_days,
│       old_scheduled_days, now
│   )
│   -- review_logs records the BEFORE state + the rating applied
│
└─ IF update/insert fails → 500 (this is critical — FSRS state must persist)

STEP 4: RETURN RESULT
│
└─ Return 200 {
     next_due: updated_card.due (ISO datetime string),
     interval_days: updated_card.scheduled_days,
     state: updated_card.state.value,
     state_label: state name ("New" | "Learning" | "Review" | "Relearning")
   }
```

**FSRS state transitions (for reference):**

```
                     ┌────────────────────────────────────┐
                     │                                    │
  ┌──────┐   Good/Easy   ┌──────────┐   Good/Easy   ┌────▼───┐
  │  New ├────────────────► Learning ├───────────────► Review │
  │ (0)  │               │   (1)    │               │  (2)   │
  └──┬───┘               └────┬─────┘               └────┬───┘
     │                        │                          │
     │  Again                 │ Again                    │ Again
     │                        │                          │
     │                        ▼                          ▼
     │                   Stay in Learning          ┌──────────┐
     │                   (reset step)              │Relearning│
     └──────────────────────────────────────────────►   (3)    │
                                                   └────┬─────┘
                                                        │ Good/Easy
                                                        │
                                                        ▼
                                                   Back to Review (2)
```

**Rating effects on scheduling:**

```
Rating.Again (1):
  - IF state == New or Learning → reset learning steps, re-show soon
  - IF state == Review → lapses += 1, state → Relearning, stability drops
  - interval: minutes

Rating.Hard (2):
  - Interval grows slower than Good
  - Difficulty increases slightly
  - interval: 1.2x previous

Rating.Good (3):
  - Standard progression
  - interval: grows by stability factor (typically 2-3x)

Rating.Easy (4):
  - Accelerated progression
  - Difficulty decreases
  - interval: grows by large factor (3-5x)
```

---

### 3D. QUERY FLOW

**Trigger:** `POST /api/knowledge/query` with `{ query }`

```
STEP 1: VALIDATE
│
├─ IF query is None or empty → 422 { error: "Query is required" }
├─ IF query.length > 2000 → 422 { error: "Query too long" }
│
└─ Valid → proceed

STEP 2: EMBED QUERY
│
├─ embedding = embedder.embed(query)
│
├─ IF embedding fails:
│   ├─ Fallback to full-text search (no vector):
│   │   SELECT content FROM extracted_points
│   │   WHERE to_tsvector('english', content) @@ plainto_tsquery('english', query)
│   │   ORDER BY ts_rank(...) DESC LIMIT 5
│   └─ Continue to step 4 with text-search results
│
└─ embedding generated → proceed

STEP 3: VECTOR SIMILARITY SEARCH
│
├─ SQL:
│   SELECT ep.content, ep.content_type,
│          c.created_at as capture_date, c.source_type,
│          1 - (ep.embedding <=> {query_embedding}) AS similarity
│   FROM extracted_points ep
│   JOIN captures c ON ep.capture_id = c.id
│   WHERE ep.embedding IS NOT NULL
│   ORDER BY ep.embedding <=> {query_embedding}
│   LIMIT 5
│
├─ IF no results found:
│   └─ Return 200 {
│        answer: "I don't have any knowledge matching that query yet. Capture something first!",
│        sources: []
│      }
│
├─ IF all results have similarity < 0.3:
│   ├─ Results are too distant — likely irrelevant
│   └─ Return 200 {
│        answer: "I found some results but they don't seem closely related to your question.",
│        sources: filtered_results   -- still show them, let user judge
│      }
│
└─ results with similarity >= 0.3 → proceed

STEP 4: SYNTHESIZE ANSWER (LLM)
│
├─ system = "You are a personal knowledge assistant. Answer the user's question
│            using ONLY the provided context from their captured knowledge.
│            If the context doesn't contain enough info, say so honestly.
│            Do not make up information."
│
├─ user_message = format:
│     "Question: {query}"
│     "Your captured knowledge:"
│     FOR EACH result:
│       "- [{result.capture_date}] {result.content}"
│
├─ Call GPT-4.1-mini (NOT structured output — free text answer)
│   temperature = 0.3
│   max_tokens = 1000
│
├─ IF LLM fails:
│   ├─ Return results WITHOUT synthesis:
│   └─ Return 200 {
│        answer: "Here's what I found (AI summary unavailable):",
│        sources: results
│      }
│
└─ Return 200 {
     answer: llm_response,
     sources: results (with content, similarity, capture_date, source_type)
   }
```

---

### 3E. STATS FLOW

**Trigger:** `GET /api/stats/dashboard`

```
STEP 1: QUERY ALL STATS (single DB round trip, multiple CTEs)
│
├─ SQL:
│   WITH
│     due_count AS (
│       SELECT COUNT(*) as n FROM questions
│       WHERE state IN (0,1,3) OR (state = 2 AND due <= NOW())
│     ),
│     review_today AS (
│       SELECT COUNT(*) as n FROM review_logs
│       WHERE reviewed_at >= CURRENT_DATE
│     ),
│     retention AS (
│       SELECT
│         COUNT(*) FILTER (WHERE rating >= 3) as correct,
│         COUNT(*) as total
│       FROM review_logs
│       WHERE reviewed_at >= NOW() - INTERVAL '30 days'
│     ),
│     streak AS (
│       SELECT COUNT(DISTINCT DATE(reviewed_at)) as days
│       FROM review_logs
│       WHERE reviewed_at >= (
│         -- find the first gap (day with no reviews) going backwards
│         SELECT COALESCE(
│           (SELECT DATE(d) + 1
│            FROM generate_series(CURRENT_DATE - INTERVAL '365 days', CURRENT_DATE, '1 day') d
│            WHERE DATE(d) NOT IN (SELECT DISTINCT DATE(reviewed_at) FROM review_logs)
│              AND DATE(d) < CURRENT_DATE
│            ORDER BY d DESC LIMIT 1),
│           CURRENT_DATE - INTERVAL '365 days'
│         )
│       )
│     ),
│     totals AS (
│       SELECT
│         (SELECT COUNT(*) FROM captures) as total_captures,
│         (SELECT COUNT(*) FROM questions) as total_questions
│     )
│   SELECT
│     due_count.n as due_today,
│     review_today.n as reviews_today,
│     CASE WHEN retention.total > 0
│       THEN ROUND(100.0 * retention.correct / retention.total)
│       ELSE 0
│     END as retention_rate,
│     streak.days as streak_days,
│     totals.total_captures,
│     totals.total_questions
│   FROM due_count, review_today, retention, streak, totals
│
└─ Return 200 {
     due_today: int,
     reviews_today: int,
     retention_rate: int (0-100),
     streak_days in,
     total_captures: int,
     total_questions: int
   }
```

---

### 3F. MODE SWITCHING (Phase 1 vs Phase 2)

**Phase 1 (REST only):** No mode switching. Each endpoint is its own mode. The frontend navigates between pages — the backend is stateless.

```
Phase 1 mode switching = frontend navigation:
  /capture → capture mode
  /review  → review mode
  /search  → query mode
  /        → dashboard mode

The backend has NO concept of "current mode."
Each request is independent. No session tracking needed.
```

**Phase 2 (Voice WebSocket):** Mode switching happens within a single WebSocket session.

```
Voice session state machine:

  ┌───────────┐
  │   IDLE     │ ← WebSocket connected, no mode set
  └─────┬─────┘
        │ user speaks (intent detected)
        ├──────────────────────────────────────────────────┐
        ▼                          ▼                       ▼
  ┌───────────┐          ┌──────────────┐         ┌───────────┐
  │  CAPTURE  │          │    REVIEW    │         │   QUERY   │
  │  MODE     │          │    MODE      │         │   MODE    │
  │           │          │              │         │           │
  │ awaiting  │          │ sub-states:  │         │ awaiting  │
  │ speech    │          │ • presenting │         │ speech    │
  └─────┬─────┘          │ • answer_wait│         └─────┬─────┘
        │                │ • evaluating │               │
        │                │ • rating_wait│               │
        │                └──────┬───────┘               │
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                │ "stop" / "switch to X" / disconnect
                                ▼
                          ┌───────────┐
                          │   IDLE     │
                          └───────────┘

MODE SWITCH RULES:
  - User says "switch to capture" → mode = CAPTURE, TTS: "OK, tell me what you learned."
  - User says "switch to review"  → mode = REVIEW, begin review session
  - User says "stop" / "done"     → mode = IDLE, TTS: "Session ended. [stats]"
  - User disconnects              → clean up, save any pending state

INTERRUPTION RULES (voice-specific):
  - During TTS playback, user speaks → Deepgram barge-in stops TTS
  - If mid-evaluation, ignore barge-in (don't cancel LLM call)
  - If mid-question presentation, barge-in = user wants to answer early (treat as answer)
```

---

## 4. State Management

### 4.1 What State Exists

```
STATE TYPE         │ WHERE STORED      │ LIFETIME
───────────────────┼───────────────────┼──────────────────────────────
FSRS card state    │ questions table   │ Permanent (until question deleted)
Review history     │ review_logs table │ Permanent (never deleted)
User data          │ users table       │ Permanent
Capture data       │ captures table    │ Permanent
Extracted facts    │ extracted_points  │ Permanent

Review session     │ Frontend state    │ Current page visit
  (which question  │ (React useState)  │ (lost on navigation/refresh)
   we're on, etc.) │                   │

Voice session      │ Backend memory    │ WebSocket connection lifetime
  (mode, awaiting  │ (Python dict per  │ (lost on disconnect)
   state, current  │  connection)      │
   question)       │                   │
```

### 4.2 Session State (Frontend — Phase 1)

```
ReviewSession (React state in /review page):

{
  questions: ReviewQuestion[]     // fetched from GET /due at page load
  currentIndex: number            // 0-based index into questions array
  phase: "question" | "evaluating" | "feedback" | "rating" | "complete"
  currentAnswer: string           // user's typed answer (cleared each question)
  evaluation: EvaluateResponse | null   // from POST /evaluate
  sessionStats: {
    total: number                 // questions.length
    answered: number              // how many the user has rated
    ratings: { 1: n, 2: n, 3: n, 4: n }  // distribution of user ratings this session
    startTime: Date               // when session started (for duration calc)
  }
}

STATE TRANSITIONS:
  page load                     → phase = "question", currentIndex = 0
  user submits answer           → phase = "evaluating" (show spinner)
  evaluate response arrives     → phase = "feedback" (show correct answer + feedback)
  user clicks rating button     → phase = "rating" (POST /rate, brief spinner)
  rate response arrives
    + more questions            → phase = "question", currentIndex++
    + no more questions         → phase = "complete" (show summary)
  user clicks "End Session"     → phase = "complete" (show partial summary)
```

### 4.3 Voice Session State (Backend — Phase 2)

```python
# In-memory state per WebSocket connection (not persisted to DB)

class VoiceSessionState:
    mode: Literal["idle", "capture", "review", "query"] = "idle"
    user_id: str

    # Review mode sub-state
    review_questions: list[ReviewQuestion] = []   # loaded once at review start
    current_question_index: int = 0
    awaiting: Literal["command", "answer", "rating"] | None = None   # what we expect next
    current_evaluation: EvaluateResponse | None = None

    # Capture mode buffer
    capture_buffer: str = ""   # accumulates speech across turns if needed

    # Timestamps
    mode_started_at: datetime | None = None
    last_activity: datetime | None = None
```

**State update rules:**

```
ON WebSocket connect:
  state = VoiceSessionState(mode="idle", user_id=authenticated_user_id)
  TTS: "Hey! What would you like to do? Capture, review, or search?"

ON transcript received:
  state.last_activity = NOW()
  Route to mode handler (see Decision Tree 2.2)

ON mode change:
  state.mode = new_mode
  state.mode_started_at = NOW()
  Reset mode-specific sub-state

ON WebSocket disconnect:
  IF state.mode == "review" AND state.current_question_index > 0:
    → stats are already persisted (each rating is a DB write)
    → no data loss
  Delete state from memory
  Log: "Voice session ended. Duration: {elapsed}. Questions reviewed: {n}"

ON inactivity (no transcript for 120 seconds):
  TTS: "Are you still there?"
  IF no response for 30 more seconds:
    → close WebSocket
    → same cleanup as disconnect
```

### 4.4 No Server-Side HTTP Session State

**Phase 1 backend is fully stateless for HTTP requests.** No session cookies, no server-side session store, no Redis.

```
Why:
  - Single user system (no auth needed in Phase 1)
  - Each request carries all needed info (question_id, rating, etc.)
  - FSRS state lives in the DB, not in memory
  - Frontend holds session state (which question we're on)

Implication:
  - User can refresh /review page → refetches due questions → loses current position
    This is ACCEPTABLE for Phase 1. Not worth adding server session for this.
  - To improve later: frontend can store currentIndex in sessionStorage
```

---

## 5. Edge Cases & Fallbacks

### 5.1 Input Edge Cases

```
EDGE CASE                        │ HANDLING
─────────────────────────────────┼─────────────────────────────────────────────
Empty raw_text (after trim)      │ 422 response. Frontend should also block empty submit.
                                 │
Whitespace-only input            │ Treated as empty after .strip(). 422.
                                 │
Very short input (<10 chars)     │ Frontend shows warning but allows submit.
                                 │ LLM extraction may return 0 facts. Return status="no_facts".
                                 │
Very long input (>50K chars)     │ 422 response. Frontend should enforce limit.
                                 │
Non-English input                │ Allow it. GPT-4.1 handles multilingual.
                                 │ Extraction quality may vary. No special handling.
                                 │
Input with only URLs             │ Phase 1: treat as raw text (extract what we can).
                                 │ Phase 4: URL ingestion parses the page.
                                 │
Input with code snippets         │ LLM should extract concepts from code.
                                 │ Code itself is not a "fact" — the concept behind it is.
                                 │
Duplicate capture (same text)    │ Phase 1: allow duplicates. No dedup logic.
                                 │ LLM may generate similar questions. Acceptable.
                                 │ Phase 4: add hash-based dedup check.
                                 │
HTML/script injection in text    │ raw_text is stored as-is (TEXT column, not HTML).
                                 │ Never rendered as raw HTML. Frontend uses React (auto-escapes).
                                 │ SQL: parameterized queries (asyncpg). No injection risk.
                                 │
Invalid UUID for question_id     │ 422 via Pydantic UUID validation.
                                 │
Rating out of range              │ 422 if not in [1,2,3,4].
                                 │
Rating for already-rated card    │ Allowed. FSRS handles repeated reviews.
                                 │ Each review creates a new review_log entry.
                                 │
Capture with why_it_matters only │ Invalid. raw_text is required. why_it_matters is optional context.
```

### 5.2 LLM Failure Modes

```
FAILURE MODE                     │ HANDLING
─────────────────────────────────┼─────────────────────────────────────────────
OpenAI API timeout (>30s)        │ Set timeout = 30s on httpx client.
                                 │ On timeout: fail gracefully per flow.
                                 │ Capture: save raw, return extraction_failed status.
                                 │ Evaluate: return fallback evaluation (see 3C).
                                 │ Query: return raw results without synthesis.
                                 │
OpenAI rate limit (429)          │ py retries with exponential backoff (httpx-retry or tenacity).
                                 │ Max 3 retries, 1s → 2s → 4s.
                                 │ After 3 retries: fail gracefully.
                                 │
OpenAI invalid response          │ Structured output guarantees valid JSON schema.
                                 │ If somehow invalid: catch ValidationError,
                                 │ log raw response, fail gracefully.
                                 │
LLM returns 0 facts for         │ Not an error. Some text has no extractable knowledge.
  valid input                    │ Return status="no_facts". User sees clear message.
                                 │
LLM returns hallucinated facts   │ Cannot detect automatically.
                                 │ Phase 4: add edit/delete buttons for questions.
                                 │ User can remove bad questions.
                                 │
LLM returns garbage questions    │ Structured output prevents schema violations.
                                 │ Semantic quality issues: iterate prompts.
                                 │ Phase 4: add flag/thumbs-down for bad questions.
                                 │
Embedding API fails              │ Capture: store fact without embedding (set to NULL).
                                 │ Query: fallback to full-text search.
                                 │ Partial degradation, not failure.
                                 │
API key invalid/expired          │ 401 from OpenAI → 500 to user.
                                 │ Log specific error. Clear message in logs.
                                 │
Model not available              │ 404 from OpenAI → 500 to user.
                                 │ Should be caught by using stable model names.
```

### 5.3 Database Failure Modes

```
FAILURE MODE                     │ HANDLING
─────────────────────────────────┼─────────────────────────────────────────────
DB connection pool exhausted     │ asyncpg will queue requests up to pool max.
                                 │ If all slots busy > 30s → ConnectionError.
                                 │ → 503 to user. Log pool stats.
                                 │
DB connection lost               │ asyncpg auto-reconnects on next query.
                                 │ Current request fails → 500. Next request works.
                                 │
Insert fails (constraint)        │ Unique violation: shouldn't happen (UUIDs).
                                 │ FK violation: capture deleted mid-processing.
                                 │ → 500 with specific error logged.
                                 │
Questions table empty            │ GET /due returns []. Dashboard shows due_today=0.
                                 │ Frontend: "No reviews due. Capture something first!"
                                 │
FSRS state corruption            │ If any FSRS column is NaN or negative:
                                 │ → Reset card to New state (state=0, due=NOW()).
                                 │ → Log warning. This is a py-fsrs bug, not user error.
                                 │
Concurrent rating of same card   │ Single-user system, unlikely in Phase 1.
                                 │ If happens: last write wins. Both review_logs are created.
                                 │ FSRS state from second write overwrites first. Acceptable.
```

### 5.4 Voice Edge Cases (Phase 2)

```
EDGE CASE                        │ HANDLING
─────────────────────────────────┼─────────────────────────────────────────────
User speaks but transcript       │ Deepgram returns empty string.
  is empty (background noise)    │ → Ignore. Do not change state.
                                 │ → TTS: nothing (don't say "I didn't hear you" for noise)
                                 │
User speaks gibberish            │ Transcript arrived but nonsensical.
                                 │ Capture: store it, LLM returns 0 facts. status="no_facts".
                                 │ Review answer: LLM evaluates as "wrong". Natural behavior.
                                 │ Rating: no keyword match → re-prompt.
                                 │
Voice rating ambiguous            │ "I think it was good but kind of hard"
  (multiple rating words)        │ Priority order: pick FIRST keyword match.
                                 │ "good" appears before "hard" → rating = 3 (Good).
                                 │ OR: use a simple LLM call to classify (adds latency).
                                 │ Phase 1 choice: first keyword wins. Fast, deterministic.
                                 │
User barge-in during TTS         │ Deepgram handles: stops TTS playback automatically.
                                 │ Backend: cancel current TTS, process new transcript.
                                 │ IF mid-question → treat barge-in as early answer attempt.
                                 │ IF mid-feedback → user wants to move on. Process as command.
                                 │
WebSocket drops mid-review       │ All previously rated cards are already persisted.
                                 │ Current unanswered question: no data loss (no answer to save).
                                 │ User reconnects → new session → re-fetches due questions.
                                 │
Mic permission denied            │ Frontend issue. Show: "Mic access needed for voice mode."
                                 │ Offer text-only fallback.
                                 │
Multiple simultaneous sessions   │ Single-user system: should only have one voice session.
                                 │ On new WebSocket connect: close previous WebSocket.
                                 │ Send close frame with reason: "New session opened."
```

### 5.5 Frontend Edge Cases

```
EDGE CASE                        │ HANDLING
─────────────────────────────────┼─────────────────────────────────────────────
Network error on API call        │ Frontend shows: "Connection error. Tap to retry."
                                 │ Retry button re-sends the same request.
                                 │ Do NOT auto-retry mutations (captures, ratings).
                                 │ OK to auto-retry reads (due, stats) once.
                                 │
User navigates away mid-review   │ Current question answer is lost (not submitted).
                                 │ All previously rated questions are safe (persisted).
                                 │ Acceptable for Phase 1. No "are you sure?" prompt needed.
                                 │
User double-clicks rating button │ Disable buttons after first click (until response arrives).
                                 │ Backend: idempotent? No — creates another review_log.
                                 │ Fix: frontend disables buttons. That's sufficient.
                                 │
User submits empty answer        │ Frontend blocks empty submit (disable "Check" button if empty).
                                 │ Backend also validates (defense in depth).
                                 │
Page refresh during review       │ Loses currentIndex. Re-fetches due questions.
                                 │ May re-show already-rated questions? No — rated questions
                                 │ have updated due dates, so GET /due won't return them
                                 │ (unless rated Again and still due). This is correct behavior.
                                 │
Backend returns 500              │ Frontend shows: "Something went wrong. Try again."
                                 │ Log error to console (for debugging).
                                 │ Never show raw error messages to user.
```

---

## 6. Pseudocode

### 6.1 Main Application Entry Point

```python
# main.py — FastAPI app setup and request lifecycle

app = FastAPI()

# Global exception handler
@app.exception_handler(Exception)
async def global_handler(request, exc):
    log.error(f"Unhandled error: {exc}", request_path=request.url.path)
    return JSONResponse(status_code=500, content={"error": "Internal server error"})

# Lifespan: startup/shutdown
@asynccontextmanager
async def lifespan(app):
    # STARTUP
    app.state.db_pool = await create_db_pool(settings.DATABASE_URL)
    app.state.openai = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    app.state.scheduler = Scheduler()  # py-fsrs, default params
    yield
    # SHUTDOWN
    await app.state.db_pool.close()

# CORS (allow Next.js frontend)
app.add_middleware(CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(captures_router, prefix="/api/captures")
app.include_router(reviews_router, prefix="/api/reviews")
app.include_router(knowledge_router, prefix="/api/knowledge")
app.include_router(stats_router, prefix="/api/stats")
```

### 6.2 Capture Flow

```python
# routers/captures.py

@router.post("")
async def create_capture(req: CaptureRequest, request: Request):
    service = CaptureService(
        db=request.app.state.db_pool,
        openai=request.app.state.openai,
    )
    result = await service.process(req.raw_text, req.source_type, req.why_it_matters)
    return result


# services/capture_service.py

class CaptureService:
    def __init__(self, db, openai):
        self.db = db
        self.llm = LLMClient(openai)
        self.embedder = Embedder(openai)

    async def process(self, raw_text: str, source_type: str,
                      why_it_matters: str | None) -> CaptureResponse:
        start = time_ms()

        # 1. Store raw capture
        capture_id = await db_queries.insert_capture(
            self.db, raw_text, source_type, why_it_matters
        )

        # 2. Extract facts
        try:
            extracted = await self.llm.extract_facts(raw_text, why_it_matters)
        except LLMError as e:
            log.error(f"Extraction failed for capture {capture_id}: {e}")
            await db_queries.update_capture_status(self.db, capture_id, "extraction_failed")
            return CaptureResponse(
                capture_id=capture_id, facts_count=0, questions_count=0,
                status="extraction_failed",
                processing_time_ms=time_ms() - start
            )

        if len(extracted.facts) == 0:
            await db_queries.update_capture_status(self.db, capture_id, "no_facts")
            return CaptureResponse(
                capture_id=capture_id, facts_count=0, questions_count=0,
                status="no_facts",
                processing_time_ms=time_ms() - start
            )

        # 3. Store facts + embeddings
        point_ids = []
        for fact in extracted.facts:
            try:
                embedding = await self.embedder.embed(fact.content)
            except EmbeddingError:
                embedding = None  # store fact without embedding, not fatal

            point_id = await db_queries.insert_extracted_point(
                self.db, capture_id, fact.content, fact.content_type, embedding
            )
            point_ids.append(point_id)

        # 4. Generate questions + select technique (PARALLEL)
        questions_task = self.llm.generate_questions(extracted.facts)
        technique_task = self.llm.select_technique(extracted.facts)

        try:
            questions_result, technique_result = await asyncio.gather(
                questions_task, technique_task,
                return_exceptions=True
            )
        except Exception:
            questions_result = GeneratedQuestions(questions=[])
            technique_result = TechniqueSelection(technique="none", instructions="")

        # Handle individual task failures from gather
        if isinstance(questions_result, Exception):
            log.warning(f"Question gen failed: {questions_result}")
            questions_result = GeneratedQuestions(questions=[])
        if isinstance(technique_result, Exception):
            log.warning(f"Technique selection failed: {technique_result}")
            technique_result = TechniqueSelection(technique="none", instructions="")

        # 5. Store questions with FSRS initial state
        questions_stored = 0
        for i, q in enumerate(questions_result.questions[:5]):  # max 5
            # Map question to source fact (best-effort: use index if available)
            point_id = point_ids[min(i, len(point_ids) - 1)]

            try:
                await db_queries.insert_question(
                    self.db,
                    extracted_point_id=point_id,
                    question_text=q.question_text,
                    answer_text=q.answer_text,
                    question_type=q.question_type,
                    technique_used=technique_result.technique,
                    mnemonic_hint=technique_result.instructions if technique_result.technique != "none" else None,
                    # FSRS initial state
                    due=datetime.now(timezone.utc),
                    stability=0, difficulty=0,
                    elapsed_days=0, scheduled_days=0,
                    reps=0, lapses=0, state=0,
                    last_review=None,
                )
                questions_stored += 1
            except DBError as e:
                log.error(f"Failed to insert question: {e}")
                continue  # skip this question, try the rest

        return CaptureResponse(
            capture_id=capture_id,
            facts_count=len(extracted.facts),
            questions_count=questions_stored,
            status="complete",
            processing_time_ms=time_ms() - start,
        )
```

### 6.3 Review Flow

```python
# routers/reviews.py

@router.get("/due")
async def get_due(request: Request, limit: int = 20):
    service = ReviewService(
        db=request.app.state.db_pool,
        openai=request.app.state.openai,
        scheduler=request.app.state.scheduler,
    )
    return await service.get_due(limit=limit)


@router.post("/evaluate")
async def evaluate(req: EvaluateRequest, request: Request):
    service = ReviewService(
        db=request.app.state.db_pool,
        openai=request.app.state.openai,
        scheduler=request.app.state.scheduler,
    )
    return await service.evaluate_answer(req.question_id, req.user_answer)


@router.post("/rate")
async def rate(req: RateRequest, request: Request):
    service = ReviewService(
        db=request.app.state.db_pool,
        openai=request.app.state.openai,
        scheduler=request.app.state.scheduler,
    )
    return await service.rate(req.question_id, req.rating)


# services/review_service.py

class ReviewService:
    def __init__(self, db, openai, scheduler):
        self.db = db
        self.llm = LLMClient(openai)
        self.fsrs = FSRSEngine(scheduler)

    async def get_due(self, limit: int = 20) -> DueResponse:
        rows = await db_queries.get_due_questions(self.db, limit)
        total = await db_queries.count_due_questions(self.db)

        questions = [
            ReviewQuestion(
                question_id=row["id"],
                question_text=row["question_text"],
                question_type=row["question_type"],
                mnemonic_hint=row["mnemonic_hint"],
                technique_used=row["technique_used"],
            )
            for row in rows
        ]
        return DueResponse(questions=questions, total_due=total)

    async def evaluate_answer(self, question_id: str,
                               user_answer: str) -> EvaluateResponse:
        # Fetch question + correct answer from DB
        row = await db_queries.get_question(self.db, question_id)
        if row is None:
            raise HTTPException(404, "Question not found")

        # LLM evaluation
        try:
            evaluation = await self.llm.evaluate_answer(
                question_text=row["question_text"],
                expected_answer=row["answer_text"],
                user_answer=user_answer,
            )
        except LLMError:
            # Fallback: basic word overlap
            expected_words = set(row["answer_text"].lower().split())
            answer_words = set(user_answer.lower().split())
            overlap = len(expected_words & answer_words) / max(len(expected_words), 1)

            if overlap >= 0.8:
                score, suggested = "correct", 3
            elif overlap >= 0.3:
                score, suggested = "partial", 2
            else:
                score, suggested = "wrong", 1

            evaluation = AnswerEvaluation(
                score=score,
                feedback="AI evaluation unavailable. Compare with the correct answer.",
                suggested_rating=suggested,
            )

        return EvaluateResponse(
            correct_answer=row["answer_text"],
            score=evaluation.score,
            feedback=evaluation.feedback,
            suggested_rating=evaluation.suggested_rating,
        )

    async def rate(self, question_id: str, rating: int) -> RateResponse:
        # Fetch current FSRS state
        row = await db_queries.get_question_fsrs_state(self.db, question_id)
        if row is None:
            raise HTTPException(404, "Question not found")

        # Reconstruct card + apply rating
        card = self.fsrs.card_from_row(row)
        old_state = card.state

        # Validate card state (guard against corruption)
        if math.isnan(card.stability) or card.stability < 0:
            log.warning(f"Corrupted FSRS state for {question_id}, resetting to New")
            card = Card()  # reset to fresh New card

        rating_enum = self.fsrs.map_rating(rating)
        now = datetime.now(timezone.utc)
        updated_card, review_log = self.fsrs.review(card, rating_enum, now)

        # Persist: update question + insert review_log
        await db_queries.update_question_fsrs(self.db, question_id, updated_card, now)
        await db_queries.insert_review_log(
            self.db, question_id, rating, old_state,
            card.stability, card.difficulty,
            card.elapsed_days, card.scheduled_days, now
        )

        return RateResponse(
            next_due=updated_card.due.isoformat(),
            interval_days=updated_card.scheduled_days,
            state=updated_card.state.value,
            state_label=updated_card.state.name,
        )
```

### 6.4 FSRS Engine (Core Module)

```python
# core/fsrs_engine.py

from fsrs import Scheduler, Card, Rating, State

class FSRSEngine:
    def __init__(self, scheduler: Scheduler | None = None):
        self.scheduler = scheduler or Scheduler()

    def card_from_row(self, row: dict) -> Card:
        """Reconstruct a py-fsrs Card from a database row."""
        card = Card()
        card.due = row["due"]
        card.stability = row["stability"]
        card.difficulty = row["difficulty"]
        card.elapsed_days = row["elapsed_days"]
        card.scheduled_days = row["scheduled_days"]
        card.reps = row["reps"]
        card.lapses = row["lapses"]
        card.state = State(row["state"])
        card.last_review = row["last_review"]
        return card

    def map_rating(self, rating: int) -> Rating:
        """Map integer 1-4 to py-fsrs Rating enum."""
        mapping = {
            1: Rating.Again,
            2: Rating.Hard,
            3: Rating.Good,
            4: Rating.Easy,
        }
        if rating not in mapping:
            raise ValueError(f"Invalid rating: {rating}. Must be 1-4.")
        return mapping[rating]

    def review(self, card: Card, rating: Rating,
               now: datetime) -> tuple[Card, ReviewLog]:
        """Apply a review to a card. Returns updated card + log."""
        result = self.scheduler.review_card(card, rating, now)
        return result  # (Card, ReviewLog)

    def is_due(self, card: Card, now: datetime) -> bool:
        """Check if a card is due for review."""
        if card.state in (State.New, State.Learning, State.Relearning):
            return True   # these states are always "due"
        if card.state == State.Review:
            return card.due <= now
        return False

    def card_to_dict(self, card: Card) -> dict:
        """Serialize a Card to a dict for DB storage."""
        return {
            "due": card.due,
            "stability": card.stability,
            "difficulty": card.difficulty,
            "elapsed_days": card.elapsed_days,
            "scheduled_days": card.scheduled_days,
            "reps": card.reps,
            "lapses": card.lapses,
            "state": card.state.value,
            "last_review": card.last_review,
        }
```

### 6.5 LLM Client (Core Module)

```python
# core/llm.py

class LLMClient:
    def __init__(self, openai_client):
        self.client = openai_client
        self.prompts = {
            "extraction": load_prompt("prompts/extraction.txt"),
            "question_generation": load_prompt("prompts/question_generation.txt"),
            "answer_evaluation": load_prompt("prompts/answer_evaluation.txt"),
            "technique_selection": load_prompt("prompts/technique_selection.txt"),
        }

    async def extract_facts(self, raw_text: str,
                            why: str | None) -> ExtractedFacts:
        user_msg = raw_text
        if why:
            user_msg += f"\n\nContext (why this matters to me): {why}"

        return await self._structured_call(
            model="gpt-4.1-nano",
            system=self.prompts["extraction"],
            user=user_msg,
            response_format=ExtractedFacts,
            temperature=0.3,
            max_tokens=2000,
            timeout=30,
        )

    async def generate_questions(self, facts: list[Fact]) -> GeneratedQuestions:
        facts_json = json.dumps([f.model_dump() for f in facts])
        return await self._structured_call(
            model="gpt-4.1-nano",
            system=self.prompts["question_generation"],
            user=facts_json,
            response_format=GeneratedQuestions,
            temperature=0.5,
            max_tokens=3000,
            timeout=30,
        )

    async def evaluate_answer(self, question_text: str,
                               expected_answer: str,
                               user_answer: str) -> AnswerEvaluation:
        user_msg = (
            f"Question: {question_text}\n"
            f"Expected answer: {expected_answer}\n"
            f"User's answer: {user_answer}"
        )
        return await self._structured_call(
            model="gpt-4.1-mini",          # mini for evaluation (needs judgment)
            system=self.prompts["answer_evaluation"],
            user=user_msg,
            response_format=AnswerEvaluation,
            temperature=0.2,
            max_tokens=500,
            timeout=30,
        )

    async def select_technique(self, facts: list[Fact]) -> TechniqueSelection:
        facts_json = json.dumps([f.model_dump() for f in facts])
        return await self._structured_call(
            model="gpt-4.1-nano",
            system=self.prompts["technique_selection"],
            user=facts_json,
            response_format=TechniqueSelection,
            temperature=0.2,
            max_tokens=300,
            timeout=30,
        )

    async def synthesize_answer(self, query: str,
                                 context: list[str]) -> str:
        """Free-text synthesis for knowledge queries. Returns plain string."""
        system = (
            "You are a personal knowledge assistant. Answer using ONLY the "
            "provided context from the user's captured knowledge. If the context "
            "doesn't contain enough info, say so. Do not make up information."
        )
        context_block = "\n".join(f"- {c}" for c in context)
        user_msg = f"Question: {query}\n\nYour captured knowledge:\n{context_block}"

        response = await self.client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.3,
            max_tokens=1000,
        )
        return response.choices[0].message.content

    async def _structured_call(self, model, system, user, response_format,
                                temperature, max_tokens, timeout):
        """Core method: calls OpenAI with structured output (Pydantic model)."""
        try:
            response = await asyncio.wait_for(
                self.client.beta.chat.completions.parse(
                    model=model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    response_format=response_format,
                    temperature=temperature,
                    max_tokens=max_tokens,
                ),
                timeout=timeout,
            )
            parsed = response.choices[0].message.parsed
            if parsed is None:
                raise LLMError("Structured output returned None (refusal?)")
            return parsed

        except asyncio.TimeoutError:
            raise LLMError(f"LLM call timed out after {timeout}s")
        except openai.RateLimitError:
            raise LLMError("OpenAI rate limit exceeded")
        except openai.APIError as e:
            raise LLMError(f"OpenAI API error: {e}")


class LLMError(Exception):
    """Raised when an LLM call fails for any reason."""
    pass
```

### 6.6 Knowledge Flow

```python
# services/knowledge_service.py

class KnowledgeService:
    def __init__(self, db, openai):
        self.db = db
        self.llm = LLMClient(openai)
        self.embedder = Embedder(openai)

    async def search(self, query: str, limit: int = 5) -> list[KnowledgeItem]:
        """Pure vector search. No LLM synthesis."""
        try:
            embedding = await self.embedder.embed(query)
        except EmbeddingError:
            # Fallback: full-text search
            return await db_queries.fulltext_search(self.db, query, limit)

        results = await db_queries.vector_search(self.db, embedding, limit)

        if not results:
            return []

        return [
            KnowledgeItem(
                content=r["content"],
                similarity=r["similarity"],
                capture_date=r["capture_date"],
                source_type=r["source_type"],
            )
            for r in results
        ]

    async def query(self, query: str) -> QueryResponse:
        """Vector search + LLM synthesis."""
        items = await self.search(query, limit=5)

        if not items:
            return QueryResponse(
                answer="I don't have any knowledge matching that query yet.",
                sources=[],
            )

        # Filter low-similarity results
        relevant = [i for i in items if i.similarity >= 0.3]
        if not relevant:
            return QueryResponse(
                answer="I found some results but they don't seem closely related.",
                sources=items,  # show all, let user judge
            )

        # Synthesize
        try:
            context = [f"[{i.capture_date}] {i.content}" for i in relevant]
            answer = await self.llm.synthesize_answer(query, context)
        except LLMError:
            answer = "Here's what I found (AI summary unavailable):"

        return QueryResponse(answer=answer, sources=relevant)
```

### 6.7 Voice Orchestrator (Phase 2)

```python
# routers/voice.py (Phase 2)

RATING_KEYWORDS = {
    "again": 1, "forgot": 1, "no": 1, "nope": 1, "wrong": 1,
    "hard": 2, "difficult": 2, "barely": 2, "struggled": 2,
    "good": 3, "got it": 3, "yes": 3, "correct": 3, "right": 3,
    "easy": 4, "obvious": 4, "trivial": 4, "simple": 4, "knew it": 4,
}

CAPTURE_TRIGGERS = {"remember", "save", "note", "capture", "i learned", "learned"}
REVIEW_TRIGGERS = {"quiz", "review", "test me", "start review", "quiz me"}
QUERY_TRIGGERS = {"what", "when", "how", "why", "tell me", "search", "find"}
STOP_WORDS = {"stop", "done", "end", "quit", "exit", "goodbye"}
SKIP_WORDS = {"skip", "next", "pass"}


@router.websocket("/ws/voice")
async def voice_session(ws: WebSocket, request: Request):
    await ws.accept()
    state = VoiceSessionState(mode="idle")

    # Close any existing voice session for this user
    # (single-session enforcement)

    await tts(ws, "Hey! Would you like to capture, review, or search?")

    try:
        while True:
            transcript = await receive_transcript(ws)

            if not transcript or not transcript.strip():
                continue  # ignore empty/noise

            transcript = transcript.strip().lower()
            state.last_activity = datetime.now(timezone.utc)

            # ── IDLE MODE: detect intent ──
            if state.mode == "idle":
                if any(t in transcript for t in STOP_WORDS):
                    await tts(ws, "Goodbye!")
                    break

                if any(t in transcript for t in CAPTURE_TRIGGERS):
                    state.mode = "capture"
                    # Strip trigger word, use remainder as first input
                    remainder = strip_trigger(transcript, CAPTURE_TRIGGERS)
                    if remainder:
                        result = await capture_service.process(remainder, "voice", None)
                        await tts(ws, f"Got it. {result.facts_count} facts, "
                                      f"{result.questions_count} questions created.")
                        state.mode = "idle"  # back to idle after one capture
                    else:
                        await tts(ws, "OK, tell me what you learned.")

                elif any(t in transcript for t in REVIEW_TRIGGERS):
                    state.mode = "review"
                    due = await review_service.get_due(limit=20)
                    if not due.questions:
                        await tts(ws, "No reviews due right now. All caught up!")
                        state.mode = "idle"
                    else:
                        state.review_questions = due.questions
                        state.current_question_index = 0
                        state.awaiting = "answer"
                        q = state.review_questions[0]
                        await tts(ws, q.question_text)

                elif any(transcript.startswith(t) for t in QUERY_TRIGGERS):
                    result = await knowledge_service.query(transcript)
                    await tts(ws, result.answer)
                    state.mode = "idle"

                else:
                    await tts(ws, "I didn't catch that. Capture, review, or search?")

            # ── CAPTURE MODE ──
            elif state.mode == "capture":
                if any(t in transcript for t in STOP_WORDS):
                    state.mode = "idle"
                    await tts(ws, "Capture mode ended.")
                else:
                    result = await capture_service.process(transcript, "voice", None)
                    await tts(ws, f"Captured. {result.facts_count} facts, "
                                  f"{result.questions_count} questions. "
                                  f"Tell me more, or say done.")

            # ── REVIEW MODE ──
            elif state.mode == "review":
                if any(t in transcript for t in STOP_WORDS):
                    answered = state.current_question_index
                    state.mode = "idle"
                    await tts(ws, f"Review ended. You answered {answered} questions.")
                    continue

                if state.awaiting == "answer":
                    if any(t in transcript for t in SKIP_WORDS):
                        # Skip this question
                        state.current_question_index += 1
                        if state.current_question_index >= len(state.review_questions):
                            state.mode = "idle"
                            await tts(ws, "Review complete! Nice work.")
                        else:
                            state.awaiting = "answer"
                            q = state.review_questions[state.current_question_index]
                            await tts(ws, f"Next question. {q.question_text}")
                        continue

                    # Evaluate the spoken answer
                    q = state.review_questions[state.current_question_index]
                    evaluation = await review_service.evaluate_answer(
                        q.question_id, transcript
                    )
                    state.current_evaluation = evaluation
                    state.awaiting = "rating"
                    await tts(ws, f"{evaluation.feedback}. "
                                  f"The answer was: {evaluation.correct_answer}. "
                                  f"How did you do? Again, Hard, Good, or Easy?")

                elif state.awaiting == "rating":
                    rating = parse_rating(transcript)
                    if rating is None:
                        await tts(ws, "Didn't catch that. Again, Hard, Good, or Easy?")
                        continue

                    q = state.review_questions[state.current_question_index]
                    result = await review_service.rate(q.question_id, rating)
                    state.current_question_index += 1

                    if state.current_question_index >= len(state.review_questions):
                        total = len(state.review_questions)
                        state.mode = "idle"
                        await tts(ws, f"Review complete! {total} questions done.")
                    else:
                        state.awaiting = "answer"
                        next_q = state.review_questions[state.current_question_index]
                        await tts(ws, f"Next. {next_q.question_text}")

            # ── QUERY MODE ──
            elif state.mode == "query":
                # Query mode is one-shot (handled in idle), shouldn't reach here
                state.mode = "idle"

    except WebSocketDisconnect:
        log.info("Voice session disconnected")
    finally:
        # Cleanup: all data already persisted per-action
        pass


def parse_rating(transcript: str) -> int | None:
    """Extract rating from spoken text. Returns 1-4 or None."""
    transcript = transcript.lower().strip()

    # Check exact matches first
    if transcript in RATING_KEYWORDS:
        return RATING_KEYWORDS[transcript]

    # Check if any keyword appears in transcript (first match wins)
    for keyword, rating in RATING_KEYWORDS.items():
        if keyword in transcript:
            return rating

    # Check for digit
    for char in transcript:
        if char in "1234":
            return int(char)

    return None  # unrecognized
```

### 6.8 DB Queries Module

```python
# core/db_queries.py
# All SQL in one place. All functions take pool as first arg.

async def insert_capture(pool, raw_text, source_type, why_it_matters) -> str:
    return await pool.fetchval(
        """INSERT INTO captures (raw_text, source_type, why_it_matters)
           VALUES ($1, $2, $3) RETURNING id""",
        raw_text, source_type, why_it_matters
    )

async def insert_extracted_point(pool, capture_id, content,
                                  content_type, embedding) -> str:
    return await pool.fetchval(
        """INSERT INTO extracted_points (capture_id, content, content_type, embedding)
           VALUES ($1, $2, $3, $4) RETURNING id""",
        capture_id, content, content_type, embedding
    )

async def insert_question(pool, *, extracted_point_id, question_text, answer_text,
                           question_type, technique_used, mnemonic_hint,
                           due, stability, difficulty, elapsed_days,
                           scheduled_days, reps, lapses, state, last_review) -> str:
    return await pool.fetchval(
        """INSERT INTO questions
           (extracted_point_id, question_text, answer_text, question_type,
            technique_used, mnemonic_hint,
            due, stability, difficulty, elapsed_days,
            scheduled_days, reps, lapses, state, last_review)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)
           RETURNING id""",
        extracted_point_id, question_text, answer_text, question_type,
        technique_used, mnemonic_hint,
        due, stability, difficulty, elapsed_days,
        scheduled_days, reps, lapses, state, last_review,
    )

async def get_due_questions(pool, limit: int) -> list[dict]:
    return await pool.fetch(
        """SELECT id, question_text, answer_text, question_type,
                  technique_used, mnemonic_hint, state, due
           FROM questions
           WHERE state IN (0, 1, 3)
              OR (state = 2 AND due <= NOW())
           ORDER BY
               CASE state WHEN 3 THEN 1 WHEN 1 THEN 2
                          WHEN 0 THEN 3 WHEN 2 THEN 4 END,
               due ASC
           LIMIT $1""",
        limit
    )

async def count_due_questions(pool) -> int:
    return await pool.fetchval(
        """SELECT COUNT(*) FROM questions
           WHERE state IN (0, 1, 3)
              OR (state = 2 AND due <= NOW())"""
    )

async def get_question(pool, question_id: str) -> dict | None:
    return await pool.fetchrow(
        "SELECT * FROM questions WHERE id = $1", question_id
    )

async def get_question_fsrs_state(pool, question_id: str) -> dict | None:
    return await pool.fetchrow(
        """SELECT due, stability, difficulty, elapsed_days,
                  scheduled_days, reps, lapses, state, last_review
           FROM questions WHERE id = $1""",
        question_id
    )

async def update_question_fsrs(pool, question_id, card, now):
    await pool.execute(
        """UPDATE questions
           SET due=$2, stability=$3, difficulty=$4, elapsed_days=$5,
               scheduled_days=$6, reps=$7, lapses=$8, state=$9, last_review=$10
           WHERE id = $1""",
        question_id, card.due, card.stability, card.difficulty,
        card.elapsed_days, card.scheduled_days, card.reps,
        card.lapses, card.state.value, now,
    )

async def insert_review_log(pool, question_id, rating, state,
                              stability, difficulty, elapsed_days,
                              scheduled_days, reviewed_at):
    await pool.execute(
        """INSERT INTO review_logs
           (question_id, rating, state, stability, difficulty,
            elapsed_days, scheduled_days, reviewed_at)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8)""",
        question_id, rating, state, stability, difficulty,
        elapsed_days, scheduled_days, reviewed_at,
    )

async def vector_search(pool, embedding, limit: int) -> list[dict]:
    return await pool.fetch(
        """SELECT ep.content, ep.content_type,
                  c.created_at as capture_date, c.source_type,
                  1 - (ep.embedding <=> $1::vector) AS similarity
           FROM extracted_points ep
           JOIN captures c ON ep.capture_id = c.id
           WHERE ep.embedding IS NOT NULL
           ORDER BY ep.embedding <=> $1::vector
           LIMIT $2""",
        embedding, limit
    )

async def fulltext_search(pool, query: str, limit: int) -> list[dict]:
    return await pool.fetch(
        """SELECT ep.content, ep.content_type,
                  c.created_at as capture_date, c.source_type,
                  ts_rank(to_tsvector('english', ep.content),
                          plainto_tsquery('english', $1)) AS similarity
           FROM extracted_points ep
           JOIN captures c ON ep.capture_id = c.id
           WHERE to_tsvector('english', ep.content)
                 @@ plainto_tsquery('english', $1)
           ORDER BY similarity DESC
           LIMIT $2""",
        query, limit
    )

async def get_dashboard_stats(pool) -> dict:
    return await pool.fetchrow(
        """WITH
             due_count AS (
               SELECT COUNT(*) as n FROM questions
               WHERE state IN (0,1,3) OR (state = 2 AND due <= NOW())
             ),
             review_today AS (
               SELECT COUNT(*) as n FROM review_logs
               WHERE reviewed_at >= CURRENT_DATE
             ),
             retention AS (
               SELECT COUNT(*) FILTER (WHERE rating >= 3) as correct,
                      COUNT(*) as total
               FROM review_logs
               WHERE reviewed_at >= NOW() - INTERVAL '30 days'
             ),
             streak AS (
               SELECT COUNT(DISTINCT DATE(reviewed_at)) as days
               FROM review_logs
               WHERE reviewed_at >= (
                 SELECT COALESCE(
                   (SELECT DATE(d) + INTERVAL '1 day'
                    FROM generate_series(
                      CURRENT_DATE - INTERVAL '365 days',
                      CURRENT_DATE, '1 day') d
                    WHERE DATE(d) NOT IN (
                      SELECT DISTINCT DATE(reviewed_at) FROM review_logs)
                      AND DATE(d) < CURRENT_DATE
                    ORDER BY d DESC LIMIT 1),
                   CURRENT_DATE - INTERVAL '365 days'
                 )
               )
             ),
             totals AS (
               SELECT (SELECT COUNT(*) FROM captures) as total_captures,
                      (SELECT COUNT(*) FROM questions) as total_questions
             )
           SELECT due_count.n as due_today,
                  review_today.n as reviews_today,
                  CASE WHEN retention.total > 0
                    THEN ROUND(100.0 * retention.correct / retention.total)
                    ELSE 0 END as retention_rate,
                  streak.days as streak_days,
                  totals.total_captures,
                  totals.total_questions
           FROM due_count, review_today, retention, streak, totals"""
    )
```

---

## Appendix: Complete Condition Reference

Quick lookup for every condition/branch in the system:

```
CONDITION                              →  ACTION
───────────────────────────────────────────────────────────────────
raw_text empty                         →  422
raw_text > 50K chars                   →  422
source_type invalid                    →  422
extraction LLM fails                   →  save raw, return extraction_failed
extraction returns 0 facts             →  return no_facts
embedding fails                        →  store fact without embedding
question gen fails                     →  store facts, 0 questions
technique selection fails              →  technique = "none"
question insert fails                  →  skip question, continue
question_id not found                  →  404
rating not 1-4                         →  422
FSRS state corrupted                   →  reset card to New
user_answer empty                      →  422
evaluate LLM fails                     →  word-overlap fallback
query empty                            →  422
query embedding fails                  →  full-text search fallback
vector search 0 results                →  "no knowledge yet"
vector search all sim < 0.3            →  "results don't seem related"
synthesis LLM fails                    →  return raw results
no due questions                       →  return empty list
voice transcript empty                 →  ignore
voice rating unrecognized              →  re-prompt
voice intent unclear                   →  ask "capture, review, or search?"
voice WebSocket disconnect             →  cleanup, data already persisted
voice inactivity > 120s                →  prompt, then close after 30s more
frontend network error (read)          →  show retry, auto-retry once
frontend network error (mutation)      →  show retry, no auto-retry
frontend double-click rating           →  disable buttons after first click
```
