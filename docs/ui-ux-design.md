# ReCall — UI/UX Design Document
**Version:** 1.0  
**Date:** April 18, 2026  
**Stack:** Next.js 14 (App Router) + Tailwind CSS + shadcn/ui  
**Approach:** Mobile-first, single-user MVP, text-only (Phase 1)

---

## 1. User Persona

**Name:** Sharuk (founder / sole user in MVP)  
**Role:** Software developer, lifelong learner  
**Goal:** Capture what he learns daily and actually retain it through spaced repetition  
**Skill level:** Technical — comfortable with web apps, no hand-holding needed  
**Device:** Primarily phone (capture on-the-go), laptop for review sessions  
**Daily usage pattern:**
- **Morning:** Open dashboard → start review session (3–5 min)
- **Throughout day:** Quick captures after reading/meetings/conversations
- **Evening:** Optional reflection capture

---

## 2. User Journeys

### Journey 1: First-Time Use (Cold Start)

```
Entry: User opens app for the first time
  → Dashboard shows all zeros (empty state)
  → Prominent CTA: "Capture your first learning"
  → User navigates to /capture
  → Types something they learned
  → Optionally fills "Why does this matter?"
  → Submits → sees success: "3 facts extracted, 4 questions generated"
  → Returns to Dashboard → sees "4 reviews due"
  → Clicks "Start Review" → enters first review session
  → Completes review → sees session summary
  → Dashboard updates with streak = 1
```

### Journey 2: Daily Capture

```
Entry: User taps "Capture" in bottom nav (mobile) or sidebar (desktop)
  → Text area is focused and ready
  → User pastes or types what they learned
  → Optionally adds "Why does this matter?"
  → Clicks "Capture" button
  → Loading state: spinner + "Extracting knowledge..."
  → Success: card shows facts_count + questions_count
  → Form clears for next capture
  → User can capture more or navigate away
Error: If extraction fails → show "Saved but extraction failed. Will retry."
Error: If no facts found → show "No reviewable facts found. Try being more specific."
```

### Journey 3: Daily Review Session

```
Entry: User taps "Review" in nav, or "Start Review" on Dashboard
  → Fetch due questions (loading spinner)
  → IF 0 due → empty state: "All caught up! Nothing to review."
  → IF >0 due → enter review loop:

  LOOP (for each question):
    1. QUESTION phase:
       - Show question text + question type badge + mnemonic hint (if any)
       - Text area for answer
       - "Check Answer" button (disabled until input)
    
    2. EVALUATING phase:
       - User clicks "Check Answer"
       - Spinner: "Evaluating..."
       - POST /api/reviews/evaluate
    
    3. FEEDBACK phase:
       - Show correct answer
       - Show AI feedback (score: correct/partial/wrong with color)
       - Show 4 rating buttons: Again / Hard / Good / Easy
       - Suggested rating is pre-highlighted
    
    4. RATING phase:
       - User clicks a rating
       - Brief spinner
       - POST /api/reviews/rate
       - Auto-advance to next question
  
  END:
    - Session complete screen: total reviewed, rating distribution, time spent
    - "Back to Dashboard" button

  AT ANY TIME:
    - "End Session" button → shows partial summary
    - Progress bar shows X of Y questions
```

### Journey 4: Browsing Capture History

```
Entry: User taps "History" in nav
  → List of recent captures (newest first)
  → Each card shows: truncated text (200 chars), facts count, date
  → Tap a capture → detail view:
    - Full raw text
    - "Why it matters" (if provided)
    - List of extracted facts
    - List of generated questions with FSRS state
  → Back button returns to list
  → Infinite scroll / "Load more" for pagination
```

---

## 3. Information Architecture

```
App
├── / (Dashboard)
│   ├── Stats overview (due today, streak, retention, totals)
│   ├── "Start Review" CTA (if due > 0)
│   └── Recent captures list (last 5)
│
├── /capture
│   └── Capture form (text area + why prompt + submit)
│
├── /review
│   ├── Empty state (no due items)
│   ├── Review session (question → answer → feedback → rate loop)
│   └── Session complete summary
│
└── /history
    ├── Capture list (paginated)
    └── /history/[id] — Capture detail (facts + questions)
```

**Navigation:** Bottom tab bar (mobile), left sidebar (desktop)  
**Tabs:** Dashboard | Capture | Review | History

---

## 4. Page Designs & Component Hierarchy

### 4.1 Root Layout (`app/layout.tsx`)

```
<html>
  <body>
    <div className="flex min-h-screen">
      {/* Desktop: sidebar */}
      <DesktopSidebar />          {/* hidden on mobile */}
      
      <main className="flex-1 pb-16 md:pb-0">
        {children}                {/* page content */}
      </main>
      
      {/* Mobile: bottom tab bar */}
      <MobileTabBar />            {/* hidden on desktop */}
    </div>
  </body>
</html>
```

**Component tree:**
```
RootLayout
├── DesktopSidebar
│   ├── AppLogo ("ReCall")
│   ├── NavLink (Dashboard, icon: LayoutDashboard)
│   ├── NavLink (Capture, icon: Plus)
│   ├── NavLink (Review, icon: Brain)
│   └── NavLink (History, icon: Clock)
│
├── {children} (page content)
│
└── MobileTabBar
    ├── TabItem (Dashboard, icon: LayoutDashboard)
    ├── TabItem (Capture, icon: PlusCircle)
    ├── TabItem (Review, icon: Brain, badge: dueCount)
    └── TabItem (History, icon: Clock)
```

---

### 4.2 Dashboard (`app/page.tsx`)

**Purpose:** At-a-glance status — how much to review, motivation stats, recent activity.

**Wireframe:**
```
┌─────────────────────────────────────────────┐
│  ReCall                            [mobile] │
├─────────────────────────────────────────────┤
│                                             │
│  ┌─────────────┐  ┌──────────────────────┐  │
│  │  🔥 3-day   │  │  📊 87% retention   │  │
│  │  streak     │  │  (last 30 days)      │  │
│  └─────────────┘  └──────────────────────┘  │
│                                             │
│  ┌───────────────────────────────────────┐  │
│  │  12 reviews due today                 │  │
│  │                                       │  │
│  │  [ ▶  Start Review Session ]          │  │
│  │                                       │  │
│  │  5 reviewed today                     │  │
│  └───────────────────────────────────────┘  │
│                                             │
│  ┌───────────────────────────────────────┐  │
│  │  Totals                               │  │
│  │  ┌──────────┐  ┌───────────────────┐  │  │
│  │  │ 24       │  │ 67               │   │  │
│  │  │ captures │  │ questions         │   │  │
│  │  └──────────┘  └───────────────────┘  │  │
│  └───────────────────────────────────────┘  │
│                                             │
│  Recent Captures                            │
│  ┌───────────────────────────────────────┐  │
│  │ WebSockets vs HTTP...         Today   │  │
│  │ 3 facts · 4 questions                 │  │
│  ├───────────────────────────────────────┤  │
│  │ Binary search algorithm...    Yesterday│ │
│  │ 2 facts · 3 questions                 │  │
│  ├───────────────────────────────────────┤  │
│  │ Docker networking basics...   Apr 16  │  │
│  │ 4 facts · 5 questions                 │  │
│  └───────────────────────────────────────┘  │
│                                             │
├─────────────────────────────────────────────┤
│  [Dashboard]  [Capture]  [Review]  [History]│
└─────────────────────────────────────────────┘
```

**Component tree:**
```
DashboardPage
├── PageHeader (title: "ReCall")
├── StatsGrid
│   ├── StatCard (streak_days, icon: Flame, label: "day streak")
│   └── StatCard (retention_rate, icon: TrendingUp, label: "retention")
├── ReviewCTA
│   ├── DueCount (due_today number, label: "reviews due today")
│   ├── StartReviewButton (link to /review) — only if due_today > 0
│   └── ReviewedToday (reviews_today, label: "reviewed today")
├── TotalsRow
│   ├── StatCard (total_captures, label: "captures")
│   └── StatCard (total_questions, label: "questions")
└── RecentCaptures
    └── CaptureListItem[] (last 5 from GET /api/captures?limit=5)
        ├── TruncatedText (raw_text, 120 chars)
        ├── MetaBadges (facts_count, created_at relative)
        └── → links to /history/[id]
```

**API calls:**
| When | Endpoint | Data used |
|---|---|---|
| Page load | `GET /api/stats/dashboard` | due_today, streak_days, retention_rate, reviews_today, total_captures, total_questions |
| Page load | `GET /api/captures?limit=5` | Recent captures for list |

---

### 4.3 Capture Page (`app/capture/page.tsx`)

**Purpose:** Quick knowledge capture — type what you learned, AI handles the rest.

**Wireframe:**
```
┌─────────────────────────────────────────────┐
│  Capture                                    │
├─────────────────────────────────────────────┤
│                                             │
│  What did you learn?                        │
│  ┌───────────────────────────────────────┐  │
│  │                                       │  │
│  │  (text area, 6 rows min, auto-grow)   │  │
│  │                                       │  │
│  │                                       │  │
│  └───────────────────────────────────────┘  │
│  42 / 50,000 characters                     │
│                                             │
│  Why does this matter to you? (optional)    │
│  ┌───────────────────────────────────────┐  │
│  │  (single line input)                  │  │
│  └───────────────────────────────────────┘  │
│                                             │
│  [ 🧠  Capture Knowledge ]                  │
│                                             │
│                                             │
│  ─ ─ ─ ─ AFTER SUBMIT ─ ─ ─ ─ ─            │
│                                             │
│  ┌───────────────────────────────────────┐  │
│  │  ✓ Captured successfully!             │  │
│  │                                       │  │
│  │  3 facts extracted                    │  │
│  │  4 questions generated                │  │
│  │                                       │  │
│  │  Processing time: 1.4s               │  │
│  │                                       │  │
│  │  [ Capture Another ]  [ Start Review ]│  │
│  └───────────────────────────────────────┘  │
│                                             │
├─────────────────────────────────────────────┤
│  [Dashboard]  [Capture]  [Review]  [History]│
└─────────────────────────────────────────────┘
```

**Component tree:**
```
CapturePage
├── PageHeader (title: "Capture")
├── CaptureForm
│   ├── TextArea (raw_text — label: "What did you learn?")
│   │   ├── auto-grow height
│   │   ├── character counter (X / 50,000)
│   │   └── min 6 rows
│   ├── Input (why_it_matters — label: "Why does this matter to you?", optional badge)
│   ├── SubmitButton (label: "Capture Knowledge", icon: Brain)
│   │   ├── disabled if raw_text is empty
│   │   └── shows spinner during submission
│   └── ShortInputWarning (if raw_text.length < 10 && raw_text.length > 0)
│       └── "That's very short. Add more detail for better extraction."
└── CaptureResult (shown after successful submit)
    ├── SuccessIcon (checkmark, green)
    ├── FactsCount ("3 facts extracted")
    ├── QuestionsCount ("4 questions generated")
    ├── ProcessingTime ("1.4s")
    ├── CaptureAnotherButton (clears form)
    └── StartReviewLink (link to /review)
```

**API calls:**
| When | Endpoint | Request | Response used |
|---|---|---|---|
| Form submit | `POST /api/captures` | `{ raw_text, source_type: "text", why_it_matters }` | capture_id, facts_count, questions_count, processing_time_ms, status |

---

### 4.4 Review Page (`app/review/page.tsx`)

**Purpose:** Spaced repetition review session — the core learning loop.

**Wireframe — Question Phase:**
```
┌─────────────────────────────────────────────┐
│  Review          3 / 12         [End Session]│
├─────────────────────────────────────────────┤
│  ████████░░░░░░░░░░░░░░░  25%               │
│                                             │
│  ┌───────────────────────────────────────┐  │
│  │  RECALL                               │  │
│  │                                       │  │
│  │  What is the key difference between   │  │
│  │  WebSockets and HTTP?                 │  │
│  │                                       │  │
│  │  💡 Hint: Think about connection      │  │
│  │  persistence                          │  │
│  └───────────────────────────────────────┘  │
│                                             │
│  Your answer                                │
│  ┌───────────────────────────────────────┐  │
│  │                                       │  │
│  │  (text area, 3 rows)                  │  │
│  │                                       │  │
│  └───────────────────────────────────────┘  │
│                                             │
│  [ ✓  Check Answer ]                        │
│                                             │
├─────────────────────────────────────────────┤
│  [Dashboard]  [Capture]  [Review]  [History]│
└─────────────────────────────────────────────┘
```

**Wireframe — Feedback Phase:**
```
┌─────────────────────────────────────────────┐
│  Review          3 / 12         [End Session]│
├─────────────────────────────────────────────┤
│  ████████░░░░░░░░░░░░░░░  25%               │
│                                             │
│  ┌───────────────────────────────────────┐  │
│  │  ✓ Correct                            │  │
│  │                                       │  │
│  │  Correct Answer:                      │  │
│  │  WebSockets maintain a persistent     │  │
│  │  TCP connection, while HTTP uses a    │  │
│  │  request-response model where each    │  │
│  │  exchange opens a new connection.     │  │
│  │                                       │  │
│  │  Feedback:                            │  │
│  │  Good explanation! You captured the   │  │
│  │  key distinction. You could also      │  │
│  │  mention that WebSockets allow        │  │
│  │  server-initiated push.              │  │
│  └───────────────────────────────────────┘  │
│                                             │
│  How difficult was this?                    │
│  ┌─────────────────────────────────────┐    │
│  │ [Again]  [Hard]  [*Good*]  [Easy]  │    │
│  │  forgot   tough   got it   obvious │    │
│  └─────────────────────────────────────┘    │
│                                             │
├─────────────────────────────────────────────┤
│  [Dashboard]  [Capture]  [Review]  [History]│
└─────────────────────────────────────────────┘
```

**Wireframe — Session Complete:**
```
┌─────────────────────────────────────────────┐
│  Review Complete                             │
├─────────────────────────────────────────────┤
│                                             │
│               🎉                             │
│         Session Complete!                    │
│                                             │
│  ┌───────────────────────────────────────┐  │
│  │  12 questions reviewed                │  │
│  │  in 4 min 32 sec                      │  │
│  │                                       │  │
│  │  Again:  2  ████                      │  │
│  │  Hard:   3  ██████                    │  │
│  │  Good:   5  ██████████                │  │
│  │  Easy:   2  ████                      │  │
│  │                                       │  │
│  │  Accuracy: 58% (Good + Easy)          │  │
│  └───────────────────────────────────────┘  │
│                                             │
│  [ Back to Dashboard ]                       │
│                                             │
├─────────────────────────────────────────────┤
│  [Dashboard]  [Capture]  [Review]  [History]│
└─────────────────────────────────────────────┘
```

**Component tree:**
```
ReviewPage
├── ReviewSession (main orchestrator — manages state machine)
│   ├── SessionHeader
│   │   ├── Title ("Review")
│   │   ├── Progress ("3 / 12")
│   │   └── EndSessionButton
│   │
│   ├── ProgressBar (currentIndex / totalQuestions)
│   │
│   ├── [phase === "question"] → QuestionCard
│   │   ├── QuestionTypeBadge (recall / cloze / explain / connect / apply)
│   │   ├── QuestionText
│   │   ├── MnemonicHint (if mnemonic_hint exists — collapsible)
│   │   ├── AnswerTextArea
│   │   └── CheckAnswerButton (disabled if answer empty)
│   │
│   ├── [phase === "evaluating"] → LoadingState
│   │   └── Spinner + "Evaluating your answer..."
│   │
│   ├── [phase === "feedback"] → FeedbackCard
│   │   ├── ScoreBadge (correct: green, partial: yellow, wrong: red)
│   │   ├── CorrectAnswer (the expected answer)
│   │   ├── AIFeedback (evaluation feedback text)
│   │   └── RatingButtons
│   │       ├── AgainButton (1, label: "Again", sublabel: "forgot", color: red)
│   │       ├── HardButton (2, label: "Hard", sublabel: "tough", color: orange)
│   │       ├── GoodButton (3, label: "Good", sublabel: "got it", color: green)
│   │       └── EasyButton (4, label: "Easy", sublabel: "obvious", color: blue)
│   │       └── SuggestedRating (ring highlight on suggested button)
│   │
│   ├── [phase === "rating"] → LoadingState
│   │   └── Brief spinner (< 500ms typically)
│   │
│   └── [phase === "complete"] → SessionSummary
│       ├── CelebrationIcon
│       ├── TotalReviewed
│       ├── Duration (calculated from sessionStats.startTime)
│       ├── RatingDistribution (horizontal bar chart per rating)
│       ├── AccuracyPercent ((good + easy) / total * 100)
│       └── BackToDashboardButton
│
└── [no due questions] → EmptyReviewState
    ├── Illustration (optional)
    ├── Message ("All caught up! Nothing to review right now.")
    ├── SubMessage ("Capture something new to generate review questions.")
    └── CaptureLink (link to /capture)
```

**API calls (sequential within session):**
| When | Endpoint | Request | Response used |
|---|---|---|---|
| Page load | `GET /api/reviews/due?limit=20` | — | questions[], total_due |
| User checks answer | `POST /api/reviews/evaluate` | `{ question_id, user_answer }` | correct_answer, score, feedback, suggested_rating |
| User clicks rating | `POST /api/reviews/rate` | `{ question_id, rating }` | next_due, interval_days, state |

---

### 4.5 History Page (`app/history/page.tsx`)

**Purpose:** Browse past captures and their extracted knowledge.

**Wireframe — List View:**
```
┌─────────────────────────────────────────────┐
│  History                                     │
├─────────────────────────────────────────────┤
│                                             │
│  ┌───────────────────────────────────────┐  │
│  │ WebSockets keep a persistent TCP      │  │
│  │ connection open unlike HTTP which...  │  │
│  │                                       │  │
│  │ 3 facts · 4 questions     Today 9:14a │  │
│  └───────────────────────────────────────┘  │
│                                             │
│  ┌───────────────────────────────────────┐  │
│  │ Binary search works by repeatedly     │  │
│  │ dividing the search interval in...    │  │
│  │                                       │  │
│  │ 2 facts · 3 questions   Yesterday 3pm │  │
│  └───────────────────────────────────────┘  │
│                                             │
│  ┌───────────────────────────────────────┐  │
│  │ Docker containers share the host OS   │  │
│  │ kernel unlike VMs which run their...  │  │
│  │                                       │  │
│  │ 4 facts · 5 questions     Apr 16 11am │  │
│  └───────────────────────────────────────┘  │
│                                             │
│  [ Load more ]                               │
│                                             │
├─────────────────────────────────────────────┤
│  [Dashboard]  [Capture]  [Review]  [History]│
└─────────────────────────────────────────────┘
```

**Wireframe — Detail View (`app/history/[id]/page.tsx`):**
```
┌─────────────────────────────────────────────┐
│  ← Back                                     │
├─────────────────────────────────────────────┤
│                                             │
│  Captured Today at 9:14 AM                  │
│                                             │
│  ┌───────────────────────────────────────┐  │
│  │  WebSockets keep a persistent TCP     │  │
│  │  connection open unlike HTTP which    │  │
│  │  is request-response. The server can  │  │
│  │  push data without the client asking. │  │
│  └───────────────────────────────────────┘  │
│                                             │
│  Why it matters:                            │
│  "Needed for real-time features in the      │
│   chat app I'm building"                    │
│                                             │
│  ── Extracted Facts (3) ──                  │
│                                             │
│  • WebSockets are persistent connections    │
│    [fact]                                   │
│  • HTTP uses request-response model         │
│    [comparison]                              │
│  • Server can push data without client      │
│    request (server push)                    │
│    [fact]                                   │
│                                             │
│  ── Generated Questions (4) ──              │
│                                             │
│  1. What is the key difference between      │
│     WebSockets and HTTP?                    │
│     Type: recall · Due: Tomorrow            │
│                                             │
│  2. Explain how server push works in        │
│     WebSockets.                              │
│     Type: explain · Due: Apr 20             │
│                                             │
│  3. Fill in: WebSockets maintain a ___      │
│     connection, while HTTP is ___.           │
│     Type: cloze · Due: Today                │
│                                             │
├─────────────────────────────────────────────┤
│  [Dashboard]  [Capture]  [Review]  [History]│
└─────────────────────────────────────────────┘
```

**Component tree:**
```
HistoryPage (list)
├── PageHeader (title: "History")
└── CaptureList
    ├── CaptureCard[] (for each capture)
    │   ├── TruncatedText (raw_text, max 150 chars)
    │   ├── MetaRow
    │   │   ├── FactsBadge ("3 facts")
    │   │   ├── QuestionsBadge ("4 questions")
    │   │   └── RelativeDate ("Today 9:14a")
    │   └── → links to /history/[id]
    └── LoadMoreButton (offset += limit)

CaptureDetailPage
├── BackButton (→ /history)
├── CaptureDate ("Captured Today at 9:14 AM")
├── RawTextBlock (full raw_text in card)
├── WhyItMatters (if exists — italic quote style)
├── FactsList
│   ├── SectionHeader ("Extracted Facts (3)")
│   └── FactItem[] 
│       ├── FactContent (text)
│       └── ContentTypeBadge (fact / concept / list / comparison / procedure)
└── QuestionsList
    ├── SectionHeader ("Generated Questions (4)")
    └── QuestionItem[]
        ├── QuestionText
        ├── QuestionTypeBadge
        └── DueDate ("Due: Tomorrow")
```

**API calls:**
| When | Endpoint | Request | Response used |
|---|---|---|---|
| Page load | `GET /api/captures?limit=20&offset=0` | — | Capture list items |
| Load more | `GET /api/captures?limit=20&offset=20` | — | Next page |
| Detail view | `GET /api/captures/{id}` | — | Full capture + facts + questions |

---

## 5. State Management

### 5.1 Review Session State Machine

```
States: loading → question → evaluating → feedback → rating → question (loop) → complete

type ReviewPhase = "loading" | "question" | "evaluating" | "feedback" | "rating" | "complete"

interface ReviewSessionState {
  questions: ReviewQuestion[]
  currentIndex: number
  phase: ReviewPhase
  currentAnswer: string
  evaluation: EvaluateResponse | null
  sessionStats: {
    total: number
    answered: number
    ratings: Record<1 | 2 | 3 | 4, number>
    startTime: Date
  }
}
```

**Transitions:**
```
page load                       → phase: "loading"
GET /due response (has items)   → phase: "question", currentIndex: 0
GET /due response (empty)       → render EmptyReviewState
user types in answer textarea   → update currentAnswer (no phase change)
user clicks "Check Answer"      → phase: "evaluating"
POST /evaluate response         → phase: "feedback", store evaluation
user clicks rating button       → phase: "rating"
POST /rate response + more Qs   → phase: "question", currentIndex++, clear answer
POST /rate response + no more   → phase: "complete"
user clicks "End Session"       → phase: "complete" (partial stats)
```

### 5.2 State Per Page

| Page | State approach | Persistence |
|---|---|---|
| Dashboard | Server state via `fetch` on mount. No client state needed beyond loading/error. | None — refetch on every visit |
| Capture | Form state via `useState`. CaptureResult in `useState`. | Lost on navigation (intentional — form should be clean) |
| Review | Session state via `useReducer` (complex state machine). | Lost on refresh. Store `currentIndex` in `sessionStorage` for resilience. |
| History | List in `useState` + pagination offset. | Lost on navigation. Could cache in `useState` during session. |

### 5.3 Loading / Empty / Error / Success States

| Page | Loading | Empty | Error | Success |
|---|---|---|---|---|
| **Dashboard** | Skeleton cards (pulsing gray blocks for stat cards + capture list) | "Welcome! Capture your first learning to get started." + CTA to /capture | "Couldn't load dashboard. Check your connection." + Retry button | Normal render |
| **Capture** | "Extracting knowledge..." + spinner on submit button. Form fields disabled. | N/A (always shows form) | "Failed to process. Your text was saved — we'll retry extraction." (for extraction_failed). Red toast for network errors. | Green success card with stats. Form clears. |
| **Review** | "Loading review questions..." + skeleton card | "All caught up! Nothing to review." + illustration + link to /capture | "Couldn't load questions. Try again." + Retry button. Mid-session: "Evaluation failed — rate this one yourself." | Auto-advance to next question. Session complete screen at end. |
| **History** | Skeleton list items (3 pulsing cards) | "No captures yet. Start by capturing something you learned!" + CTA to /capture | "Couldn't load captures." + Retry button | Normal render |
| **History Detail** | Skeleton blocks for text + facts + questions | N/A (404 if not found) | "Capture not found." + Back to History link | Normal render |

---

## 6. Responsive Design

### 6.1 Breakpoints

| Breakpoint | Tailwind class | Width | Layout changes |
|---|---|---|---|
| Mobile (default) | — | 0–639px | Bottom tab bar. Single column. Full-width cards. |
| Tablet | `sm:` | 640–767px | Same as mobile but wider cards with more padding. |
| Small desktop | `md:` | 768–1023px | Sidebar nav replaces tab bar. Content max-width 672px centered. |
| Desktop | `lg:` | 1024–1279px | Sidebar + content. Stats in 2x2 grid. |
| Wide | `xl:` | 1280px+ | Sidebar + content. Max-width 768px content. Generous whitespace. |

### 6.2 Navigation Switching

```
Mobile (< md):
  - Bottom tab bar (fixed, 64px height)
  - 4 tabs: Dashboard, Capture, Review, History
  - Active tab: filled icon + label + accent color
  - Review tab shows badge with due count
  - Page content has pb-16 to avoid overlap with tab bar

Desktop (≥ md):
  - Left sidebar (fixed, 240px width)
  - App logo at top
  - Vertical nav links with icons + labels
  - Active link: background highlight + accent color border-left
  - Review link shows badge with due count
  - Sidebar collapses to icon-only at md, full at lg
```

### 6.3 Key Layout Differences

| Element | Mobile | Desktop |
|---|---|---|
| Stats grid | 2 columns, stacked | 2x2 grid or 4-column row |
| Capture text area | Full width, 6 rows | Max-width 672px, 8 rows |
| Review card | Full width with padding | Centered card, max-width 640px |
| Rating buttons | Full width, stacked 2x2 | Horizontal row, equal width |
| History list | Full-width cards | Cards with max-width, more padding |
| Capture detail | Full width | Centered, max-width 768px, two-column for facts/questions at lg |

---

## 7. Navigation & Routing

### 7.1 Route Map

| Route | Page | Component | Data fetched |
|---|---|---|---|
| `/` | Dashboard | `app/page.tsx` | Stats + recent captures |
| `/capture` | Capture | `app/capture/page.tsx` | None (form only) |
| `/review` | Review Session | `app/review/page.tsx` | Due questions |
| `/history` | Capture History | `app/history/page.tsx` | Capture list |
| `/history/[id]` | Capture Detail | `app/history/[id]/page.tsx` | Single capture + facts + questions |

### 7.2 Navigation Behavior

- **Tab bar / sidebar:** Always visible. Active state on current route.
- **Back navigation:** History detail → History list (browser back or explicit back button).
- **Review session:** No navigation during active session (no accidental exits). "End Session" button is the explicit exit.
- **After capture success:** Two CTAs — "Capture Another" (stays on page) or "Start Review" (navigates to /review).
- **Deep linking:** All routes are directly accessible via URL. No auth gates.

### 7.3 Review Tab Badge

The Review tab in the navigation should show the due count as a small red badge. This requires fetching the due count in the layout. Options:

- **Option A (simple):** Fetch `GET /api/stats/dashboard` in the layout, pass `due_today` to nav. Refetch on interval (60s) or on page navigation.
- **Option B (prop drilling):** Dashboard fetches stats, passes via context to nav.
- **Recommended:** Option A — a lightweight stats fetch in the layout with a `SWR` or React Query pattern with `revalidateOnFocus: true`.

---

## 8. API Integration Map

### Component → Endpoint Mapping

```
┌──────────────────────────┬──────────────────────────────────┬─────────────┐
│ Component                │ Endpoint                         │ Trigger     │
├──────────────────────────┼──────────────────────────────────┼─────────────┤
│ MobileTabBar (badge)     │ GET /api/stats/dashboard         │ Layout load │
│ DashboardStats           │ GET /api/stats/dashboard         │ Page load   │
│ RecentCaptures           │ GET /api/captures?limit=5        │ Page load   │
│ CaptureForm              │ POST /api/captures               │ Form submit │
│ ReviewSession (init)     │ GET /api/reviews/due?limit=20    │ Page load   │
│ ReviewSession (evaluate) │ POST /api/reviews/evaluate       │ Check click │
│ ReviewSession (rate)     │ POST /api/reviews/rate           │ Rating click│
│ CaptureList              │ GET /api/captures?limit=20       │ Page load   │
│ CaptureList (paginate)   │ GET /api/captures?offset=N       │ Load more   │
│ CaptureDetail            │ GET /api/captures/{id}           │ Page load   │
└──────────────────────────┴──────────────────────────────────┴─────────────┘
```

### API Client (`lib/api.ts`)

```
api.ts exports:
  fetchDashboardStats()        → GET  /api/stats/dashboard
  createCapture(data)          → POST /api/captures
  listCaptures(limit, offset)  → GET  /api/captures
  getCaptureDetail(id)         → GET  /api/captures/{id}
  getDueQuestions(limit)       → GET  /api/reviews/due
  evaluateAnswer(data)         → POST /api/reviews/evaluate
  rateQuestion(data)           → POST /api/reviews/rate
```

All functions:
- Set `Content-Type: application/json`
- Use `NEXT_PUBLIC_API_URL` environment variable as base URL (default: `http://localhost:8000`)
- Throw typed errors on non-2xx responses
- Handle network errors with user-friendly messages

---

## 9. Accessibility

### 9.1 ARIA Labels & Roles

| Element | ARIA attribute | Value |
|---|---|---|
| Bottom tab bar | `role="navigation"`, `aria-label` | "Main navigation" |
| Active tab | `aria-current` | "page" |
| Review badge | `aria-label` | "12 reviews due" |
| Stat cards | `role="status"` | — |
| Capture text area | `aria-label` | "What did you learn? Enter the text you want to capture." |
| Why input | `aria-label` | "Why does this matter to you? Optional." |
| Submit button (loading) | `aria-disabled`, `aria-busy` | "true" |
| Progress bar | `role="progressbar"`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax` | current / 0 / total |
| Rating buttons group | `role="group"`, `aria-label` | "Rate your recall difficulty" |
| Rating button | `aria-label` | "Again — I forgot", "Hard — it was tough", etc. |
| Score badge (feedback) | `role="status"`, `aria-label` | "Your answer was correct" |
| Skeleton loaders | `aria-hidden` | "true" |
| Toast notifications | `role="alert"`, `aria-live` | "polite" |

### 9.2 Keyboard Navigation

| Context | Key | Action |
|---|---|---|
| Global | `Tab` | Move focus through interactive elements |
| Capture form | `Ctrl+Enter` / `Cmd+Enter` | Submit capture |
| Review — question | `Tab` → `Enter` | Focus answer box → submit (Check Answer) |
| Review — feedback | `1` / `2` / `3` / `4` | Quick-rate (Again/Hard/Good/Easy) |
| Review — feedback | `Tab` through buttons | Navigate rating buttons |
| Rating buttons | `Enter` / `Space` | Activate selected rating |
| History list | `Enter` on focused card | Open capture detail |
| History detail | `Escape` or `Backspace` | Go back to list |

### 9.3 Focus Management

- **After capture submit:** Focus moves to the success card (announced by screen reader).
- **After evaluate response:** Focus moves to score badge, then rating buttons get focus.
- **After rating click + next question:** Focus moves to question text, then to answer textarea.
- **Session complete:** Focus moves to summary heading.
- **Modal/toast dismissal:** Focus returns to triggering element.
- **Page navigation:** Focus moves to page heading (h1).

### 9.4 Color Contrast

All text meets WCAG 2.1 AA (4.5:1 ratio minimum). Rating button colors have sufficient contrast on both light and dark backgrounds. Score badges use both color AND text label (not color alone) to convey meaning.

---

## 10. Design Tokens

### 10.1 Color Palette

Using shadcn/ui's CSS variable system with Tailwind. All colors defined in `globals.css` as HSL variables.

**Semantic Colors:**

| Token | Light mode | Dark mode | Usage |
|---|---|---|---|
| `--background` | `0 0% 100%` (white) | `240 10% 3.9%` (near-black) | Page background |
| `--foreground` | `240 10% 3.9%` (near-black) | `0 0% 98%` (near-white) | Primary text |
| `--card` | `0 0% 100%` | `240 10% 3.9%` | Card surfaces |
| `--card-foreground` | `240 10% 3.9%` | `0 0% 98%` | Card text |
| `--primary` | `262 83% 58%` (purple) | `262 83% 58%` | Primary actions, active nav |
| `--primary-foreground` | `0 0% 100%` | `0 0% 100%` | Text on primary bg |
| `--muted` | `240 4.8% 95.9%` | `240 3.7% 15.9%` | Disabled, secondary surfaces |
| `--muted-foreground` | `240 3.8% 46.1%` | `240 5% 64.9%` | Secondary text, placeholders |
| `--destructive` | `0 84% 60%` (red) | `0 62.8% 30.6%` | Errors, "Again" rating |
| `--border` | `240 5.9% 90%` | `240 3.7% 15.9%` | Card borders, dividers |
| `--ring` | `262 83% 58%` | `262 83% 58%` | Focus rings |

**Rating Colors (semantic, not from shadcn defaults):**

| Rating | Color token | Hex (light) | Usage |
|---|---|---|---|
| Again (1) | `--rating-again` | `#EF4444` (red-500) | Again button bg |
| Hard (2) | `--rating-hard` | `#F97316` (orange-500) | Hard button bg |
| Good (3) | `--rating-good` | `#22C55E` (green-500) | Good button bg |
| Easy (4) | `--rating-easy` | `#3B82F6` (blue-500) | Easy button bg |

**Score Colors:**

| Score | Color | Usage |
|---|---|---|
| Correct | `text-green-600` / `bg-green-50` | Score badge in feedback |
| Partial | `text-yellow-600` / `bg-yellow-50` | Score badge in feedback |
| Wrong | `text-red-600` / `bg-red-50` | Score badge in feedback |

### 10.2 Typography Scale

Using system font stack via Tailwind defaults (`font-sans`). No custom fonts to minimize load time.

| Token | Tailwind class | Size | Weight | Usage |
|---|---|---|---|---|
| Display | `text-3xl font-bold` | 30px / 1.875rem | 700 | Session complete heading |
| Page title | `text-2xl font-semibold` | 24px / 1.5rem | 600 | Page headings (h1) |
| Section title | `text-lg font-semibold` | 18px / 1.125rem | 600 | "Extracted Facts", "Recent Captures" |
| Card title | `text-base font-medium` | 16px / 1rem | 500 | Question text, capture preview |
| Body | `text-sm` | 14px / 0.875rem | 400 | General content, feedback text |
| Caption | `text-xs` | 12px / 0.75rem | 400 | Dates, badges, character count |
| Stat number | `text-4xl font-bold` | 36px / 2.25rem | 700 | Dashboard stat values (12, 87%) |
| Stat label | `text-xs text-muted-foreground` | 12px / 0.75rem | 400 | "reviews due", "day streak" |

### 10.3 Spacing System

Using Tailwind's default 4px-based spacing scale:

| Token | Tailwind | Pixels | Usage |
|---|---|---|---|
| `space-1` | `p-1` / `gap-1` | 4px | Tight internal padding (badge content) |
| `space-2` | `p-2` / `gap-2` | 8px | Between icon and label, between badges |
| `space-3` | `p-3` / `gap-3` | 12px | Card internal padding (mobile) |
| `space-4` | `p-4` / `gap-4` | 16px | Card internal padding (desktop), section gaps |
| `space-6` | `p-6` / `gap-6` | 24px | Between sections, card padding (desktop) |
| `space-8` | `p-8` / `gap-8` | 32px | Page top padding, between major sections |

### 10.4 Border Radius

| Token | Tailwind | Value | Usage |
|---|---|---|---|
| Small | `rounded-md` | 6px | Buttons, inputs, badges |
| Medium | `rounded-lg` | 8px | Cards |
| Large | `rounded-xl` | 12px | Modal, large cards |
| Full | `rounded-full` | 9999px | Badges, avatars, pill shapes |

### 10.5 Shadows

| Token | Tailwind | Usage |
|---|---|---|
| None | `shadow-none` | Flat cards (bordered style) |
| Small | `shadow-sm` | Elevated cards, dropdown |
| Medium | `shadow-md` | Modals, floating elements |

**Design preference:** Use bordered cards (`border border-border`) rather than shadow-based elevation. Cleaner look, better on mobile, works well in both light and dark mode.

---

## 11. Interaction Patterns

### 11.1 Capture Flow Interactions

| User action | System response | Duration |
|---|---|---|
| Types in textarea | Character count updates live | Instant |
| Clears textarea | Submit button disables | Instant |
| Types < 10 chars | Warning appears below textarea (not blocking) | Instant |
| Clicks "Capture Knowledge" | Button shows spinner, form fields disable, text: "Extracting knowledge..." | 1–3 seconds |
| Capture succeeds | Success card slides in below form. Form clears. Toast: "Knowledge captured!" | Instant |
| Capture fails (network) | Red toast: "Failed to connect. Check your connection." Button re-enables. | Instant |
| Capture status: extraction_failed | Yellow card: "Saved but extraction failed. Will retry." | Instant |
| Capture status: no_facts | Yellow card: "No reviewable facts found. Try being more specific." | Instant |
| Clicks "Capture Another" | Success card disappears, textarea focuses | Instant |
| Clicks "Start Review" | Navigate to /review | Instant |

### 11.2 Review Flow Interactions

| User action | System response | Duration |
|---|---|---|
| Opens /review | "Loading review questions..." + skeleton card | 200–500ms |
| No questions due | Empty state with link to /capture | Instant |
| Sees question | Focus on answer textarea. Hint collapsed by default. | Instant |
| Taps hint toggle | Mnemonic hint expands/collapses (accordion) | 150ms animation |
| Types answer | "Check Answer" button enables | Instant |
| Clicks "Check Answer" | Button shows spinner. Answer textarea disables. "Evaluating..." | 500ms–2s |
| Evaluation arrives | Feedback card replaces question card (crossfade). Rating buttons appear. Suggested rating highlighted. | 200ms transition |
| Clicks a rating button | Button briefly pulses. Short spinner. POST /rate fires. | 200–500ms |
| Rating saved + more Qs | Slide transition to next question card. Answer clears. Focus on new question. | 300ms transition |
| Rating saved + last Q | Slide to session complete summary. | 300ms transition |
| Clicks "End Session" | Confirmation: "End session? You've reviewed X of Y questions." → OK / Cancel | Instant (dialog) |
| Confirms end session | Show summary with partial stats. | Instant |

### 11.3 Transitions & Animations

| Transition | Animation | Duration | Easing |
|---|---|---|---|
| Question → Feedback | Crossfade (opacity) | 200ms | ease-in-out |
| Feedback → Next Question | Slide left | 300ms | ease-out |
| Success card appear | Slide down + fade in | 200ms | ease-out |
| Skeleton → Content | Fade in | 150ms | ease-in |
| Toast appear | Slide in from top-right | 200ms | ease-out |
| Toast dismiss | Fade out | 150ms | ease-in |
| Tab bar active indicator | Background fill | 150ms | ease-in-out |

---

## 12. Edge Case Handling

| State | What user sees | What system does |
|---|---|---|
| Network offline | Toast: "You're offline. Changes won't be saved." | Disable submit buttons. Show stale data if cached. |
| API timeout (>10s) | "This is taking longer than usual..." below spinner | Wait up to 30s, then show error |
| Backend down (500) | "Something went wrong on our end. Try again." + Retry button | Log error. No retry auto. |
| Empty capture list (new user) | Dashboard: "Welcome! Capture your first learning." + CTA | Show onboarding-style empty state |
| Review mid-session refresh | Session restarts — re-fetches due questions | Questions already rated are excluded from new fetch. Some progress appears "lost" but ratings are persisted. |
| Extremely long answer | Textarea scrolls. No hard limit on answer length (backend limits at 10K chars). | Frontend trims to 10K before submit |
| Rapid rating clicks | Debounce: first click wins, subsequent ignored until POST completes | Button group disables during POST /rate |
| Concurrent tab captures | Each tab operates independently. No real-time sync between tabs. | Acceptable for single-user MVP |
| 0 facts extracted | Yellow card: "No reviewable facts found. Try adding more detail." | capture_id still returned. Capture is stored. |
| Review due count badge stale | Badge updates on every page navigation + 60s interval | Fetch stats in layout, revalidate on focus |

---

## 13. Component Inventory

### Shared Components (used across pages)

| Component | Description | Props |
|---|---|---|
| `PageHeader` | Page title with consistent sizing | `title: string` |
| `StatCard` | Stat value + label in a bordered card | `value: number \| string, label: string, icon?: LucideIcon` |
| `LoadingSpinner` | Centered spinner with optional message | `message?: string` |
| `SkeletonCard` | Pulsing gray placeholder card | `lines?: number` |
| `EmptyState` | Illustration + message + CTA | `message: string, cta?: { label: string, href: string }` |
| `ErrorState` | Error message + retry button | `message: string, onRetry: () => void` |
| `Badge` | Small colored label | `variant: "default" \| "secondary" \| "outline", children` |
| `Toast` | Non-blocking notification (success/error/warning) | Via shadcn/ui toast system |

### Navigation Components

| Component | Description | Where used |
|---|---|---|
| `MobileTabBar` | Fixed bottom tab bar with 4 tabs + active state + badge | Layout (< md) |
| `DesktopSidebar` | Fixed left sidebar with logo + nav links + badge | Layout (≥ md) |
| `NavLink` | Single nav item with icon, label, active state | TabBar, Sidebar |

### Capture Components

| Component | Description | Where used |
|---|---|---|
| `CaptureForm` | Textarea + why input + submit button + validation | /capture |
| `CaptureResult` | Success/warning card after capture | /capture |
| `CaptureCard` | Compact capture preview for lists | Dashboard, /history |

### Review Components

| Component | Description | Where used |
|---|---|---|
| `ReviewSession` | State machine orchestrator | /review |
| `SessionHeader` | Title + progress counter + end session | /review |
| `ProgressBar` | Horizontal fill bar showing review progress | /review |
| `QuestionCard` | Question display + type badge + hint toggle | /review |
| `QuestionTypeBadge` | Colored badge: recall, cloze, explain, connect, apply | /review, /history detail |
| `AnswerTextArea` | Text input for user's answer | /review |
| `FeedbackCard` | Correct answer + score + AI feedback | /review |
| `ScoreBadge` | Correct (green) / Partial (yellow) / Wrong (red) | /review |
| `RatingButtons` | 4-button group: Again, Hard, Good, Easy | /review |
| `SessionSummary` | End-of-session stats + rating distribution | /review |
| `EmptyReviewState` | "All caught up!" message | /review |

### History Components

| Component | Description | Where used |
|---|---|---|
| `CaptureList` | Paginated list of capture cards | /history |
| `CaptureDetailView` | Full capture + facts + questions | /history/[id] |
| `FactItem` | Single extracted fact with type badge | /history/[id] |
| `QuestionItem` | Single question with type + due date | /history/[id] |
| `LoadMoreButton` | "Load more" pagination trigger | /history |

---

## 14. File Structure (Frontend)

```
frontend/
├── app/
│   ├── layout.tsx                 # Root layout: sidebar/tabbar + main content
│   ├── page.tsx                   # Dashboard page
│   ├── capture/
│   │   └── page.tsx               # Capture page
│   ├── review/
│   │   └── page.tsx               # Review session page
│   ├── history/
│   │   ├── page.tsx               # History list page
│   │   └── [id]/
│   │       └── page.tsx           # Capture detail page
│   └── globals.css                # Tailwind + CSS variables (design tokens)
│
├── components/
│   ├── layout/
│   │   ├── MobileTabBar.tsx
│   │   ├── DesktopSidebar.tsx
│   │   └── NavLink.tsx
│   ├── dashboard/
│   │   ├── StatsGrid.tsx
│   │   ├── StatCard.tsx
│   │   ├── ReviewCTA.tsx
│   │   └── RecentCaptures.tsx
│   ├── capture/
│   │   ├── CaptureForm.tsx
│   │   └── CaptureResult.tsx
│   ├── review/
│   │   ├── ReviewSession.tsx      # State machine orchestrator
│   │   ├── SessionHeader.tsx
│   │   ├── ProgressBar.tsx
│   │   ├── QuestionCard.tsx
│   │   ├── FeedbackCard.tsx
│   │   ├── RatingButtons.tsx
│   │   ├── SessionSummary.tsx
│   │   └── EmptyReviewState.tsx
│   ├── history/
│   │   ├── CaptureCard.tsx
│   │   ├── CaptureList.tsx
│   │   ├── CaptureDetailView.tsx
│   │   ├── FactItem.tsx
│   │   └── QuestionItem.tsx
│   └── shared/
│       ├── PageHeader.tsx
│       ├── LoadingSpinner.tsx
│       ├── SkeletonCard.tsx
│       ├── EmptyState.tsx
│       ├── ErrorState.tsx
│       └── Badge.tsx              # (or use shadcn Badge directly)
│
├── lib/
│   ├── api.ts                     # Backend API client (fetch wrappers)
│   └── utils.ts                   # Relative date formatting, cn() helper
│
├── hooks/
│   ├── useReviewSession.ts        # useReducer-based review state machine
│   └── useDashboardStats.ts       # Stats fetch + polling hook
│
├── types/
│   └── api.ts                     # TypeScript interfaces matching backend models
│
├── tailwind.config.ts
├── next.config.js
├── package.json
└── tsconfig.json
```

---

## 15. UX Recommendations

### Critical Decisions

1. **Bottom tab bar on mobile (not hamburger menu).** All 4 pages must be one tap away. Hamburger menus hide navigation and reduce engagement. The review tab badge drives daily usage.

2. **Review session is linear, not card-swipe.** Scroll-based Q&A with "Check Answer" button is more accessible and works identically on mobile and desktop. Swipe gestures are fragile and exclude keyboard users.

3. **Suggested rating is highlighted, not auto-selected.** The AI suggests a rating, but the user always has final control. This builds trust and produces better FSRS training data.

4. **No confirmation dialog on capture submit.** Capture should feel instant and low-friction. The success card provides confirmation. "Capture Another" makes rapid captures easy.

5. **Form clears after successful capture.** Don't make the user manually clear the form. But show the success result so they know it worked.

6. **Review progress persists per session, not per page load.** If the user refreshes mid-review, they restart with whatever is still due. Already-rated questions won't reappear. This is acceptable for MVP — no server-side session needed.

7. **No dark mode toggle in MVP.** Ship with system-preference detection (`prefers-color-scheme`). The CSS variables support dark mode inherently via shadcn. No manual toggle needed initially.

8. **Keyboard shortcuts in review (1/2/3/4 for ratings).** Power users will review dozens of items. Number keys for ratings save significant time. Show keyboard hint on desktop.
