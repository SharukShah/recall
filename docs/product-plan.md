# Product Plan — ReCall: Voice-First Personal Memory Assistant
**Version:** 1.0
**Date:** April 14, 2026
**Status:** Pre-build
**Author:** Sharuk

---

## 1. The Problem

### What's Actually Happening
Poor memory and recall is not a hardware problem — it's a **system failure**. Most people (including the founder) have:

- **Zero capture system** — information enters the brain and is never persisted
- **Zero review system** — even when something is noted, it's never revisited
- **Zero retrieval practice** — the brain is never forced to *pull* information out, which is the #1 way to strengthen memory

The result: ~70% of what you learn is forgotten within 24 hours (Ebbinghaus forgetting curve). Over a week, it's 90%+.

### Who Has This Problem
- Software developers who can't remember syntax, patterns, APIs they've used before
- Students and lifelong learners who read/watch but retain almost nothing
- Professionals who forget meeting decisions, conversations, and commitments
- Anyone consuming 3-5+ sources of information daily with nothing sticking

### Why Existing Solutions Fail

| Tool | What It Does | Why It Fails |
|---|---|---|
| **Anki** | Flashcard-based spaced repetition | Manual card creation is too much effort. Users quit. Text-only. No conversation. |
| **Notion / Obsidian** | Note-taking and knowledge management | Write-only graveyard. Notes are never revisited. No active recall. |
| **RemNote** | Notes + spaced repetition | Better than Anki but still text-first. No voice. No conversational learning. |
| **Pimsleur** | Audio-based graduated interval recall | Language-only. Pre-scripted. No personalization. Can't learn arbitrary topics. |
| **Pi.ai** | Personal conversational AI | No memory. No spaced repetition. Conversations are ephemeral. |
| **ChatGPT** | General AI assistant | No persistent structured memory. No spaced repetition. Doesn't quiz you proactively. |

### The Gap
**No product combines:**
1. Voice-first conversational AI
2. Persistent personal knowledge base
3. Spaced repetition scheduling (FSRS-level algorithm)
4. Active recall through natural dialogue
5. Multiple memory techniques (chunking, mnemonics, elaboration, method of loci)
6. Pimsleur-style anticipation for any knowledge domain — not just languages
7. Personal assistant capabilities (query your own knowledge)

---

## 2. The Solution

### One-Line Definition
> A voice-first AI personal assistant that captures what you learn, teaches it back using proven memory techniques, and ensures you never forget it through conversational spaced repetition.

### What It Does (5 Core Jobs)

1. **Captures knowledge effortlessly** — Talk or type what you learned. AI extracts the key facts, concepts, and insights. No manual card creation.

2. **Teaches using memory science** — AI applies the right memory technique based on content type: chunking for lists, mnemonics for vocabulary, elaboration for concepts, method of loci for sequences.

3. **Forces active recall** — Every review is a conversation, not a re-read. AI asks you to produce the answer (Pimsleur anticipation principle), then gives feedback.

4. **Schedules reviews optimally** — FSRS algorithm (state-of-the-art, trained on 700M+ reviews) schedules each item at the exact moment you're about to forget it.

5. **Acts as a personal assistant** — "What did my team decide about the auth migration?" — queries your entire knowledge base by voice.

### The Difference

| What Others Do | What ReCall Does |
|---|---|
| You create flashcards manually | AI generates questions from your voice/text input automatically |
| You read cards on a screen | AI quizzes you through conversation — voice-first |
| One technique (spaced repetition only) | 6+ memory techniques orchestrated by AI per content type |
| You decide when to review | AI schedules optimally and prompts you proactively |
| Notes are static | Knowledge is alive — connected, searchable, actively reinforced |
| Text-only | Voice-first with text fallback |
| Learning tool | Learning tool + personal assistant |

---

## 3. How It Works (User Experience)

### 3.1 Capture Flow

**Voice (primary):**
> "Hey Recall, today I learned that WebSockets keep a persistent TCP connection open unlike HTTP which is request-response. The server can push data without the client asking."

**Text (fallback):**
> Quick text box → paste anything → submit

**What AI does automatically:**
1. Extracts key facts: "WebSockets are persistent connections", "Differ from HTTP request-response", "Server can push data unprompted"
2. Selects memory techniques based on content type
3. Generates 3-5 retrieval questions
4. Creates a mnemonic or analogy if applicable
5. Schedules first review (typically next day)

**The "Why does this matter?" prompt:**
After every capture, AI asks: "Why is this important to you?" — Forces one sentence of reflection, dramatically improves encoding. Takes 5 seconds.

### 3.2 Teaching Flow (Teach Me Mode)

User: "Recall, teach me how binary search works."

AI responds using layered memory techniques:
1. **Chunking** — Breaks concept into 3-4 digestible pieces
2. **Elaboration** — Adds analogies ("like finding a name in a phone book")
3. **Active Recall** — Tests after each chunk ("tell me back what we just covered")
4. **Mnemonic** — Creates memorable hook ("Binary = Bisect — cut in two")
5. **Dual Coding** — Prompts user to visualize ("picture a library with a million books, finding yours in 20 glances")

### 3.3 Review Flow (Daily Session)

**Morning prompt:** "You have 8 items to review today. Ready?"

Each item follows the Pimsleur anticipation pattern:
1. AI asks question (open-ended, not multiple choice)
2. **Pause** — user produces answer from memory
3. AI reveals correct answer + gives feedback
4. User self-rates: Forgot / Partial / Got it
5. Algorithm adjusts next review interval

**Session features:**
- Interleaving: items shuffled across topics (not grouped)
- Connection questions: "How does X relate to Y you learned last week?"
- Explain-back prompts: "Explain this concept in your own words"
- Takes 3-5 minutes for most sessions

### 3.4 Personal Assistant Flow (Query Mode)

> "What did my team decide about auth last Thursday?"

> "What were the three design patterns I captured from that article?"

> "When is the deadline for the migration project?"

AI searches your entire knowledge base semantically and responds with the relevant information + context (when you captured it, from what source).

### 3.5 Evening Reflection

Daily 9 PM prompt:
> "What did you learn today? Even 1-2 sentences."

This single habit forces consolidation. Even without other captures, this alone improves next-day recall. The response gets extracted and added to the review queue.

---

## 4. Memory Techniques — How Each Is Implemented

### Technique Selection Matrix
AI automatically selects techniques based on content type:

| Content Type | Primary Techniques | Example |
|---|---|---|
| Ordered list / steps | Chunking + Method of Loci + Active Recall | "The 5 stages of grief" |
| Vocabulary / terminology | Mnemonic + Dual Coding + Spaced Repetition | "What is idempotent?" |
| Concept / how-it-works | Elaboration + Chunking + Teach-back | "How does DNS work?" |
| Fact / data point | Mnemonic + Association + Active Recall | "Python GIL only affects CPU-bound" |
| Conversation / meeting | Association + Active Recall + Spaced Repetition | "Team auth decision" |
| Comparison / difference | Interleaving + Elaboration + Active Recall | "REST vs GraphQL" |
| Skill / procedure | Chunking + Active Recall + Spaced Repetition | "Docker setup process" |

### Technique Details

| Technique | Scientific Basis | Implementation |
|---|---|---|
| **Active Recall** | Retrieving info strengthens the memory trace more than re-reading. Dual hippocampal action (Wiklund-Hörnqvist, 2021). Benefits persist for years. | Every review = produce the answer before seeing it. Open-ended questions, not recognition. |
| **Spaced Repetition** | Reviewing at increasing intervals resets the forgetting curve. Each harder retrieval creates deeper processing. | FSRS algorithm. Intervals expand: 1d → 3d → 7d → 14d → 30d → 90d based on performance. |
| **Chunking** | Bypasses working memory limit (~3-4 items). Auditory presentation → larger chunks (modality effect). | AI breaks info into groups of 3-4. Especially effective in voice delivery. |
| **Mnemonics** | Activates medial temporal lobe. Transforms abstract info into spatial/personal/sensory forms. | AI generates acronyms, acrostics, keyword associations, rhymes. Voice delivery enables jingles. |
| **Elaboration** | Deeper semantic processing creates multiple retrieval pathways (Craik & Tulving, 1975). | AI adds analogies, context, reasons. Asks "what does this remind you of?" to create personal connections. |
| **Method of Loci** | Hijacks the brain's spatial memory system (hippocampus). fMRI shows it reshapes brain networks (Dresler, 2017). | Guided audio walkthroughs: "You're in your kitchen. On the stove, picture [item 1]..." |
| **Interleaving** | Mixing topics forces discrimination learning and prevents illusion of competence. | Review sessions shuffle across topics. Never >3 consecutive items from same subject. |
| **Dual Coding** | Mind processes verbal + visual on separate channels. Images are recalled better (picture superiority effect). | Voice + mental imagery prompts: "Picture a seahorse replaying a movie in a theater." |

### The Universal Amplifier
**Active recall is the foundation.** Every other technique becomes significantly more effective when combined with retrieval practice. The voice-first conversational format is inherently a retrieval practice interface — this is the product's core structural advantage.

---

## 5. Technical Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    USER INTERFACE                        │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  Voice (AI)   │  │  Text Chat   │  │ Quick Capture │  │
│  │  (Primary)    │  │  (Fallback)  │  │ (Text/URL)    │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬────────┘  │
│         └─────────────────┼──────────────────┘           │
│                           ▼                              │
│  ┌──────────────────────────────────────────────────┐    │
│  │         CONVERSATION ENGINE (LLM)                │    │
│  │  • Intent detection (learn/review/ask/capture)   │    │
│  │  • Memory technique selection per content type   │    │
│  │  • Question generation + mnemonic creation       │    │
│  │  • Answer evaluation + feedback                  │    │
│  │  • Teach-me mode orchestration                   │    │
│  └──────────────────┬───────────────────────────────┘    │
│                     ▼                                    │
│  ┌──────────────────────────────────────────────────┐    │
│  │           MEMORY LAYER                           │    │
│  │                                                  │    │
│  │  ┌──────────────┐  ┌─────────────────────────┐   │    │
│  │  │  Knowledge   │  │  Spaced Repetition      │   │    │
│  │  │  Store       │  │  Scheduler (FSRS)       │   │    │
│  │  │  (PostgreSQL)│  │  • Per-item intervals   │   │    │
│  │  │              │  │  • Ease factors          │   │    │
│  │  │              │  │  • Due dates             │   │    │
│  │  └──────────────┘  └─────────────────────────┘   │    │
│  │                                                  │    │
│  │  ┌──────────────┐  ┌─────────────────────────┐   │    │
│  │  │  Semantic    │  │  Knowledge Graph         │   │    │
│  │  │  Search      │  │  • Concept connections   │   │    │
│  │  │  (pgvector)  │  │  • Topic relationships   │   │    │
│  │  │              │  │  • "What relates to X?"  │   │    │
│  │  └──────────────┘  └─────────────────────────┘   │    │
│  └──────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

### Tech Stack

| Layer | Technology | Rationale |
|---|---|---|
| **Voice Pipeline** | Deepgram Voice Agent API (Flux STT + Aura-2 TTS) | Single API for complete voice agent. Sub-300ms latency. BYO LLM. $4.50/hr all-inclusive. Native turn detection + barge-in. |
| **LLM** | GPT-4o (via Deepgram BYO LLM) | Best reasoning for memory technique orchestration. Function calling for memory queries mid-conversation. |
| **LLM (text tasks)** | GPT-4o-mini | Cost-efficient for extraction, question generation, answer evaluation during text captures. |
| **Frontend** | Next.js 15 + Tailwind CSS + shadcn/ui | PWA-capable (single codebase for web + mobile). WebRTC for browser voice. Fast to build. |
| **Backend** | FastAPI (Python) | Async WebSocket support. Memory layer APIs. FSRS implementation. Existing developer experience. |
| **Database** | PostgreSQL (Supabase) | Structured data: captures, questions, schedules, users. Free tier covers personal use. |
| **Vector Search** | pgvector (Supabase extension) | Semantic search over knowledge base. "What did I learn about X?" No separate vector DB needed. |
| **Spaced Repetition** | FSRS algorithm (Python implementation) | State-of-the-art. Trained on 700M+ reviews from 20K users. More accurate than SM-2. ~100 lines of code. |
| **Auth** | Supabase Auth | Ready-made. Free tier. Easy to add multi-user later. |
| **Notifications** | Web Push API + PWA | Review reminders. Daily reflection prompts. |

### Voice Pipeline Comparison (Why Deepgram)

| Option | Latency | Cost/hr | Voice Agent API | BYO LLM | Quality |
|---|---|---|---|---|---|
| **Deepgram (chosen)** | Sub-300ms | $4.50 | ✅ Unified | ✅ | Enterprise-grade |
| OpenAI Realtime | Native S2S | $8.64 | ✅ Realtime | ❌ Locked | Best reasoning |
| ElevenLabs | 75ms TTS | $10-20 | ✅ ElevenAgents | ✅ | Best voice quality |
| Google Cloud | Not optimized | $1.32+LLM | ❌ DIY | ✅ | Most languages |

**Upgrade path:** Start with Deepgram Aura-2 TTS → swap to ElevenLabs Flash v2.5 for premium voice quality (Deepgram supports BYO TTS natively).

### Data Model

```sql
-- Core entities
captures
  id, user_id, raw_text, source_type (voice/text/url), source_url,
  why_it_matters, created_at

extracted_points
  id, capture_id, content, content_type (fact/concept/list/comparison/procedure),
  embedding (vector), created_at

questions
  id, extracted_point_id, question_text, answer_text,
  question_type (open/cloze/explain/connect), technique_used,
  mnemonic_hint, created_at

review_schedule
  id, question_id, user_id, next_review_at, interval_days,
  stability, difficulty, elapsed_days, scheduled_days,
  last_rating, repetition_count, last_reviewed_at

review_log
  id, question_id, user_id, rating (1-4),
  user_answer, ai_feedback, reviewed_at

daily_reflections
  id, user_id, content, extracted_point_ids[], created_at

-- Knowledge graph (simple version using PostgreSQL)
concept_links
  id, point_a_id, point_b_id, relationship_type, strength, created_at
```

### Cost Estimate (Personal Use)

| Service | 15 min/day voice | 30 min/day voice |
|---|---|---|
| Deepgram Voice Agent | ~$2.25/month | ~$4.50/month |
| GPT-4o (BYO LLM) | ~$5-10/month | ~$10-15/month |
| GPT-4o-mini (text tasks) | ~$1-3/month | ~$2-5/month |
| Supabase (free tier) | $0 | $0 |
| **Total** | **~$8-15/month** | **~$16-25/month** |

---

## 6. Feature Specification

### MVP (Must-Have) — Phase 1 & 2

| # | Feature | What It Does | Memory Technique |
|---|---|---|---|
| 1 | **Quick Text Capture** | Paste/type anything learned → AI extracts key points + generates questions | Encoding |
| 2 | **"Why It Matters" Prompt** | One sentence forced reflection at capture time | Elaborative encoding |
| 3 | **AI Extraction Engine** | LLM parses raw input → extracts 3-7 key facts/concepts | Chunking |
| 4 | **Auto Question Generation** | AI generates 2-5 retrieval questions per capture, mixed formats | Active recall |
| 5 | **FSRS Scheduler** | Calculates optimal next review date per question | Spaced repetition |
| 6 | **Daily Review Session** | 5-10 min conversational quiz. Produce answer → reveal → rate. | Active recall + spaced repetition |
| 7 | **Interleaved Reviews** | Shuffle questions across topics in review sessions | Interleaving |
| 8 | **Voice Capture** | Talk about what you learned → AI processes | Low-friction encoding |
| 9 | **Voice Review** | Pimsleur-style: AI asks → pause → you answer → feedback | Active recall + anticipation |
| 10 | **Dashboard** | Items due, streak, retention rate, recent captures | Motivation + visibility |

### Post-MVP (Nice-to-Have) — Phase 3 & 4

| # | Feature | What It Does | Priority |
|---|---|---|---|
| 11 | **Teach Me Mode** | "Teach me about X" → AI teaches using chunking + elaboration + recall | High |
| 12 | **Knowledge Query (PA Mode)** | "What did I learn about X?" → semantic search over knowledge base | High |
| 13 | **Connection Questions** | AI asks how concept A relates to concept B from different captures | High |
| 14 | **Evening Reflection** | Daily "What did you learn today?" prompt with extraction | High |
| 15 | **Mnemonic Generation** | AI creates acronyms, analogies, visual hooks for difficult items | Medium |
| 16 | **Method of Loci** | Guided audio walkthrough for memorizing ordered lists | Medium |
| 17 | **URL Ingestion** | Paste a link → AI reads article → extracts key points | Medium |
| 18 | **Push Notifications** | "You have 8 items to review" — behavioral trigger | Medium |
| 19 | **Explain-Back Mode** | "Explain this in your own words" → AI evaluates understanding | Medium |
| 20 | **Knowledge Graph Viz** | See how your concepts connect visually | Low |
| 21 | **Analytics Dashboard** | Retention rate over time, weak areas, learning velocity | Low |
| 22 | **Voice Cloning** | Personal Jarvis voice via ElevenLabs | Low |
| 23 | **Meeting Summary Capture** | Record → transcribe → extract decisions + action items | Low |
| 24 | **Browser Extension** | Highlight text on any page → capture to ReCall | Low |

---

## 7. Execution Plan

### Phase 1: Text-First Core (Days 1-7)
**Goal:** Working capture → extract → generate → review pipeline.

- [ ] Set up Next.js project (Tailwind + shadcn/ui)
- [ ] Set up Supabase (PostgreSQL + pgvector + Auth)
- [ ] Create database schema and migrations
- [ ] Build Quick Capture UI (text box + submit)
- [ ] Integrate GPT-4o-mini for extraction + question generation
- [ ] Build extraction pipeline: raw text → extracted points → questions
- [ ] Add "Why does this matter?" prompt at capture
- [ ] End-to-end test: capture → see extracted points → see generated questions

### Phase 2: Review Engine (Days 8-14)
**Goal:** Working spaced repetition with daily review sessions.

- [ ] Implement FSRS algorithm in Python (FastAPI)
- [ ] Build review session UI: show question → text input → reveal answer → rate
- [ ] Implement review scheduling (due today queue)
- [ ] Add interleaving across topics in review queue
- [ ] Build dashboard: items due, total captured, streak counter
- [ ] Set up PWA basics for mobile access
- [ ] **START USING IT DAILY** — seed with real learning data

### Phase 3: Voice Layer (Days 15-25)
**Goal:** Voice-first capture and conversational review.

- [ ] Integrate Deepgram Voice Agent API (WebSocket)
- [ ] Voice capture: speak → Deepgram STT → extraction pipeline
- [ ] Voice review: Pimsleur-style anticipation loop
  - AI asks question (TTS)
  - User answers (STT)
  - AI evaluates + gives feedback (TTS)
  - User rates confidence
- [ ] Function calling: memory queries during voice conversation
- [ ] Teach-me mode: chunked voice teaching with recall checks
- [ ] Barge-in handling (Deepgram built-in)

### Phase 4: Smart PA (Days 26-35)
**Goal:** Personal assistant capabilities + advanced memory techniques.

- [ ] Semantic search over all captures (pgvector)
- [ ] Voice query: "What did I learn about X?"
- [ ] Connection questions in review sessions
- [ ] Evening reflection prompt (scheduled notification)
- [ ] Mnemonic auto-generation for vocabulary/facts
- [ ] Push notification reminders for daily review

### Phase 5: Polish & Advanced (Day 36+)
**Goal:** Production quality + advanced features.

- [ ] URL/article ingestion
- [ ] Method of Loci guided walkthroughs
- [ ] Explain-back evaluation
- [ ] Analytics dashboard (retention curves, weak areas)
- [ ] Knowledge graph visualization
- [ ] Premium TTS upgrade (ElevenLabs Flash v2.5)
- [ ] Performance optimization + caching

---

## 8. Success Metrics

### 30-Day Personal Validation

| Metric | Target | How to Measure |
|---|---|---|
| **Daily review completion** | 90%+ days with review done | Streak counter |
| **Capture frequency** | 2+ captures per day average | Count in DB |
| **Retention rate** | 70%+ on items reviewed 3+ times | (Got it) / (Total reviews) |
| **Subjective recall improvement** | Notice remembering things at work that would have been forgotten | Self-assessment |
| **Review session duration** | Under 5 minutes average | Timer |

### Product-Market Fit Signals (If Expanding to Others)

| Signal | Threshold |
|---|---|
| Daily active usage | Users return 5+ days/week |
| Capture rate | 10+ captures in first week |
| Review completion | 70%+ of due reviews completed |
| 30-day retention (user) | 40%+ of signups still active at day 30 |
| NPS | 50+ |

---

## 9. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **You stop doing daily reviews** | HIGH | Fatal — entire product fails | Push notifications. Keep sessions under 5 min. Streak gamification. Make it the first thing you do with coffee. |
| **AI-generated questions are low quality** | Medium | Reviews feel useless, you stop | Flag bad question button. Weekly prompt refinement. Review question quality in first 2 weeks. |
| **You don't capture in the moment** | HIGH | Nothing to review = no improvement | Voice capture reduces friction to ~5 seconds. Make it brain-dead simple. |
| **Over-engineering before using it** | HIGH | Never ships, never used | **Hard rule: Phase 1+2 must ship in 14 days. Use daily for 1 week before touching voice.** |
| **Scope creep into "Jarvis" before core works** | HIGH | Cool demos, no retention improvement | Voice (Phase 3) only starts after Phase 2 is used daily for 7+ days. |
| **Deepgram TTS quality feels robotic** | Medium | Unpleasant to use daily | Acceptable for MVP. Swap to ElevenLabs Flash later. |
| **Voice API costs spike with heavy use** | Low | Budget concern | Monitor daily. 15 min/day = ~$8-15/month. Set alerts. |
| **FSRS scheduling feels wrong for voice content** | Low | Suboptimal intervals | FSRS is content-agnostic. Monitor and tune parameters after 2 weeks of data. |

### Where People Fail When Solving This Problem

1. **Building the tool instead of using the tool** — Spend months coding, 0 minutes reviewing. Rule: after day 14, reviews happen every day even if the product is incomplete.
2. **Making capture too complex** — Tags, categories, folders, metadata. Kill it. One text box + one sentence. That's it for MVP.
3. **Passive review** — Re-reading notes is nearly useless. The product MUST force active recall (produce the answer before seeing it).
4. **Expecting instant results** — Spaced repetition compounds over weeks. Noticeable improvement at week 3-4, not day 2. Trust the science.
5. **Not starting with real data** — Don't build with dummy data. From day 1 of Phase 2, capture what you actually learn at work.

---

## 10. What This Product IS vs ISN'T

| It IS | It ISN'T |
|---|---|
| A personal memory companion using proven cognitive science | A magic brain upgrade |
| A voice-first AI that remembers everything you tell it | A replacement for paying attention in the moment |
| A system that makes forgetting much harder | A cure for attention/focus issues |
| A second brain with active recall built in | A passive note-taking app |
| Built on decades of research (testing effect, spacing effect, elaboration) | Experimental or unproven |
| A practical tool that works in 7 minutes/day | A full-time learning management system |

---

## 11. Competitive Landscape

| Product | What They Do | What They Don't Do | Our Advantage |
|---|---|---|---|
| **Anki** | Best spaced repetition algorithm | No voice. Manual card creation. No AI. No conversation. | AI auto-generates cards. Voice-first. Conversational review. |
| **RemNote** | Notes + flashcards + SRS | No voice. Text-heavy. Passive review. | Voice-first. Active conversational recall. Memory technique orchestration. |
| **Pimsleur** | Audio graduated-interval recall | Language-only. Pre-scripted. No personalization. | Any topic. AI-personalized. Adapts to your knowledge. |
| **Pi.ai** | Empathetic conversational AI | No memory. No SRS. Ephemeral conversations. | Persistent memory. Structured recall. Proactive quizzing. |
| **Notion AI** | AI-enhanced notes | No spaced repetition. No active recall. No voice. | Full memory system, not just storage. |
| **Quizlet** | Flashcard platform | Manual creation. No voice. Basic SRS. | AI generation. Voice-first. Multiple memory techniques. |

**Positioning:** ReCall is what you'd get if Anki's algorithm + Pimsleur's audio method + a personal AI assistant had a baby. No product in the market occupies this intersection.

---

## 12. Future Expansion (If It Works for You)

### Personal → Product
If ReCall works well for personal use, the expansion path:

1. **Developer-focused version** — Capture code snippets, CLI commands, API patterns. Integrate with VS Code.
2. **Student version** — Course/textbook ingestion. Exam scheduling mode. Study group sharing.
3. **Professional version** — Meeting capture + recall. Client/project knowledge. Team knowledge base.
4. **Language learning mode** — Direct Pimsleur competitor with AI personalization.

### Monetization (Future)
| Tier | Price | Includes |
|---|---|---|
| Free | $0 | 10 captures/month. Text review only. No voice. |
| Personal | $15/month | Unlimited captures. Voice. All techniques. |
| Pro | $30/month | URL ingestion. Meeting capture. Analytics. Priority voice. |

### MCP as Distribution Channel (Phase 5)
After the core product works, expose ReCall as an **MCP server** (Model Context Protocol). This lets any AI client (Claude, ChatGPT, VS Code Copilot) discover and query your knowledge base without building separate integrations. Mount on existing FastAPI at `/mcp`. Publish on Smithery + mcp.so for free distribution to 20K+ AI clients. See [architecture-decisions.md](architecture-decisions.md) for implementation details.

### Why This Can Work as a Business
- AI infrastructure costs are dropping (GPT-4o-mini, Deepgram BYO pricing)
- Memory/learning is a universal human need, not a niche
- The habit loop (daily reviews) creates strong retention (user retention, ironically)
- Network effects via shared knowledge/study groups (future)
- No current product serves the voice-first + spaced repetition intersection
- MCP distribution puts ReCall inside every AI assistant automatically

---

## 13. Immediate Next Steps

| Step | Action | When |
|---|---|---|
| 1 | Set up Next.js + Supabase project skeleton | Day 1 |
| 2 | Create DB schema + migrations | Day 1 |
| 3 | Build capture → extract → generate pipeline | Day 2-3 |
| 4 | Build review session UI with FSRS | Day 4-7 |
| 5 | Start using daily with real work learning | Day 8 |
| 6 | Evaluate question quality + capture friction after 7 days of use | Day 14 |
| 7 | Begin voice integration (Deepgram) only after daily use is established | Day 15 |

**The single most important rule:**
> This product's value is 10% in the code and 90% in whether you actually do the daily 5-minute review. Design every decision around reducing friction to that daily habit.
