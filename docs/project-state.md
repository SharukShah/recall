# Project State: ReCall — Voice-First Personal Memory Assistant

> Last Updated: 2026-04-18
> Current Phase: Phase 2 In Progress — Knowledge Search complete, Voice + Auth + Deploy remaining
> Next Agent: Deep Dive Agent (Deepgram Voice Agent integration)

## Pipeline Status

| # | Stage | Agent | Status | Output File | Notes |
|---|-------|-------|--------|------------|-------|
| 1 | Research | Research Agent | Completed | docs/fsrs-deep-research.md, docs/llm-orchestration-research.md, docs/vector-db-rag-research.md, docs/voice-ai-infrastructure-research.md | 4 deep research docs covering FSRS, LLM orchestration, vector DB/RAG, and voice AI infra. All thorough and complete. |
| 2 | Product Vision | ProductPilot | Completed | docs/product-plan.md | Comprehensive 13-section product plan. Problem, solution, UX flows, memory techniques, architecture, feature spec, execution plan, risks. |
| 3 | Tech Stack | Tech Stack Decision Agent | Completed | docs/architecture-decisions.md | Stack locked: FastAPI + Next.js + PostgreSQL + pgvector + OpenAI (GPT-4.1-nano/mini) + py-fsrs + Deepgram (Phase 2). All decisions justified. |
| 4 | Architecture | Architecture Agent | Completed | docs/system-design.md | Full system design: component map, 5 data flows (capture, review, query, voice capture, voice review), API design, module structure, DB schema, cost estimates. |
| 5 | Decision Logic | Orchestrator Logic Agent | Completed | docs/orchestrator-logic.md | Complete decision trees for all flows: capture, review (3 endpoints), query, voice orchestrator, frontend state machines. Edge cases and error handling covered. |
| 6 | UI/UX | UI/UX Agent | Completed | docs/ui-ux-design.md | 10-section UX spec: page inventory, component hierarchy, wireframes, interaction patterns, state machines, responsive design, navigation, API map, accessibility, design tokens. |
| 7 | MVP Planning | MVP Planner Agent | Completed (Inline) | docs/product-plan.md (Section 6-7) | MVP features defined in product plan (10 MVP features, 14 post-MVP). Execution plan has 5 phases. No separate MVP doc. |
| 8 | Implementation | Coding Agent | Completed (Backend + Frontend) | backend/ (20+ files), frontend/ (50+ files) | Backend: 7 endpoints, tested & hardened. Frontend: Next.js 14, 5 pages, 30+ components, all API integrations, review state machine. Builds clean. |
| 9 | Audit | Traceability Auditor | Completed | docs/audit-report.md | Initial: 92% → fixed 3 gaps → re-audit: 100%. Then re-verified 8/8 security fixes after iteration 2. |
| 10 | Testing | Testing - Critic | Completed | docs/test-report.md | Backend: 9/10. Frontend: 7/10 → fixed 4 Medium issues → estimated 9/10. Iteration loop exited for both. |
| 11 | Iteration | Iteration Agent | Completed (2 cycles) | 12+ files changed | Cycle 1: Fixed 3 audit gaps. Cycle 2: Fixed 8 of 11 security findings (all High + Medium). 3 Low/Info deferred. |

## Key Decisions Made

* 2026-04-17 — FastAPI (Python) backend + Next.js frontend architecture selected
* 2026-04-17 — OpenAI GPT-4.1-nano for extraction/questions, GPT-4.1-mini for evaluation/queries
* 2026-04-17 — PostgreSQL + pgvector (local first, Supabase later)
* 2026-04-17 — FSRS-6 via py-fsrs for spaced repetition scheduling
* 2026-04-17 — Deepgram Voice Agent API for Phase 2 voice layer
* 2026-04-17 — No ORM — raw asyncpg + parameterized SQL queries
* 2026-04-18 — pgvector 0.8.0 installed on PostgreSQL 16 (built from source with VS Build Tools)
* 2026-04-18 — text-embedding-3-small (1536-dim) selected for embeddings
* 2026-04-18 — Pure vector search for Phase 2a, hybrid search deferred to Phase 2b
* 2026-04-18 — Embedding failure at capture time is non-fatal (NULL embedding, backfilled later)
* 2026-04-17 — Single-user MVP (no auth in Phase 1)
* 2026-04-17 — Text-first core (Phase 1), voice layer on top (Phase 2)
* 2026-04-17 — Schema simplified for MVP: no pgvector, no embeddings, no user_id
* 2026-04-18 — PostgreSQL 16 installed locally, recall_mvp database created with 4 tables
* 2026-04-18 — Custom rate limiter chosen over slowapi (integration issues with FastAPI Depends pattern)
* 2026-04-18 — Iteration loop exited: Security 9/10, 0 High/Medium issues, backend MVP complete

## Current Issues / Blockers

* ~~retention_rate missing~~ — FIXED
* ~~user_answer/ai_feedback not stored~~ — FIXED
* ~~question→fact mapping~~ — FIXED
* ~~[High] why_it_matters no max_length~~ — FIXED (max_length=1000)
* ~~[High] No transaction in capture pipeline~~ — FIXED (transaction wrapping)
* ~~[Medium] No rate limiting~~ — FIXED (custom sliding window, 10/min captures, 30/min evaluate)
* ~~[Medium] UUID validation, FSRS race condition, prompt injection, capture_id~~ — ALL FIXED
* **[Low]** `/api/reviews/rate` not rate limited (no LLM cost risk, deferred)
* **[Low]** Whitespace-only `raw_text` wastes 1 LLM call (deferred)
* **[Info]** Rate limiter dict never cleaned for inactive IPs (deferred)
* **[Info]** `openai` dependency not upper-bounded (deferred)
* Knowledge search endpoints are stubs (Phase 2 — expected)
* ~~No frontend exists yet~~ — DONE (50+ files, 5 pages, 30+ components)
* ~~UI/UX design stage was skipped~~ — DONE (docs/ui-ux-design.md)
* Need to verify ALTER TABLE on live DB for user_answer/ai_feedback columns
* CORS updated to allow both localhost:3000 and localhost:3001

## Iteration History

| # | Cycle | Auditor Score | Critical Issues | Status |
|---|-------|--------------|----------------|--------|
| 1 | Audit gaps | 92% → 100% | 0 critical, 3 low | Fixed — all 3 verified |
| 2 | Security fixes | 7/10 → 9/10 | 2 High, 5 Medium | Fixed — 8/8 fixes verified, 0 High/Medium remain |
| 3 | Re-test | 9/10 | 0 High/Medium, 3 new Low/Info | Loop exited — acceptable for MVP |

## Agent Invocation Log

| # | Date | Agent | Task | Outcome |
|---|------|-------|------|---------|
| 1 | 2026-04-14 | Research Agent | Voice AI infrastructure research | Completed — docs/voice-ai-infrastructure-research.md |
| 2 | 2026-04-17 | Research Agent | FSRS deep research | Completed — docs/fsrs-deep-research.md |
| 3 | 2026-04-17 | Research Agent | LLM orchestration research | Completed — docs/llm-orchestration-research.md |
| 4 | 2026-04-17 | Research Agent | Vector DB & RAG research | Completed — docs/vector-db-rag-research.md |
| 5 | 2026-04-17 | ProductPilot | Product plan creation | Completed — docs/product-plan.md |
| 6 | 2026-04-17 | Tech Stack Decision Agent | Architecture decisions | Completed — docs/architecture-decisions.md |
| 7 | 2026-04-17 | Architecture Agent | System design | Completed — docs/system-design.md |
| 8 | 2026-04-17 | Orchestrator Logic Agent | Decision logic blueprint | Completed — docs/orchestrator-logic.md |
| 9 | 2026-04-18 | Coding Agent | Backend skeleton setup | In Progress — main.py, config.py, db.py, schema.sql created |
| 10 | 2026-04-18 | Coding Agent | Full Phase 1 backend implementation | Completed — 20+ files: models, prompts, core modules (LLM, FSRS, DB), services (capture, review, knowledge stub), routers (captures, reviews, stats), main.py wired. Schema fixed for actual py-fsrs API. All 7 endpoints tested: capture → extract → questions works in ~4.7s, review evaluate + rate with FSRS works, dashboard stats works. |
| 11 | 2026-04-18 | Traceability Auditor | Audit backend against plan docs | Completed — 92% completeness. 7/7 MVP features, 7/7 endpoints, Capture + Review flows 100% complete. All 4 prompts match templates. py-fsrs deviations justified. 3 low-severity gaps found (retention_rate, review_log columns, question→fact mapping). 0 critical issues. |
| 12 | 2026-04-18 | Iteration Agent | Fix 3 audit gaps | Completed — 8 files changed: db_queries.py (retention_rate query + review_log insert), review_models.py (RateRequest fields), review_service.py (pass-through), schema.sql (columns), capture_models.py (fact_index), question_generation.txt (fact_index instruction), capture_service.py (fact_index lookup). All tested: retention_rate returns, user_answer stored, questions mapped to 4 different facts. |
| 13 | 2026-04-18 | Traceability Auditor | Re-audit after fixes | Completed — 100% completeness. All 3 fixes verified: retention_rate correct with NULL handling, user_answer/ai_feedback fully wired, fact_index with bounds checking. 0 regressions, 0 new issues. Ready for Testing-Critic. |
| 14 | 2026-04-18 | Testing - Critic | Security & stress testing | Completed — 11 findings (2 High, 5 Med, 3 Low, 1 Info). Security score 7/10. |
| 15 | 2026-04-18 | Iteration Agent | Fix 8 security findings | Completed — Fixed all High + Medium: why_it_matters max_length, transaction wrapping, UUID validators, SELECT FOR UPDATE, rate limiting (custom sliding window), prompt injection boundaries, capture_id validation, RateRequest field limits. |
| 16 | 2026-04-18 | Traceability Auditor | Verify 8 security fixes | Completed — 8/8 fixes verified correct. |
| 17 | 2026-04-18 | Testing - Critic | Re-test after security fixes | Completed — Score 9/10. 0 High/Medium remaining. 3 new Low/Info found. Iteration loop exit approved. |
| 18 | 2026-04-18 | UI/UX Agent | Frontend UI/UX design | Completed — docs/ui-ux-design.md. 10 sections: pages, components, wireframes, interactions, state, responsive, nav, API map, accessibility, design tokens. |
| 19 | 2026-04-18 | Coding Agent | Build full frontend | Completed — frontend/ with Next.js 14, 50+ files, all 5 pages, 30+ components, review state machine, API client, design tokens. Builds clean (0 errors). |
| 20 | 2026-04-18 | Traceability Auditor | Audit frontend vs UX spec | Completed — 93% completeness. 4 polish-level gaps (focus management, animations, confirmation dialog, keyboard shortcut). All core functionality present. |
| 21 | 2026-04-18 | Iteration Agent | Fix 4 frontend polish gaps | Completed — All 4 gaps fixed: focus management (5 transitions), CSS animations (crossfade/slide), End Session confirmation dialog, Escape/Backspace in history detail. Build clean. |
| 22 | 2026-04-18 | Testing - Critic | Frontend security audit | Completed — 4 Medium (path traversal, no security headers, double-click race, CSR layout), 8 Low, 3 Info. Score 7/10. |
| 23 | 2026-04-18 | Iteration Agent | Fix 4 frontend security issues | Completed — F1: encodeURIComponent on capture ID. F2: security headers in next.config.js. F3: isSubmitting ref guard on rating/evaluate. F4: server component layout + AppShell client wrapper. Build clean. |

## Skipped Stages

* ~~**UI/UX**~~ — No longer skipped. Completed by UI/UX Agent → docs/ui-ux-design.md
