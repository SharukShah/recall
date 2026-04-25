# Phase 5: Polish & Advanced Features — System Architecture
**Version:** 1.0  
**Date:** April 18, 2026  
**Status:** Ready to implement  
**Depends on:** Phases 1-4 complete (text capture, review engine, voice layer, smart PA features)

---

## Overview

Ten features that bring ReCall to production quality: five product features (Method of Loci, push notifications, knowledge graph visualization, analytics dashboard, browser extension) and five infrastructure features (authentication, PWA setup, Docker deployment, error monitoring, performance & caching).

**Design principles:**
- Reuse existing patterns: service classes with `db_pool`/`openai` from `app.state`, `core/llm.py` for all LLM calls, `core/db_queries.py` for all SQL
- GPT-4.1-nano for generation tasks, GPT-4.1-mini for evaluation tasks
- No new databases — everything in PostgreSQL (including caching)
- All endpoints under `/api/` prefix
- Auth is middleware-based, not per-endpoint
- Docker setup works for development AND production
- Browser extension in separate `extension/` directory at project root
- PWA service worker goes in `frontend/public/`

---

## Table of Contents

1. [Authentication](#1-authentication)
2. [PWA Setup](#2-pwa-setup)
3. [Push Notifications](#3-push-notifications)
4. [Method of Loci](#4-method-of-loci)
5. [Knowledge Graph Visualization](#5-knowledge-graph-visualization)
6. [Analytics Dashboard](#6-analytics-dashboard)
7. [Browser Extension](#7-browser-extension)
8. [Deployment (Docker Compose)](#8-deployment-docker-compose)
9. [Error Monitoring (Sentry)](#9-error-monitoring-sentry)
10. [Performance & Caching](#10-performance--caching)
11. [Schema Migration SQL](#schema-migration-sql)
12. [New Files to Create](#new-files-to-create)
13. [Integration Points](#integration-points)
14. [Key Architecture Decisions](#key-architecture-decisions)

---

## 1. Authentication

### What It Does
Simple API-key-based authentication protecting the deployed instance. A pre-configured secret token is checked on every request via FastAPI middleware. No registration, no user management — single-user MVP. The frontend stores the token in `localStorage` and sends it as a `Bearer` token in the `Authorization` header.

### API Endpoints

| Method | Path | Purpose | Auth Required |
|---|---|---|---|
| `POST` | `/api/auth/verify` | Verify token validity, return status | No (checks the token itself) |
| `GET` | `/api/auth/status` | Check if auth is enabled | No |

All other existing endpoints become protected automatically via middleware.

#### Request/Response Models

```python
class AuthVerifyRequest(BaseModel):
    token: str = Field(..., min_length=1, max_length=500)

class AuthVerifyResponse(BaseModel):
    valid: bool
    message: str

class AuthStatusResponse(BaseModel):
    auth_enabled: bool
```

### Data Flow

```
Every HTTP request to /api/* (except /api/auth/*)
│
├─ 1. Middleware: AuthMiddleware intercepts request
│
├─ 2. Check if AUTH_SECRET_KEY is configured in settings
│     ├─ IF not set or empty → skip auth (dev mode, backward compatible)
│     └─ IF set → continue auth check
│
├─ 3. Extract token from Authorization header
│     ├─ Format: "Bearer <token>"
│     ├─ IF missing → return 401 { error: "Missing authorization header" }
│     └─ IF malformed → return 401 { error: "Invalid authorization format" }
│
├─ 4. Compare token to AUTH_SECRET_KEY using constant-time comparison
│     ├─ IF match → allow request to proceed
│     └─ IF no match → return 401 { error: "Invalid token" }
│
└─ Request proceeds to router normally

POST /api/auth/verify { token: "..." }
│
├─ 1. Compare token to AUTH_SECRET_KEY (constant-time)
│
└─ Response: { valid: true/false, message: "..." }
```

### Database Changes

None. Auth token is stored as an environment variable, not in the database.

### Frontend Components

- **New page:** `app/login/page.tsx` — Token input form. Shows if auth is enabled and no token in localStorage. Simple input field + "Enter" button.
- **New component:** `components/auth/LoginForm.tsx` — Token input, submit, error display
- **Modify `lib/api.ts`** — Add `Authorization: Bearer <token>` header to every request. Read token from `localStorage`.
- **Modify `AppShell.tsx`** — On 401 response, redirect to `/login` and clear localStorage token.

### New Files to Create

```
backend/
├── core/
│   └── auth.py               # AuthMiddleware class, verify_token(), constant-time compare
└── routers/
    └── auth.py                # POST /verify, GET /status

frontend/
├── app/
│   └── login/
│       └── page.tsx           # Login page
└── components/
    └── auth/
        └── LoginForm.tsx      # Token input form
```

### Files to Modify

| File | Change |
|---|---|
| `backend/config.py` | Add `AUTH_SECRET_KEY: str = ""` setting |
| `backend/main.py` | Add `AuthMiddleware` before CORS middleware, mount `auth.router` |
| `frontend/lib/api.ts` | Add auth token to `request()` headers, handle 401 redirect |
| `frontend/components/layout/AppShell.tsx` | Wrap children in auth check, redirect on 401 |

### Dependencies

None — uses `hmac.compare_digest` from Python stdlib.

### Decision Logic

- **Constant-time comparison:** Use `hmac.compare_digest()` to prevent timing attacks on token comparison.
- **Backward compatible:** If `AUTH_SECRET_KEY` is empty/unset, auth is disabled. Existing dev setups work unchanged.
- **No JWT complexity:** Single-user app doesn't need JWT tokens, refresh flows, or user tables. A shared secret is simpler and sufficient.
- **WebSocket auth:** The `/ws/voice-agent` WebSocket endpoint checks the token from query params (`?token=...`) since WebSocket headers are limited in browsers.
- **Excluded paths:** `GET /` (health check), `/api/auth/*`, and `/docs` (Swagger) are excluded from auth.
- **Token storage:** Frontend stores token in `localStorage`. Acceptable for single-user self-hosted — no XSS risk from other users.
- **Error: No token on first visit** → Redirect to `/login`. After entering token, verify via `/api/auth/verify`, store in localStorage, redirect to dashboard.
- **Alternative rejected: Session cookies** — More complex, requires CSRF protection, doesn't work well for the browser extension.
- **Alternative rejected: OAuth/OIDC** — Massive overkill for single-user. Adds external dependencies and complexity.

---

## 2. PWA Setup

### What It Does
Progressive Web App configuration: `manifest.json`, service worker for offline review caching, installable on mobile. The service worker caches the review UI shell and question data so users can review even without connectivity. Answers are queued in IndexedDB and synced when back online.

### API Endpoints

No new backend endpoints. PWA is a frontend-only feature.

### Data Flow

```
Service Worker Registration:
│
├─ 1. next.config.js registers /sw.js from public/
│
├─ 2. On install: cache app shell (HTML, CSS, JS bundles, icons)
│
└─ 3. On activate: clean old caches

Offline Review Flow:
│
├─ 1. When user opens /review (online):
│     ├─ Fetch due questions from GET /api/reviews/due
│     ├─ Cache response in IndexedDB (idb-keyval or raw IndexedDB)
│     └─ Render normally
│
├─ 2. When user opens /review (offline):
│     ├─ Service worker intercepts fetch to /api/reviews/due
│     ├─ Returns cached questions from IndexedDB
│     └─ User can see questions and type answers
│
├─ 3. When user submits answer/rating (offline):
│     ├─ Store in IndexedDB outbox queue:
│     │   { type: "evaluate"|"rate", payload: {...}, timestamp }
│     ├─ Show optimistic UI: "Saved offline. Will sync when connected."
│     └─ Register background sync event
│
├─ 4. When connectivity returns:
│     ├─ Service worker "sync" event fires
│     ├─ Drain outbox queue: replay POSTs in order
│     ├─ On success: remove from queue, update cached data
│     └─ On failure: keep in queue, retry next sync
│
└─ Manifest enables "Add to Home Screen" prompt
```

### Database Changes

None. Offline data is stored in the browser's IndexedDB.

### Frontend Components

- **New file:** `frontend/public/manifest.json` — PWA manifest with app name, icons, theme color, display: standalone
- **New file:** `frontend/public/sw.js` — Service worker: cache app shell, intercept API calls when offline, background sync
- **New file:** `frontend/lib/offline-store.ts` — IndexedDB wrapper for caching questions and queuing offline actions
- **New icons:** `frontend/public/icon-192.png`, `frontend/public/icon-512.png` — PWA icons
- **Modify `frontend/app/layout.tsx`** — Add `<link rel="manifest">`, meta tags for PWA, register service worker

### New Files to Create

```
frontend/
├── public/
│   ├── manifest.json          # PWA manifest
│   ├── sw.js                  # Service worker
│   ├── icon-192.png           # PWA icon 192x192
│   └── icon-512.png           # PWA icon 512x512
└── lib/
    └── offline-store.ts       # IndexedDB: cache questions, queue offline actions
```

### Files to Modify

| File | Change |
|---|---|
| `frontend/app/layout.tsx` | Add manifest link, theme-color meta, service worker registration script |
| `frontend/next.config.js` | Add service worker headers (Service-Worker-Allowed: /) |
| `frontend/hooks/useReviewSession.ts` | Use offline-store for caching questions and queuing ratings when offline |

### Dependencies

None. Service worker API and IndexedDB are browser-native. No npm packages needed.

### Decision Logic

- **No next-pwa:** Next.js PWA plugins add complexity and magic. A hand-written service worker is simpler, more controllable, and under 100 lines.
- **Cache strategy:** Network-first for API calls (try network, fall back to cache). Cache-first for static assets (JS/CSS/images).
- **Offline scope:** Only the review flow works offline. Capture requires LLM calls (can't work offline). Search requires backend. Dashboard shows stale data with a "Last updated" badge.
- **Background sync:** Uses the Background Sync API where supported. Falls back to retry-on-focus for browsers that don't support it.
- **IndexedDB over localStorage:** localStorage is synchronous and limited to ~5MB. IndexedDB is async and can store structured data (cached question objects).
- **Sync conflict resolution:** Offline ratings are applied in chronological order. If the same question was rated online by another client (unlikely for single-user), the last-write-wins.
- **Error: Service worker fails to register** → App works normally without offline support. Non-fatal.
- **Error: IndexedDB unavailable (private browsing)** → Fall back to in-memory cache for the session. No offline persistence.

---

## 3. Push Notifications

### What It Does
Daily push notification: "You have N items to review." Sent via Web Push API through the PWA service worker. User configures notification time (default 9 AM). Backend checks reviews due count and only sends if > 0. Requires PWA service worker (Feature 2) to be installed.

### API Endpoints

| Method | Path | Purpose | Auth |
|---|---|---|---|
| `POST` | `/api/notifications/subscribe` | Store push subscription from browser | Yes |
| `DELETE` | `/api/notifications/subscribe` | Remove push subscription | Yes |
| `GET` | `/api/notifications/settings` | Get notification preferences | Yes |
| `PUT` | `/api/notifications/settings` | Update notification preferences | Yes |
| `POST` | `/api/notifications/test` | Send a test notification immediately | Yes |

#### Request/Response Models

```python
class PushSubscription(BaseModel):
    endpoint: str = Field(..., max_length=2000)
    keys: dict  # { p256dh: str, auth: str }

class NotificationSettings(BaseModel):
    enabled: bool = True
    review_reminder_time: str = "09:00"  # HH:MM in user's local time
    timezone: str = "UTC"

class NotificationSettingsResponse(BaseModel):
    enabled: bool
    review_reminder_time: str
    timezone: str
    subscription_active: bool
```

### Data Flow

```
Browser subscribes to push:
│
├─ 1. Frontend requests notification permission
│     └─ IF denied → show message, cannot enable
│
├─ 2. Service worker subscribes to push manager
│     ├─ Uses VAPID public key from backend
│     └─ Returns PushSubscription object
│
├─ 3. Frontend sends POST /api/notifications/subscribe
│     { endpoint, keys: { p256dh, auth } }
│
└─ 4. Backend stores subscription in notification_subscriptions table

Scheduled notification (cron-like):
│
├─ 1. Background task runs every minute (asyncio task in lifespan)
│
├─ 2. Check notification_settings: is it notification time for any subscription?
│     ├─ Convert configured HH:MM + timezone to UTC
│     ├─ IF current UTC minute matches → trigger
│     └─ IF already sent today → skip (check last_sent_at)
│
├─ 3. Query: SELECT COUNT(*) FROM questions WHERE due <= NOW()
│     ├─ IF 0 → skip notification
│     └─ IF > 0 → send
│
├─ 4. Send Web Push notification via pywebpush
│     ├─ Payload: { title: "ReCall", body: "You have 8 items to review", url: "/review" }
│     ├─ Sign with VAPID private key
│     └─ POST to subscription endpoint
│
├─ 5. Update last_sent_at in notification_settings
│
└─ 6. IF push fails (410 Gone = unsubscribed) → delete subscription
```

### Database Changes

```sql
-- Push notification subscriptions
CREATE TABLE IF NOT EXISTS notification_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    endpoint TEXT NOT NULL UNIQUE,
    p256dh_key TEXT NOT NULL,
    auth_key TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Notification settings (single row for single-user)
CREATE TABLE IF NOT EXISTS notification_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    enabled BOOLEAN NOT NULL DEFAULT true,
    review_reminder_time TEXT NOT NULL DEFAULT '09:00',  -- HH:MM
    timezone TEXT NOT NULL DEFAULT 'UTC',
    last_sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### New Files to Create

```
backend/
├── routers/
│   └── notifications.py       # Subscribe, settings, test endpoints
├── services/
│   └── notification_service.py # NotificationService: subscribe, send_push, check_and_send
├── models/
│   └── notification_models.py  # PushSubscription, NotificationSettings
└── core/
    └── push.py                # VAPID key management, pywebpush wrapper

frontend/
├── components/
│   └── settings/
│       └── NotificationSettings.tsx  # Toggle, time picker, test button
├── hooks/
│   └── useNotifications.ts    # Push permission, subscription management
└── lib/
    └── push.ts                # Subscribe/unsubscribe to push, get VAPID key
```

### Files to Modify

| File | Change |
|---|---|
| `backend/config.py` | Add `VAPID_PRIVATE_KEY`, `VAPID_PUBLIC_KEY`, `VAPID_EMAIL` settings |
| `backend/main.py` | Mount `notifications.router`, start background notification task in lifespan |
| `frontend/public/sw.js` | Add `push` and `notificationclick` event handlers |
| `frontend/components/layout/DesktopSidebar.tsx` | Add "Settings" nav link (for notification settings) |
| `frontend/lib/api.ts` | Add notification API functions |
| `frontend/types/api.ts` | Add notification types |

### Dependencies

| Package | Purpose |
|---|---|
| `pywebpush>=2.0.0` (pip) | Send Web Push notifications with VAPID |
| `py-vapid>=1.9.0` (pip) | Generate and manage VAPID keys |

### Frontend Components

- **New page:** `app/settings/page.tsx` — Notification settings (and future settings)
- **New component:** `components/settings/NotificationSettings.tsx` — Toggle enable/disable, time picker for reminder time, timezone selector, "Send test" button
- **Nav integration:** Add "Settings" link to `DesktopSidebar.tsx` and `MobileTabBar.tsx` (Settings icon)

### Decision Logic

- **VAPID keys:** Generated once, stored as environment variables. Backend exposes public key via `/api/notifications/settings` for the frontend to use during subscription.
- **Cron approach:** A simple `asyncio` background task started in the FastAPI lifespan, checking every 60 seconds. No need for Celery, APScheduler, or external cron.
- **Timezone handling:** User sets their timezone in notification settings. Server converts configured HH:MM to UTC for comparison.
- **Deduplication:** `last_sent_at` column prevents sending multiple notifications per day.
- **Subscription cleanup:** When a push fails with HTTP 410 (Gone), the subscription is deleted — the user unsubscribed via browser settings.
- **Multiple devices:** Multiple subscriptions allowed (one per device/browser). Notification sent to all active subscriptions.
- **Error: Push delivery failure** → Log warning, don't retry for this cycle. Next day will try again.
- **Alternative rejected: Firebase Cloud Messaging** — Adds Google dependency. Web Push API is standard and works directly with VAPID.
- **Alternative rejected: Email notifications** — Requires SMTP setup, email address collection. Push is simpler for a PWA.

---

## 4. Method of Loci

### What It Does
Guided audio "memory palace" walkthrough. User provides a list of items to memorize → AI creates a virtual journey placing items at familiar locations → TTS narrates the walkthrough → user listens, then tries to recall items by mentally walking the route. Works for ordered lists, sequences, procedures.

### API Endpoints

| Method | Path | Purpose | LLM Model |
|---|---|---|---|
| `POST` | `/api/loci/create` | Generate a memory palace walkthrough | GPT-4.1-nano |
| `GET` | `/api/loci/{session_id}` | Get walkthrough details | None |
| `POST` | `/api/loci/{session_id}/recall` | Submit recall attempt, get evaluation | GPT-4.1-mini |
| `GET` | `/api/loci` | List past loci sessions | None |

#### Request/Response Models

```python
class LociCreateRequest(BaseModel):
    items: list[str] = Field(..., min_length=3, max_length=20)
    title: str = Field(..., min_length=1, max_length=200)
    palace_theme: str | None = Field(default=None, max_length=200)
    # e.g., "my apartment", "a library", "a garden path"
    # If None, AI picks a theme

class LociLocation(BaseModel):
    position: int           # 1-based
    location_name: str      # e.g., "the front door"
    item: str               # The item placed here
    vivid_image: str        # e.g., "A giant TCP handshake is blocking the door..."
    narration: str          # TTS-ready narration for this stop

class LociWalkthrough(BaseModel):
    palace_theme: str       # e.g., "Your apartment"
    introduction: str       # Opening narration
    locations: list[LociLocation]
    conclusion: str         # Closing narration

class LociCreateResponse(BaseModel):
    session_id: str
    title: str
    palace_theme: str
    total_locations: int
    walkthrough: LociWalkthrough
    full_narration: str     # Complete TTS-ready text (intro + all locations + conclusion)
    capture_id: str | None  # Auto-created capture for FSRS scheduling

class LociRecallRequest(BaseModel):
    recalled_items: list[str]  # User's recall attempt (ordered)

class LociRecallResponse(BaseModel):
    score: int              # Items correctly recalled (position-sensitive)
    total: int              # Total items
    feedback: str           # AI feedback on recall performance
    correct_order: list[str]  # The actual order for comparison
    details: list[LociRecallDetail]

class LociRecallDetail(BaseModel):
    position: int
    expected: str
    recalled: str | None
    correct: bool
    location_hint: str      # "At the front door..."

class LociListItem(BaseModel):
    session_id: str
    title: str
    palace_theme: str
    total_locations: int
    last_recall_score: int | None
    created_at: str
```

### Data Flow

```
POST /api/loci/create { items: ["item1", "item2", ...], title: "...", palace_theme: "my apartment" }
│
├─ 1. LLM: Generate memory palace walkthrough (GPT-4.1-nano)
│     Input: items list, palace_theme (or "choose a familiar setting")
│     Output: LociWalkthrough structured output
│     The LLM creates vivid, bizarre, exaggerated mental images for each item
│     placed at a specific location in the palace
│
├─ 2. Concatenate all narration into full_narration string
│     intro + location1_narration + location2_narration + ... + conclusion
│
├─ 3. Auto-capture: Create capture with items as raw_text
│     source_type = "loci"
│     → Generates FSRS-scheduled review questions about the items
│
├─ 4. Store session in loci_sessions table
│     walkthrough_json = full LociWalkthrough
│
├─ 5. Return walkthrough + full_narration
│     Frontend can use existing POST /api/voice/tts to convert narration to audio
│
└─ Response: { session_id, walkthrough, full_narration, capture_id }

POST /api/loci/{session_id}/recall { recalled_items: ["item2", "item1", ...] }
│
├─ 1. Fetch session from DB
│
├─ 2. Compare recalled_items against original items (position-sensitive)
│     ├─ Exact position match → correct
│     ├─ Item present but wrong position → noted in details
│     └─ Missing items → noted
│
├─ 3. LLM: Generate recall feedback (GPT-4.1-mini)
│     Input: original items + positions, recalled items, correct/incorrect
│     Output: Encouraging feedback + suggestions for improving recall
│
├─ 4. Update last_recall_score in DB
│
└─ Response: { score, total, feedback, correct_order, details }
```

### Database Changes

```sql
CREATE TABLE IF NOT EXISTS loci_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    items JSONB NOT NULL,               -- Original items list
    palace_theme TEXT NOT NULL,
    walkthrough_json JSONB NOT NULL,     -- Full LociWalkthrough
    full_narration TEXT NOT NULL,        -- TTS-ready narration
    capture_id UUID REFERENCES captures(id),
    last_recall_score INT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_loci_sessions_created ON loci_sessions (created_at DESC);
```

### LLM Prompts

1. **`loci_walkthrough_generation.txt`** — System prompt for GPT-4.1-nano. Instructions: You are creating a Method of Loci (memory palace) walkthrough. Given a list of items to memorize and a location theme, create a guided mental journey. For each item, place it at a distinct location in the palace. Create a VIVID, BIZARRE, EXAGGERATED mental image linking the item to the location — the more unusual, the more memorable. Use sensory details (sight, sound, smell, touch). The narration should be in second person ("You walk through the door and see..."). Keep each location narration to 2-3 sentences. The introduction sets the scene, the conclusion reinforces the journey path.

2. **`loci_recall_evaluation.txt`** — System prompt for GPT-4.1-mini. Instructions: Evaluate a user's recall attempt of items from a memory palace. They were given items placed at specific locations. Compare their recalled order to the correct order. Give encouraging, specific feedback. If they missed items, suggest revisiting the mental image at that location. If they got the order wrong, note which locations they may have mixed up.

### New Files to Create

```
backend/
├── routers/
│   └── loci.py                # POST /create, GET /{id}, POST /{id}/recall, GET /
├── services/
│   └── loci_service.py        # LociService: create(), get(), recall(), list()
├── models/
│   └── loci_models.py         # All Loci request/response/LLM models
└── prompts/
    ├── loci_walkthrough_generation.txt
    └── loci_recall_evaluation.txt
```

### Files to Modify

| File | Change |
|---|---|
| `backend/main.py` | Mount `loci.router` at `/api/loci` |
| `backend/core/llm.py` | Add `generate_loci_walkthrough()` and `evaluate_loci_recall()` |
| `backend/core/db_queries.py` | Add loci session CRUD queries |
| `frontend/lib/api.ts` | Add loci API functions |
| `frontend/types/api.ts` | Add loci types |
| `frontend/components/layout/DesktopSidebar.tsx` | Add "Memory Palace" nav link |

### Frontend Components

- **New page:** `app/loci/page.tsx` — List past palaces, "Create new" button
- **New page:** `app/loci/create/page.tsx` — Items input form (add/remove items), title, optional palace theme
- **New component:** `components/loci/LociItemList.tsx` — Dynamic list of text inputs for items
- **New component:** `components/loci/WalkthroughPlayer.tsx` — Displays narration text, "Play Audio" button (uses existing TTS endpoint), location-by-location progress
- **New component:** `components/loci/RecallTest.tsx` — Ordered text inputs for recall attempt, submit + results
- **New component:** `components/loci/RecallResults.tsx` — Score display, per-item correct/incorrect, AI feedback

### Decision Logic

- **Item count:** Min 3, max 20. Fewer than 3 isn't worth a palace. More than 20 exceeds working memory limits for a single walkthrough.
- **Palace theme:** If not provided, LLM picks a common familiar setting (apartment, school, park). If provided, LLM uses it.
- **Audio delivery:** The `full_narration` string can be sent to the existing `POST /api/voice/tts` endpoint chunk by chunk. Frontend controls playback.
- **Auto-capture:** Items are captured through the standard pipeline so they enter FSRS review scheduling. The `source_type = "loci"` differentiates them in history.
- **Recall scoring:** Position-sensitive. Item "TCP" at position 3 is only correct if it was originally at position 3. Fuzzy matching on item text (case-insensitive, stripped whitespace).
- **Error: LLM fails on walkthrough** → Return 500 "Failed to generate memory palace. Try different items."
- **Error: LLM fails on recall evaluation** → Use algorithmic scoring only, skip AI feedback.
- **Alternative rejected: Pre-built palace templates** — Too rigid. LLM-generated palaces adapt to any content. The bizarre/exaggerated images are the key memory mechanism.

---

## 5. Knowledge Graph Visualization

### What It Does
Interactive graph showing how captured concepts connect. Nodes are `extracted_points`, edges are either semantic similarity (embedding cosine > 0.7) or explicit connections from `connection_questions`. Users can click nodes to see details, zoom/pan, and filter by topic. Uses a client-side graph library for rendering.

### API Endpoints

| Method | Path | Purpose | Auth |
|---|---|---|---|
| `GET` | `/api/knowledge/graph` | Get graph data (nodes + edges) | Yes |
| `GET` | `/api/knowledge/graph/node/{point_id}` | Get detailed info for a node | Yes |

#### Request/Response Models

```python
class GraphNode(BaseModel):
    id: str
    label: str              # First 60 chars of content
    content: str            # Full content
    content_type: str       # fact, concept, etc.
    capture_id: str
    created_at: str
    cluster: str | None     # Topic cluster label (from capture topic)

class GraphEdge(BaseModel):
    source: str             # point_id
    target: str             # point_id
    weight: float           # Similarity score or 1.0 for explicit connections
    edge_type: str          # "similarity" | "connection"

class GraphDataResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    stats: GraphStats

class GraphStats(BaseModel):
    total_nodes: int
    total_edges: int
    total_clusters: int

class NodeDetailResponse(BaseModel):
    id: str
    content: str
    content_type: str
    mnemonic_hint: str | None
    capture_raw_text: str
    capture_source_type: str
    capture_created_at: str
    questions: list[NodeQuestion]
    connected_nodes: list[ConnectedNode]

class NodeQuestion(BaseModel):
    question_text: str
    question_type: str
    state: int
    due: str

class ConnectedNode(BaseModel):
    id: str
    content: str
    similarity: float
```

### Data Flow

```
GET /api/knowledge/graph?min_similarity=0.7&limit=200
│
├─ 1. Fetch all extracted_points with embeddings (up to limit)
│     SELECT id, content, content_type, capture_id, created_at
│     FROM extracted_points WHERE embedding IS NOT NULL
│     ORDER BY created_at DESC LIMIT 200
│
├─ 2. Compute similarity edges using pgvector
│     For each pair of points in the result set, compute cosine similarity
│     WHERE similarity >= min_similarity AND source != target
│     (Optimized: use a single SQL query with self-join)
│
├─ 3. Add explicit connection edges from connection_questions table
│     SELECT point_a_id, point_b_id FROM connection_questions
│
├─ 4. Derive cluster labels from capture topics
│     JOIN with captures → use capture's extracted topic as cluster
│
├─ 5. Return { nodes, edges, stats }
│
└─ Response: GraphDataResponse

GET /api/knowledge/graph/node/{point_id}
│
├─ 1. Fetch point details + capture info
│
├─ 2. Fetch questions linked to this point
│
├─ 3. Fetch connected nodes (top 5 by similarity)
│
└─ Response: NodeDetailResponse
```

### Database Changes

No new tables. The graph is computed from existing `extracted_points`, `connection_questions`, and embeddings. Add one index for performance:

```sql
-- Index for self-join similarity computation
CREATE INDEX IF NOT EXISTS idx_extracted_points_embedding_not_null
    ON extracted_points (id) WHERE embedding IS NOT NULL;
```

### New Files to Create

```
backend/
├── routers/
│   └── graph.py               # GET /graph, GET /graph/node/{id}
├── services/
│   └── graph_service.py       # GraphService: get_graph_data(), get_node_detail()
└── models/
    └── graph_models.py        # GraphNode, GraphEdge, GraphDataResponse, etc.

frontend/
├── app/
│   └── graph/
│       └── page.tsx           # Knowledge graph page
├── components/
│   └── graph/
│       ├── KnowledgeGraph.tsx  # Main graph canvas component
│       ├── GraphControls.tsx   # Zoom, filter, layout controls
│       └── NodeDetail.tsx      # Side panel showing clicked node details
└── hooks/
    └── useKnowledgeGraph.ts   # Fetch graph data, manage selection state
```

### Files to Modify

| File | Change |
|---|---|
| `backend/main.py` | Mount `graph.router` at `/api/knowledge` |
| `backend/core/db_queries.py` | Add `get_graph_nodes()`, `get_graph_edges()`, `get_node_detail()` |
| `frontend/lib/api.ts` | Add `fetchGraphData()`, `fetchNodeDetail()` |
| `frontend/types/api.ts` | Add graph types |
| `frontend/components/layout/DesktopSidebar.tsx` | Add "Graph" nav link |

### Dependencies

| Package | Purpose |
|---|---|
| `@react-sigma/core` (npm) | React wrapper for Sigma.js graph rendering |
| `graphology` (npm) | In-memory graph data structure |
| `graphology-layout-forceatlas2` (npm) | Force-directed layout algorithm |

### Frontend Components

- **New page:** `app/graph/page.tsx` — Full-width graph canvas with controls
- **New component:** `components/graph/KnowledgeGraph.tsx` — Sigma.js canvas, renders nodes (colored by cluster) and edges (weighted by similarity), handles click/hover events
- **New component:** `components/graph/GraphControls.tsx` — Zoom in/out, reset view, filter by cluster, min similarity slider
- **New component:** `components/graph/NodeDetail.tsx` — Side panel (slides in from right) showing full content, related questions, connected nodes when a node is clicked

### Decision Logic

- **Node limit:** Default 200 nodes max. Beyond this, the graph becomes visually unusable. User can filter by cluster/date to focus on subsets.
- **Edge computation:** The similarity self-join is O(n²) but with limit=200 and pgvector's optimized cosine, it runs in <500ms.
- **Clustering:** Use the `topic` field from the parent capture's `ExtractedFacts`. This provides natural grouping without additional computation.
- **Node colors:** Each cluster gets a distinct color from a predefined palette. Orphan nodes (no edges) are gray.
- **Edge thickness:** Proportional to similarity score. Thicker = more related.
- **Alternative rejected: D3.js force graph** — More flexible but harder to render 200+ nodes performantly. Sigma.js uses WebGL and handles large graphs well.
- **Alternative rejected: Server-side graph layout** — Layout computation is CPU-intensive. Client-side ForceAtlas2 is fast and interactive.
- **Alternative rejected: Neo4j** — Separate database for a graph view. PostgreSQL can compute the necessary similarity edges. No new infrastructure.
- **Error: No embeddings in DB** → Show empty state: "Capture some knowledge first! The graph will appear after you have 5+ items."
- **Error: Graph render fails** → Fallback to a simple list view of extracted points grouped by capture.

---

## 6. Analytics Dashboard

### What It Does
Deep analytics beyond the basic dashboard stats: retention curves over time (are you improving?), weak areas (which topics decay fastest?), learning velocity (items captured/reviewed per week), review consistency (streak data), mastery distribution (how many items in each FSRS state), and daily/weekly review performance breakdown.

### API Endpoints

| Method | Path | Purpose | Auth |
|---|---|---|---|
| `GET` | `/api/stats/analytics` | Full analytics data | Yes |
| `GET` | `/api/stats/retention-curve` | Retention rate over time (weekly buckets) | Yes |
| `GET` | `/api/stats/weak-areas` | Topics with lowest retention | Yes |
| `GET` | `/api/stats/activity` | Daily capture/review counts for heatmap | Yes |

#### Request/Response Models

```python
class AnalyticsResponse(BaseModel):
    mastery_distribution: MasteryDistribution
    learning_velocity: LearningVelocity
    review_consistency: ReviewConsistency
    summary: AnalyticsSummary

class MasteryDistribution(BaseModel):
    new: int                # state = 0
    learning: int           # state = 1
    review: int             # state = 2 (mastered)
    relearning: int         # state = 3

class LearningVelocity(BaseModel):
    captures_this_week: int
    captures_last_week: int
    reviews_this_week: int
    reviews_last_week: int
    questions_generated_this_week: int

class ReviewConsistency(BaseModel):
    current_streak: int
    longest_streak: int
    review_days_last_30: int     # Days with at least one review in last 30
    avg_reviews_per_day: float   # Over last 30 days

class AnalyticsSummary(BaseModel):
    total_reviews_all_time: int
    avg_score: float | None      # Average rating (1-4) over all reviews
    total_time_studying_estimate_minutes: int  # reviews * ~30s each

class RetentionCurvePoint(BaseModel):
    week_start: str              # ISO date
    retention_rate: float        # % of reviews rated ≥3
    total_reviews: int

class RetentionCurveResponse(BaseModel):
    data_points: list[RetentionCurvePoint]

class WeakArea(BaseModel):
    topic: str
    capture_id: str
    total_reviews: int
    retention_rate: float        # % rated ≥3
    avg_rating: float
    lapsed_count: int            # Times rated "Again"

class WeakAreasResponse(BaseModel):
    weak_areas: list[WeakArea]   # Sorted by retention_rate ascending

class ActivityDay(BaseModel):
    date: str                    # ISO date
    captures: int
    reviews: int

class ActivityResponse(BaseModel):
    days: list[ActivityDay]      # Last 90 days
```

### Data Flow

```
GET /api/stats/analytics
│
├─ 1. Mastery distribution:
│     SELECT state, COUNT(*) FROM questions GROUP BY state
│
├─ 2. Learning velocity:
│     COUNT captures/reviews/questions created this week vs last week
│
├─ 3. Review consistency:
│     ├─ Current streak (existing logic from dashboard stats)
│     ├─ Longest streak: max consecutive days with reviews
│     ├─ Review days last 30: COUNT DISTINCT review dates
│     └─ Avg reviews/day: total reviews last 30 / 30
│
├─ 4. Summary: aggregate counts + averages
│
└─ Response: AnalyticsResponse

GET /api/stats/retention-curve?weeks=12
│
├─ 1. Bucket review_logs by ISO week
│
├─ 2. For each week: retention = COUNT(rating >= 3) / COUNT(*)
│
└─ Response: { data_points: [{ week_start, retention_rate, total_reviews }] }

GET /api/stats/weak-areas?limit=10
│
├─ 1. Join review_logs → questions → extracted_points → captures
│
├─ 2. Group by capture (topic)
│
├─ 3. Calculate retention rate and lapsed count per topic
│
├─ 4. Sort by retention_rate ascending (weakest first)
│
└─ Response: { weak_areas: [...] }

GET /api/stats/activity?days=90
│
├─ 1. Generate date series for last N days
│
├─ 2. LEFT JOIN with captures (COUNT per day) and review_logs (COUNT per day)
│
└─ Response: { days: [{ date, captures, reviews }] }
```

### Database Changes

No new tables. All analytics are computed from existing `questions`, `review_logs`, `captures`, and `extracted_points` tables. Add indexes for performance:

```sql
-- Review logs by date for time-series queries
CREATE INDEX IF NOT EXISTS idx_review_logs_date ON review_logs (reviewed_at::date);

-- Questions by state for mastery distribution
CREATE INDEX IF NOT EXISTS idx_questions_state ON questions (state);
```

### New Files to Create

```
backend/
├── services/
│   └── analytics_service.py   # AnalyticsService: all analytics queries
└── models/
    └── analytics_models.py    # All analytics response models

frontend/
├── app/
│   └── analytics/
│       └── page.tsx           # Analytics dashboard page
├── components/
│   └── analytics/
│       ├── RetentionChart.tsx  # Line chart of retention over time
│       ├── MasteryDonut.tsx    # Donut chart of FSRS state distribution
│       ├── ActivityHeatmap.tsx # GitHub-style contribution heatmap
│       ├── WeakAreasList.tsx   # Table of weakest topics
│       ├── VelocityCards.tsx   # This week vs last week comparison cards
│       └── ConsistencyStats.tsx # Streak, review days, averages
└── hooks/
    └── useAnalytics.ts        # Fetch all analytics data
```

### Files to Modify

| File | Change |
|---|---|
| `backend/routers/stats.py` | Add analytics, retention-curve, weak-areas, activity endpoints |
| `backend/core/db_queries.py` | Add analytics queries |
| `frontend/lib/api.ts` | Add analytics API functions |
| `frontend/types/api.ts` | Add analytics types |
| `frontend/components/layout/DesktopSidebar.tsx` | Add "Analytics" nav link |

### Dependencies

| Package | Purpose |
|---|---|
| `recharts` (npm) | Lightweight React charting library (line, bar, donut charts) |

### Frontend Components

- **New page:** `app/analytics/page.tsx` — Full analytics dashboard with all charts
- **New component:** `components/analytics/RetentionChart.tsx` — Line chart showing retention % per week using Recharts `LineChart`
- **New component:** `components/analytics/MasteryDonut.tsx` — Donut/pie chart of question states (New/Learning/Review/Relearning) using Recharts `PieChart`
- **New component:** `components/analytics/ActivityHeatmap.tsx` — Grid of colored squares (90 days), darker = more reviews. Similar to GitHub contribution graph. Custom CSS Grid implementation, no library needed.
- **New component:** `components/analytics/WeakAreasList.tsx` — Sorted table of topics by retention rate, with progress bars
- **New component:** `components/analytics/VelocityCards.tsx` — Side-by-side comparison cards: "This week" vs "Last week" for captures and reviews, with up/down arrows
- **New component:** `components/analytics/ConsistencyStats.tsx` — Current streak, longest streak, review days badges

### Decision Logic

- **Retention curve granularity:** Weekly buckets. Daily is too noisy, monthly too coarse. Minimum 4 weeks of data before the chart is meaningful.
- **Weak areas definition:** Topics where <50% of reviews were rated Good/Easy (≥3). Sorted ascending so the weakest show first.
- **Activity heatmap:** 90 days of data. Each cell = one day. Color intensity based on total activity (captures + reviews). 0 = empty, 1-3 = light, 4-7 = medium, 8+ = dark.
- **No real-time updates:** Analytics are computed on page load. No WebSocket streaming or auto-refresh. User refreshes to see latest.
- **Empty state:** If <7 days of data, show a message: "Keep learning for a week to see your analytics."
- **Alternative rejected: Separate analytics database** — The queries are simple aggregations on existing tables. No need for OLAP, data warehousing, or materialized views at this scale.
- **Alternative rejected: Chart.js** — Recharts is more React-native, tree-shakeable, and has simpler API for responsive charts.

---

## 7. Browser Extension

### What It Does
Chrome extension: highlight text on any webpage → right-click → "Capture to ReCall" → sends highlighted text to the backend capture endpoint. Minimal UI — just the highlight-and-capture flow with a small popup for the result.

### API Endpoints

No new backend endpoints. The extension uses existing `POST /api/captures` and `POST /api/captures/url` endpoints directly. Auth token is stored in extension's `chrome.storage.sync`.

### Data Flow

```
User highlights text on any webpage:
│
├─ 1. Right-click → context menu shows "Capture to ReCall"
│
├─ 2. User clicks → content script captures:
│     ├─ window.getSelection().toString() → highlighted text
│     ├─ document.title → page title
│     └─ window.location.href → source URL
│
├─ 3. Background service worker sends POST /api/captures
│     {
│       raw_text: `${pageTitle}\n\n${selectedText}`,
│       source_type: "extension",
│       why_it_matters: null
│     }
│     Headers: { Authorization: "Bearer <token>" }
│
├─ 4. IF successful:
│     ├─ Background worker also calls POST to update capture source_url
│     ├─ Show notification badge on extension icon
│     └─ Optional: show small toast in page via content script
│
├─ 5. IF auth fails (401):
│     └─ Open extension popup prompting token entry
│
└─ 6. Popup (on click):
      ├─ Shows recent captures count
      ├─ Token configuration (if not set)
      └─ Link to ReCall dashboard
```

### Database Changes

None. Add `"extension"` as a new valid `source_type` value (no schema change — `source_type` is TEXT).

### New Files to Create

```
extension/
├── manifest.json              # Chrome extension manifest v3
├── background.js              # Service worker: context menu, API calls
├── content.js                 # Content script: capture selection, show toast
├── popup.html                 # Extension popup HTML
├── popup.js                   # Popup logic: settings, status
├── popup.css                  # Popup styling
├── options.html               # Options page for API URL + token
├── options.js                 # Options page logic
├── options.css                # Options page styling
├── icons/
│   ├── icon-16.png
│   ├── icon-48.png
│   └── icon-128.png
└── README.md                  # Setup and installation instructions
```

### Files to Modify

| File | Change |
|---|---|
| `backend/models/common.py` | Document `"extension"` as valid source_type (no code change needed — TEXT column) |

### Dependencies

None. Chrome Extension APIs are browser-native. No npm packages.

### Extension Components

- **`manifest.json`** — Manifest V3: `permissions: ["contextMenus", "storage", "notifications"]`, `host_permissions: ["http://localhost:8001/*"]` (configurable via options), content_scripts for all URLs
- **`background.js`** — Service worker: creates context menu item "Capture to ReCall", handles clicks, sends API request, manages auth token from storage
- **`content.js`** — Content script: captures `window.getSelection()`, sends to background via `chrome.runtime.sendMessage()`, shows inline toast notification ("Captured! 3 facts extracted")
- **`popup.html/js`** — Small popup: shows "Connected to ReCall" status, recent captures today count, "Settings" link. If no token configured, shows token input form.
- **`options.html/js`** — Full settings page: API URL (default `http://localhost:8001`), auth token input, "Test Connection" button

### Decision Logic

- **Manifest V3:** Required for new Chrome extensions. Service worker instead of background page.
- **Context menu approach:** Simpler than a floating action button on every page. No visual pollution. Right-click is intuitive for "do something with this selection."
- **Auth token in chrome.storage.sync:** Syncs across Chrome instances. More secure than localStorage (extension storage is isolated from web pages).
- **Content script permissions:** Runs on all URLs (`<all_urls>`) but only activates on right-click → context menu. No persistent content script running on every page.
- **Offline handling:** If backend is unreachable, store the capture in `chrome.storage.local` and retry when connection resumes (up to 10 queued items).
- **No bundler:** Plain JavaScript (no TypeScript, no webpack). Extension is <200 lines total. Keep it dead simple.
- **Host permissions:** Default to `http://localhost:8001/*`. User can change in options page for deployed instances (e.g., `https://recall.example.com/*`).
- **Error: No text selected** → Context menu handler checks `selectionText`. If empty, show notification "No text selected."
- **Error: API request fails** → Show notification "Capture failed. Check connection settings."
- **Alternative rejected: Firefox extension** — Chrome-first. Firefox WebExtension API is similar; can be ported later with minimal changes.
- **Alternative rejected: Bookmarklet** — No persistent auth storage, no context menu, limited API access. Extension is more capable.

---

## 8. Deployment (Docker Compose)

### What It Does
Docker Compose setup with three containers: backend (FastAPI), frontend (Next.js), and PostgreSQL with pgvector. Production-ready Dockerfiles with multi-stage builds. Environment variable configuration. Ready to deploy to Railway, Fly.io, or self-host.

### API Endpoints

No new endpoints. Adds health check endpoint enhancements.

| Existing Endpoint | Change |
|---|---|
| `GET /` | Enhanced: return DB connection status, version info |

### Data Flow

```
Docker Compose Architecture:
│
├─ docker-compose.yml
│
├─ Service: postgres
│   ├─ Image: pgvector/pgvector:pg16
│   ├─ Port: 5432 (internal only in production)
│   ├─ Volume: pgdata (persistent)
│   ├─ Healthcheck: pg_isready
│   └─ Init: runs schema.sql on first start
│
├─ Service: backend
│   ├─ Build: backend/Dockerfile
│   ├─ Port: 8001
│   ├─ Depends on: postgres (healthy)
│   ├─ Environment: DATABASE_URL, OPENAI_API_KEY, AUTH_SECRET_KEY, etc.
│   ├─ Healthcheck: curl http://localhost:8001/
│   └─ Command: uvicorn main:app --host 0.0.0.0 --port 8001
│
└─ Service: frontend
    ├─ Build: frontend/Dockerfile
    ├─ Port: 3000
    ├─ Depends on: backend (healthy)
    ├─ Environment: NEXT_PUBLIC_API_URL=http://backend:8001
    └─ Command: node server.js (production Next.js)
```

### Database Changes

None. Schema.sql is run automatically on first PostgreSQL start via Docker init scripts.

### New Files to Create

```
docker-compose.yml                  # Main compose file
docker-compose.dev.yml              # Dev overrides (hot reload, exposed DB port)
backend/
└── Dockerfile                      # Multi-stage: build deps → run
frontend/
└── Dockerfile                      # Multi-stage: deps → build → run
.dockerignore                       # Exclude node_modules, venv, __pycache__, .git
docker/
├── postgres/
│   └── init.sql                    # Combined schema.sql (copy of backend/schema.sql)
└── .env.example                    # Template environment file
```

### Files to Modify

| File | Change |
|---|---|
| `backend/main.py` | Enhanced health check with DB status |
| `backend/config.py` | Add `SENTRY_DSN` and other production settings |
| `frontend/next.config.js` | Add `output: 'standalone'` for Docker production builds |
| `.gitignore` | Add Docker-specific ignores |

### Dependencies

None new. Docker and Docker Compose are runtime dependencies on the host.

### Docker Configuration Details

#### `backend/Dockerfile`
```dockerfile
# Multi-stage build
# Stage 1: Install dependencies
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Production image
FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /install /usr/local
COPY . .
EXPOSE 8001
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
```

#### `frontend/Dockerfile`
```dockerfile
# Multi-stage build
# Stage 1: Dependencies
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci --only=production

# Stage 2: Build
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# Stage 3: Production
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
EXPOSE 3000
CMD ["node", "server.js"]
```

#### `docker-compose.yml`
```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: recall_mvp
      POSTGRES_USER: ${POSTGRES_USER:-recall}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./docker/postgres/init.sql:/docker-entrypoint-initdb.d/01-schema.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-recall}"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  backend:
    build: ./backend
    ports:
      - "${BACKEND_PORT:-8001}:8001"
    environment:
      DATABASE_URL: postgresql://${POSTGRES_USER:-recall}:${POSTGRES_PASSWORD}@postgres:5432/recall_mvp
      OPENAI_API_KEY: ${OPENAI_API_KEY:?Set OPENAI_API_KEY}
      AUTH_SECRET_KEY: ${AUTH_SECRET_KEY:-}
      VAPID_PRIVATE_KEY: ${VAPID_PRIVATE_KEY:-}
      VAPID_PUBLIC_KEY: ${VAPID_PUBLIC_KEY:-}
      SENTRY_DSN_BACKEND: ${SENTRY_DSN_BACKEND:-}
      ENV: production
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/"]
      interval: 10s
      timeout: 5s
      retries: 3
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      args:
        NEXT_PUBLIC_API_URL: ${NEXT_PUBLIC_API_URL:-http://localhost:8001}
    ports:
      - "${FRONTEND_PORT:-3000}:3000"
    environment:
      NEXT_PUBLIC_API_URL: ${NEXT_PUBLIC_API_URL:-http://localhost:8001}
      SENTRY_DSN_FRONTEND: ${SENTRY_DSN_FRONTEND:-}
    depends_on:
      backend:
        condition: service_healthy
    restart: unless-stopped

volumes:
  pgdata:
```

#### `docker-compose.dev.yml`
```yaml
# Development overrides: hot reload, exposed DB, no production builds
services:
  postgres:
    ports:
      - "5432:5432"

  backend:
    build:
      context: ./backend
      target: builder
    volumes:
      - ./backend:/app
    command: uvicorn main:app --host 0.0.0.0 --port 8001 --reload
    environment:
      ENV: development

  frontend:
    build:
      context: ./frontend
      target: deps
    volumes:
      - ./frontend:/app
      - /app/node_modules
    command: npm run dev -- --port 3000
    environment:
      NODE_ENV: development
```

### Decision Logic

- **pgvector/pgvector:pg16 image:** Official pgvector Docker image with PostgreSQL 16. Includes pgvector pre-installed — no manual extension setup.
- **Multi-stage builds:** Separate dependency installation from application code. Smaller final images. Docker layer caching speeds up rebuilds.
- **Next.js standalone output:** `output: 'standalone'` in next.config.js produces a self-contained server.js that doesn't need `node_modules` at runtime. Reduces image size from ~500MB to ~100MB.
- **Health checks:** Compose `depends_on` with `condition: service_healthy` ensures proper startup order. No race conditions between backend and database.
- **Persistent volume:** `pgdata` volume survives container restarts. Data persists across deployments.
- **Schema init:** PostgreSQL Docker image runs `.sql` files in `/docker-entrypoint-initdb.d/` on first start. Handles initial schema creation.
- **Dev overrides:** `docker-compose.dev.yml` mounts source directories as volumes for hot reload. Run with `docker compose -f docker-compose.yml -f docker-compose.dev.yml up`.
- **Railway/Fly.io compatibility:** Each service can be deployed independently. Backend and frontend have their own Dockerfiles. Database is typically a managed service on these platforms.
- **Alternative rejected: Single-container approach** — Packing everything in one container simplifies deployment but prevents independent scaling and makes updates harder.
- **Alternative rejected: Nginx reverse proxy** — Not needed for MVP. Direct port exposure is simpler. Add Nginx/Traefik when SSL termination is needed.

---

## 9. Error Monitoring (Sentry)

### What It Does
Sentry integration for both backend (Python/FastAPI) and frontend (Next.js). Captures unhandled exceptions, API errors, slow transactions. PII is scrubbed from error reports. Environment and release tagging for filtering.

### API Endpoints

No new endpoints. Sentry integrates as middleware/SDK initialization.

### Data Flow

```
Backend Error Flow:
│
├─ 1. Sentry SDK initialized in main.py lifespan
│     sentry_sdk.init(dsn=..., traces_sample_rate=0.1)
│
├─ 2. FastAPI integration auto-captures:
│     ├─ Unhandled exceptions in route handlers
│     ├─ 500 errors from global exception handler
│     └─ Slow transactions (>2s)
│
├─ 3. Before sending: PII scrub callback
│     ├─ Strip user_answer, raw_text from event data
│     ├─ Strip Authorization headers
│     └─ Strip IP addresses
│
└─ 4. Event sent to Sentry cloud (or self-hosted)

Frontend Error Flow:
│
├─ 1. Sentry SDK initialized in instrumentation.ts (Next.js convention)
│
├─ 2. Auto-captures:
│     ├─ Unhandled JS errors (window.onerror)
│     ├─ Unhandled promise rejections
│     ├─ React component error boundaries
│     └─ Fetch errors from api.ts
│
├─ 3. Manual breadcrumbs:
│     ├─ API call start/end
│     ├─ Page navigation
│     └─ User actions (capture, review, rate)
│
└─ 4. Event sent to Sentry cloud
```

### Database Changes

None.

### New Files to Create

```
backend/
└── core/
    └── sentry_setup.py        # init_sentry(), PII scrub callback, custom tags

frontend/
├── sentry.client.config.ts    # Browser-side Sentry init
├── sentry.server.config.ts    # Server-side Sentry init (SSR)
├── sentry.edge.config.ts      # Edge runtime Sentry init
└── instrumentation.ts         # Next.js instrumentation hook
```

### Files to Modify

| File | Change |
|---|---|
| `backend/config.py` | Add `SENTRY_DSN_BACKEND: str = ""`, `SENTRY_TRACES_SAMPLE_RATE: float = 0.1` |
| `backend/main.py` | Call `init_sentry()` in lifespan startup (before pool creation) |
| `backend/requirements.txt` | Add `sentry-sdk[fastapi]` |
| `frontend/package.json` | Add `@sentry/nextjs` |
| `frontend/next.config.js` | Wrap with `withSentryConfig()` from `@sentry/nextjs` |
| `frontend/lib/api.ts` | Add Sentry breadcrumbs on API calls, capture exceptions on fetch errors |

### Dependencies

| Package | Purpose |
|---|---|
| `sentry-sdk[fastapi]>=2.0.0` (pip) | Python Sentry SDK with FastAPI integration |
| `@sentry/nextjs` (npm) | Next.js Sentry SDK with automatic instrumentation |

### Decision Logic

- **PII scrubbing:** Critical for a knowledge app. `raw_text`, `user_answer`, and `content` fields are stripped from error events. Only error type, stack trace, endpoint, and timing are sent.
- **Traces sample rate:** 0.1 (10%) for performance monitoring. Enough to spot slow endpoints without overwhelming the free tier (5K errors/month, 100K transactions/month).
- **Conditional init:** If `SENTRY_DSN` is empty/unset, Sentry is not initialized. No errors, no overhead. Development works unchanged.
- **Source maps:** `@sentry/nextjs` automatically uploads source maps during `next build`. Stack traces in Sentry show original TypeScript code.
- **Release tagging:** Use git commit SHA as release version. Allows tracking which deployment introduced a bug.
- **Environment tagging:** Use `ENV` setting (`development`/`production`). Filter errors by environment in Sentry dashboard.
- **Error: Sentry SDK fails to init** → Log warning, app continues without monitoring. Non-fatal.
- **Alternative rejected: Self-hosted Sentry** — Requires significant infrastructure (PostgreSQL, Redis, Kafka, ClickHouse). Use Sentry cloud free tier.
- **Alternative rejected: Datadog/New Relic** — Heavier, more expensive, overkill for personal project. Sentry free tier is sufficient.
- **Alternative rejected: Custom error logging to DB** — Reinventing Sentry. Doesn't provide stack traces, source maps, or alerting.

---

## 10. Performance & Caching

### What It Does
PostgreSQL-based caching for frequently-hit endpoints (dashboard stats, reviews due count). Connection pool tuning. LLM response caching for identical queries. Lazy loading for heavy frontend pages (analytics, graph). No Redis — keep infrastructure simple with PostgreSQL-backed caching.

### API Endpoints

No new endpoints. Caching is transparent to the API surface.

| Existing Endpoint | Change |
|---|---|
| `GET /api/stats/dashboard` | Cached for 30 seconds |
| `GET /api/reviews/due` | Due count cached for 30 seconds (question list is NOT cached) |
| `POST /api/knowledge/search` | LLM response cached by query hash for 1 hour |

### Data Flow

```
In-Memory Cache (dashboard stats, due count):
│
├─ 1. Request arrives for GET /api/stats/dashboard
│
├─ 2. Check in-memory cache (Python dict with TTL)
│     ├─ IF cache hit AND not expired → return cached response (0ms)
│     └─ IF cache miss OR expired → compute from DB
│
├─ 3. Store result in cache with 30-second TTL
│
└─ 4. Return response

LLM Response Cache (knowledge search):
│
├─ 1. POST /api/knowledge/search { query: "WebSockets" }
│
├─ 2. Compute cache key: SHA256(normalized_query)
│     Normalize: lowercase, strip whitespace, sort words
│
├─ 3. Check llm_cache table in PostgreSQL
│     SELECT response_json FROM llm_cache
│     WHERE cache_key = $1 AND expires_at > NOW()
│
├─ 4. IF cache hit → return cached response (skip embedding + LLM)
│
├─ 5. IF cache miss → compute normally, then cache:
│     INSERT INTO llm_cache (cache_key, query, response_json, expires_at)
│     VALUES ($1, $2, $3, NOW() + INTERVAL '1 hour')
│
└─ 6. Return response

Connection Pool Tuning:
│
├─ Current: min_size=2, max_size=10
│
├─ Production: min_size=5, max_size=20
│     (Configurable via settings)
│
└─ Add pool monitoring: log pool.get_size() and pool.get_idle_size() periodically

Frontend Lazy Loading:
│
├─ Analytics page: dynamic(() => import(...), { loading: ... })
│     Only loads Recharts + heavy components when navigating to /analytics
│
├─ Graph page: dynamic(() => import(...), { loading: ... })
│     Only loads Sigma.js + graphology when navigating to /graph
│
└─ Review page: already lightweight — no change needed
```

### Database Changes

```sql
-- LLM response cache table
CREATE TABLE IF NOT EXISTS llm_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cache_key TEXT NOT NULL UNIQUE,      -- SHA256 hash of normalized query
    query TEXT NOT NULL,                 -- Original query for debugging
    response_json JSONB NOT NULL,        -- Cached response
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL
);

-- Index for cache lookups + expiry cleanup
CREATE INDEX IF NOT EXISTS idx_llm_cache_key ON llm_cache (cache_key);
CREATE INDEX IF NOT EXISTS idx_llm_cache_expires ON llm_cache (expires_at);
```

### New Files to Create

```
backend/
└── core/
    ├── cache.py               # InMemoryCache class (TTL dict), LLMCache (PostgreSQL)
    └── pool_monitor.py        # Log pool stats periodically (asyncio task)
```

### Files to Modify

| File | Change |
|---|---|
| `backend/config.py` | Add `DB_POOL_MIN: int = 2`, `DB_POOL_MAX: int = 10`, `CACHE_TTL_STATS: int = 30`, `CACHE_TTL_LLM: int = 3600` |
| `backend/db.py` | Use pool size settings from config |
| `backend/main.py` | Initialize caches in lifespan, start pool monitor task, add cache cleanup task |
| `backend/routers/stats.py` | Wrap dashboard call with in-memory cache |
| `backend/services/knowledge_service.py` | Add LLM response caching in search() |
| `backend/core/db_queries.py` | Add llm_cache CRUD queries, cache cleanup query |
| `frontend/app/analytics/page.tsx` | Use `next/dynamic` for lazy loading chart components |
| `frontend/app/graph/page.tsx` | Use `next/dynamic` for lazy loading graph components |

### Dependencies

None. In-memory caching uses Python stdlib. LLM caching uses existing PostgreSQL.

### Cache Implementation Details

#### In-Memory Cache (Python)
```python
class InMemoryCache:
    """Simple TTL cache using dict. Thread-safe for async (GIL)."""
    def __init__(self):
        self._store: dict[str, tuple[Any, float]] = {}  # key → (value, expires_at)

    def get(self, key: str) -> Any | None:
        if key in self._store:
            value, expires_at = self._store[key]
            if time.time() < expires_at:
                return value
            del self._store[key]
        return None

    def set(self, key: str, value: Any, ttl_seconds: int):
        self._store[key] = (value, time.time() + ttl_seconds)

    def invalidate(self, key: str):
        self._store.pop(key, None)

    def clear(self):
        self._store.clear()
```

#### Cache Invalidation Strategy
- **Dashboard stats:** Invalidated on any review, capture, or reflection action (by setting TTL to 0 on the cache key). Also expires automatically after 30 seconds.
- **LLM cache:** Expires after 1 hour. No manual invalidation — knowledge base changes don't frequently affect search results for the same query.
- **Cache cleanup:** Background task runs every hour to delete expired rows from `llm_cache` table: `DELETE FROM llm_cache WHERE expires_at < NOW()`.

### Decision Logic

- **No Redis:** Single-user app on a single server. In-memory dict for hot data, PostgreSQL for persistent cache. Redis adds infrastructure complexity for no benefit at this scale.
- **30-second TTL for stats:** Dashboard is polled every 60 seconds. A 30-second cache cuts DB queries in half while keeping data fresh enough.
- **1-hour TTL for LLM cache:** Knowledge search results change slowly (only when new captures are added). Caching identical queries saves LLM cost and latency.
- **Query normalization:** `"What about WebSockets?"` and `"websockets what about"` map to the same cache key. Prevents cache misses for equivalent queries.
- **Pool sizing:** Production defaults (min=5, max=20) prevent connection starvation under concurrent requests while not wasting resources in idle periods.
- **Lazy loading impact:** Analytics page loads Recharts (~40KB gzipped), Graph page loads Sigma.js + graphology (~60KB gzipped). Lazy loading keeps the initial bundle under 100KB.
- **Error: Cache write fails** → Log warning, continue without caching. Non-fatal.
- **Alternative rejected: Redis** — Additional container, connection management, and deployment complexity. PostgreSQL `llm_cache` table serves the same purpose.
- **Alternative rejected: Memcached** — Same argument as Redis. Not worth the infrastructure at this scale.
- **Alternative rejected: HTTP cache headers (ETag/If-None-Match)** — Useful but doesn't save backend computation. The DB queries still run. In-memory cache prevents DB hits entirely.

---

## Schema Migration SQL

All database changes in a single migration block:

```sql
-- ============================================================
-- Phase 5 Migration: Polish & Advanced Features
-- Run after Phase 4 schema is in place
-- ============================================================

-- 1. Push Notifications: subscription storage
CREATE TABLE IF NOT EXISTS notification_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    endpoint TEXT NOT NULL UNIQUE,
    p256dh_key TEXT NOT NULL,
    auth_key TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Push Notifications: settings (single-user)
CREATE TABLE IF NOT EXISTS notification_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    enabled BOOLEAN NOT NULL DEFAULT true,
    review_reminder_time TEXT NOT NULL DEFAULT '09:00',
    timezone TEXT NOT NULL DEFAULT 'UTC',
    last_sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Method of Loci: walkthrough sessions
CREATE TABLE IF NOT EXISTS loci_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    items JSONB NOT NULL,
    palace_theme TEXT NOT NULL,
    walkthrough_json JSONB NOT NULL,
    full_narration TEXT NOT NULL,
    capture_id UUID REFERENCES captures(id),
    last_recall_score INT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Performance: LLM response cache
CREATE TABLE IF NOT EXISTS llm_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cache_key TEXT NOT NULL UNIQUE,
    query TEXT NOT NULL,
    response_json JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_loci_sessions_created ON loci_sessions (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_llm_cache_key ON llm_cache (cache_key);
CREATE INDEX IF NOT EXISTS idx_llm_cache_expires ON llm_cache (expires_at);
CREATE INDEX IF NOT EXISTS idx_review_logs_date ON review_logs (reviewed_at::date);
CREATE INDEX IF NOT EXISTS idx_questions_state ON questions (state);
CREATE INDEX IF NOT EXISTS idx_extracted_points_embedding_not_null
    ON extracted_points (id) WHERE embedding IS NOT NULL;
```

---

## New Files to Create

### Backend

```
backend/
├── core/
│   ├── auth.py                # AuthMiddleware, verify_token(), constant-time compare
│   ├── cache.py               # InMemoryCache, LLMCache (PostgreSQL-backed)
│   ├── push.py                # VAPID key management, pywebpush wrapper
│   ├── pool_monitor.py        # Periodic pool stats logging
│   └── sentry_setup.py        # init_sentry(), PII scrub, custom tags
│
├── routers/
│   ├── auth.py                # POST /verify, GET /status
│   ├── notifications.py       # Subscribe, settings, test endpoints
│   ├── loci.py                # POST /create, GET /{id}, POST /{id}/recall, GET /
│   └── graph.py               # GET /graph, GET /graph/node/{id}
│
├── services/
│   ├── notification_service.py # Subscribe, send_push, check_and_send
│   ├── loci_service.py         # Create, get, recall, list
│   ├── analytics_service.py    # All analytics queries
│   └── graph_service.py        # Graph data, node detail
│
├── models/
│   ├── auth_models.py          # AuthVerifyRequest/Response, AuthStatusResponse
│   ├── notification_models.py  # PushSubscription, NotificationSettings
│   ├── loci_models.py          # All Loci models
│   ├── analytics_models.py     # All analytics models
│   └── graph_models.py         # Graph node/edge models
│
├── prompts/
│   ├── loci_walkthrough_generation.txt
│   └── loci_recall_evaluation.txt
│
└── Dockerfile                   # Production multi-stage build
```

### Frontend

```
frontend/
├── app/
│   ├── login/
│   │   └── page.tsx            # Auth login page
│   ├── loci/
│   │   ├── page.tsx            # Loci sessions list
│   │   └── create/
│   │       └── page.tsx        # Create new memory palace
│   ├── graph/
│   │   └── page.tsx            # Knowledge graph visualization
│   ├── analytics/
│   │   └── page.tsx            # Analytics dashboard
│   └── settings/
│       └── page.tsx            # Notification settings
│
├── components/
│   ├── auth/
│   │   └── LoginForm.tsx
│   ├── loci/
│   │   ├── LociItemList.tsx
│   │   ├── WalkthroughPlayer.tsx
│   │   ├── RecallTest.tsx
│   │   └── RecallResults.tsx
│   ├── graph/
│   │   ├── KnowledgeGraph.tsx
│   │   ├── GraphControls.tsx
│   │   └── NodeDetail.tsx
│   ├── analytics/
│   │   ├── RetentionChart.tsx
│   │   ├── MasteryDonut.tsx
│   │   ├── ActivityHeatmap.tsx
│   │   ├── WeakAreasList.tsx
│   │   ├── VelocityCards.tsx
│   │   └── ConsistencyStats.tsx
│   └── settings/
│       └── NotificationSettings.tsx
│
├── hooks/
│   ├── useNotifications.ts
│   ├── useKnowledgeGraph.ts
│   └── useAnalytics.ts
│
├── lib/
│   ├── offline-store.ts        # IndexedDB for PWA offline support
│   └── push.ts                 # Push subscription management
│
├── public/
│   ├── manifest.json
│   ├── sw.js
│   ├── icon-192.png
│   └── icon-512.png
│
├── sentry.client.config.ts
├── sentry.server.config.ts
├── sentry.edge.config.ts
├── instrumentation.ts
│
└── Dockerfile                   # Production multi-stage build
```

### Project Root

```
extension/
├── manifest.json
├── background.js
├── content.js
├── popup.html
├── popup.js
├── popup.css
├── options.html
├── options.js
├── options.css
├── icons/
│   ├── icon-16.png
│   ├── icon-48.png
│   └── icon-128.png
└── README.md

docker-compose.yml
docker-compose.dev.yml
.dockerignore
docker/
├── postgres/
│   └── init.sql
└── .env.example
```

---

## Integration Points

### How New Features Connect to Existing Code

| New Feature | Integrates With | How |
|---|---|---|
| **Authentication** | Every existing endpoint | Middleware intercepts all `/api/*` requests before routers |
| **Authentication** | `frontend/lib/api.ts` | `request()` function adds Bearer token header from localStorage |
| **Authentication** | Browser Extension | Extension stores token in `chrome.storage.sync`, sends in headers |
| **PWA Setup** | `frontend/app/layout.tsx` | Adds manifest link, service worker registration |
| **PWA Setup** | `frontend/hooks/useReviewSession.ts` | Uses `offline-store.ts` for caching questions and queuing ratings |
| **Push Notifications** | `frontend/public/sw.js` | Service worker handles `push` and `notificationclick` events |
| **Push Notifications** | `backend/main.py` lifespan | Background asyncio task checks and sends notifications |
| **Push Notifications** | `core/db_queries.py` → `count_due_questions()` | Reuses existing due count query to check if notification is needed |
| **Method of Loci** | `CaptureService.process()` | Auto-captures items on palace creation for FSRS scheduling |
| **Method of Loci** | `POST /api/voice/tts` | Frontend uses existing TTS endpoint to narrate the walkthrough |
| **Method of Loci** | `core/llm.py` | Add `generate_loci_walkthrough()` and `evaluate_loci_recall()` |
| **Knowledge Graph** | `core/db_queries.py` → `search_similar_points()` | Reuses embedding similarity infrastructure for edge computation |
| **Knowledge Graph** | `connection_questions` table | Explicit connections become graph edges |
| **Analytics Dashboard** | `review_logs` table | All analytics derived from existing review history |
| **Analytics Dashboard** | `questions` table | Mastery distribution from FSRS state column |
| **Analytics Dashboard** | `captures` table | Learning velocity from capture timestamps |
| **Browser Extension** | `POST /api/captures` | Uses existing capture endpoint directly |
| **Browser Extension** | Auth middleware | Extension sends Bearer token in requests |
| **Docker Compose** | All services | Packages existing backend/frontend/DB into containers |
| **Sentry** | `backend/main.py` global exception handler | Sentry captures exceptions before the 500 response |
| **Sentry** | `frontend/lib/api.ts` | Sentry breadcrumbs on API calls, exception capture on errors |
| **Performance Cache** | `GET /api/stats/dashboard` | In-memory cache wraps existing stats query |
| **Performance Cache** | `KnowledgeService.search()` | LLM cache wraps existing search pipeline |

### Router Registration in `main.py`

```python
# Add to existing router imports and mounts:
from routers import auth, notifications, loci, graph

# Auth router is mounted WITHOUT auth middleware (excluded paths)
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])

# All other new routers are protected by auth middleware
app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])
app.include_router(loci.router, prefix="/api/loci", tags=["loci"])
app.include_router(graph.router, prefix="/api/knowledge", tags=["knowledge-graph"])

# Analytics endpoints added to existing stats router (no new router)
```

### Updated `config.py`

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # Auth
    AUTH_SECRET_KEY: str = ""  # Empty = auth disabled (dev mode)

    # Push notifications (VAPID)
    VAPID_PRIVATE_KEY: str = ""
    VAPID_PUBLIC_KEY: str = ""
    VAPID_EMAIL: str = ""

    # Sentry
    SENTRY_DSN_BACKEND: str = ""
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1

    # Database pool
    DB_POOL_MIN: int = 2
    DB_POOL_MAX: int = 10

    # Cache
    CACHE_TTL_STATS: int = 30       # seconds
    CACHE_TTL_LLM: int = 3600      # seconds (1 hour)
```

### Frontend API Client Extensions

Add to `frontend/lib/api.ts`:

```typescript
// Auth
export async function verifyToken(token: string): Promise<AuthVerifyResponse>;
export async function getAuthStatus(): Promise<AuthStatusResponse>;

// Notifications
export async function subscribePush(subscription: PushSubscription): Promise<void>;
export async function unsubscribePush(): Promise<void>;
export async function getNotificationSettings(): Promise<NotificationSettingsResponse>;
export async function updateNotificationSettings(settings: NotificationSettings): Promise<void>;
export async function sendTestNotification(): Promise<void>;

// Method of Loci
export async function createLociSession(data: LociCreateRequest): Promise<LociCreateResponse>;
export async function getLociSession(sessionId: string): Promise<LociCreateResponse>;
export async function submitLociRecall(sessionId: string, items: string[]): Promise<LociRecallResponse>;
export async function listLociSessions(): Promise<LociListItem[]>;

// Knowledge Graph
export async function fetchGraphData(minSimilarity?: number, limit?: number): Promise<GraphDataResponse>;
export async function fetchNodeDetail(nodeId: string): Promise<NodeDetailResponse>;

// Analytics
export async function fetchAnalytics(): Promise<AnalyticsResponse>;
export async function fetchRetentionCurve(weeks?: number): Promise<RetentionCurveResponse>;
export async function fetchWeakAreas(limit?: number): Promise<WeakAreasResponse>;
export async function fetchActivity(days?: number): Promise<ActivityResponse>;
```

### Updated Navigation

Add to `DesktopSidebar.tsx` and `MobileTabBar.tsx`:

```typescript
// New nav items (add after existing ones):
<NavLink href="/loci" icon={Map} label="Memory Palace" />
<NavLink href="/graph" icon={GitBranch} label="Graph" />
<NavLink href="/analytics" icon={BarChart3} label="Analytics" />
<NavLink href="/settings" icon={Settings} label="Settings" />
```

### Updated `frontend/types/api.ts`

Add all new TypeScript interfaces matching the backend models defined in each feature section above.

---

## Key Architecture Decisions

### Decision 1: API Key Auth over JWT/OAuth
**Chosen:** Simple pre-configured API key checked via middleware.
**Why:** Single-user app. No registration, no user management, no token refresh. A shared secret compared with `hmac.compare_digest()` is simple, secure, and sufficient.
**Rejected:** JWT (unnecessary complexity, refresh token management), OAuth/OIDC (massive overkill, requires external IdP), session cookies (CSRF risk, doesn't work for browser extension).

### Decision 2: PostgreSQL Cache over Redis
**Chosen:** In-memory Python dict for hot data (TTL 30s), PostgreSQL table for LLM response cache (TTL 1h).
**Why:** No new infrastructure. Single-user doesn't need distributed caching. Python dict is faster than any external cache for hot paths. PostgreSQL `llm_cache` table persists across restarts.
**Rejected:** Redis (additional container, connection management, deployment complexity for zero benefit at single-user scale), Memcached (same reasoning).

### Decision 3: Hand-written Service Worker over next-pwa
**Chosen:** Manual `sw.js` in `public/` with explicit cache and sync logic.
**Why:** Full control over caching strategy (network-first for API, cache-first for assets). Under 100 lines. No magic black-box behavior. Easy to debug.
**Rejected:** next-pwa (adds configuration complexity, abstracts away cache control, hard to customize offline behavior for specific routes).

### Decision 4: Web Push API over Firebase Cloud Messaging
**Chosen:** Standard Web Push with VAPID keys, delivered via `pywebpush`.
**Why:** Open standard, no Google dependency, works with any browser supporting Push API. VAPID keys are self-managed.
**Rejected:** FCM (Google vendor lock-in, requires Google Cloud project), email notifications (requires SMTP, email collection), SMS (requires Twilio, phone number).

### Decision 5: Sigma.js over D3.js for Knowledge Graph
**Chosen:** Sigma.js via `@react-sigma/core` with graphology data structure.
**Why:** WebGL-based rendering handles 200+ nodes smoothly. React integration via @react-sigma/core. ForceAtlas2 layout algorithm produces good graph layouts without manual positioning.
**Rejected:** D3.js force graph (SVG-based, performance degrades above 100 nodes), vis.js (heavier, less React-native), Cytoscape.js (more complex API for same result).

### Decision 6: Recharts over Chart.js for Analytics
**Chosen:** Recharts for all chart components.
**Why:** React-native (JSX-based API), tree-shakeable (only import what you use), responsive out of the box, simpler API than Chart.js for React.
**Rejected:** Chart.js (imperative API, requires react-chartjs-2 wrapper, less ergonomic in React), Nivo (heavier, more opinionated), Victory (Formidable Labs, less maintained).

### Decision 7: Standalone Extension over Bookmarklet
**Chosen:** Chrome Extension with Manifest V3.
**Why:** Persistent auth storage (chrome.storage.sync), context menu integration, background service worker for reliable API calls, notification badges, works across Chrome instances.
**Rejected:** Bookmarklet (no persistent storage, limited API access, can be blocked by CSP), web clipper (requires more complex UI), share target (requires PWA installed first).

### Decision 8: Docker Compose over Kubernetes
**Chosen:** Docker Compose with three services.
**Why:** Single-user personal project. Docker Compose is simple, well-understood, and sufficient. Works for local dev and single-server deployment.
**Rejected:** Kubernetes (massive overkill, operational complexity), single Dockerfile (can't scale components independently), bare-metal (not reproducible).

### Decision 9: Background asyncio Task over Celery for Notifications
**Chosen:** Simple `asyncio.create_task()` in FastAPI lifespan for notification scheduling.
**Why:** One check per minute, one notification per day. Celery requires a separate worker process + message broker (Redis/RabbitMQ). Way too much infrastructure for a single scheduled task.
**Rejected:** Celery (requires Redis/RabbitMQ, separate worker), APScheduler (additional dependency for one task), OS cron (not portable, not Dockerized).

### Decision 10: Sentry Cloud over Self-Hosted
**Chosen:** Sentry cloud (sentry.io) free tier.
**Why:** Free tier covers 5K errors/month and 100K transactions/month. Zero infrastructure management. Automatic source map upload via @sentry/nextjs.
**Rejected:** Self-hosted Sentry (requires PostgreSQL, Redis, Kafka, ClickHouse — massive infrastructure), custom error DB table (no stack traces, no source maps, no alerting), Datadog (expensive, overkill).
