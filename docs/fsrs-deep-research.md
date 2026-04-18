# FSRS (Free Spaced Repetition Scheduler) — Deep Implementation Research

> **Sources researched**: py-fsrs (GitHub), ts-fsrs (GitHub), fsrs4anki (GitHub), awesome-fsrs wiki (The Algorithm), Wikipedia (SuperMemo)
> **Date**: 2026-04-17
> **Purpose**: Implementation reference for voice-first memory assistant

---

## 1. FSRS Algorithm Details

### 1.1 What is FSRS?

FSRS (Free Spaced Repetition Scheduler) is a modern, open-source spaced repetition algorithm created by **Jarrett Ye (L-M-Sherlock)** at MaiMemo Inc. It originated from the **DHP model** (Difficulty, Half-life, Probability), which is a variant of the **DSR model** (Difficulty, Stability, Retrievability). It is backed by two academic papers:

- "A Stochastic Shortest Path Algorithm for Optimizing Spaced Repetition Scheduling" (ACM KDD 2022)
- "Optimizing Spaced Repetition Schedule by Capturing the Dynamics of Memory" (IEEE TKDE 2023)

The current version is **FSRS-6** (21 parameters). It is now natively integrated into **Anki 23.10+**.

### 1.2 Core Concepts — The DSR Model

FSRS models memory with three variables:

| Symbol | Name | Meaning |
|--------|------|---------|
| **D** | Difficulty | How hard the card is to remember. Range: `[1, 10]` |
| **S** | Stability | The interval (in days) at which retrievability = 90%. Higher = stronger memory |
| **R** | Retrievability | Current probability of successfully recalling the card. Range: `[0, 1]` |

**Key insight**: Stability is defined as the number of days until R drops to 90%. So when `t = S`, `R = 0.9`.

### 1.3 The Forgetting Curve

FSRS uses a **power-law forgetting curve**, not exponential (which Ebbinghaus originally proposed):

#### FSRS-6 (current):
```
R(t, S) = (1 + factor × t/S)^(-w[20])
```
where `factor = (0.9^(1/w[20]) - 1)` to ensure `R(S, S) = 0.9`.

The decay parameter `w[20]` is **trainable** in FSRS-6 (new in this version).

#### FSRS-4.5 / v4 (for reference):
```
R(t, S) = (1 + FACTOR × t/S)^DECAY
```
- FSRS v4: `DECAY = -1`, `FACTOR = 1/9`
- FSRS-4.5: `DECAY = -0.5`, `FACTOR = 19/81`

The power-law curve drops sharply before S and flattens after S, which better matches empirical data than exponential decay.

### 1.4 Rating Scale (1–4)

| Rating | Value | Meaning |
|--------|-------|---------|
| `Again` | 1 | Forgot the card |
| `Hard` | 2 | Remembered with serious difficulty |
| `Good` | 3 | Remembered after hesitation |
| `Easy` | 4 | Remembered easily |

### 1.5 FSRS-6 Formula (Current Version — 21 Parameters)

**Default parameters:**
```
[0.212, 1.2931, 2.3065, 8.2956, 6.4133, 0.8334, 3.0194, 0.001,
 1.8722, 0.1666, 0.796, 1.4835, 0.0614, 0.2629, 1.6483, 0.6014,
 1.8729, 0.5425, 0.0912, 0.0658, 0.1542]
```

#### Initial Stability (first review):
```
S₀(G) = w[G-1]
```
- `S₀(Again) = w[0] = 0.212` days
- `S₀(Easy) = w[3] = 8.2956` days

#### Initial Difficulty (first review):
```
D₀(G) = w[4] - e^(w[5] × (G - 1)) + 1
```
where `w[4] = D₀(Again)`.

#### Difficulty Update (after review):
```
ΔD(G) = -w[6] × (G - 3)
D' = D + ΔD × (10 - D) / 9       # Linear damping
D'' = w[7] × D₀(4) + (1 - w[7]) × D'  # Mean reversion toward D₀(Easy)
```
Mean reversion prevents "difficulty hell" (equivalent to Anki's "ease hell").

#### Stability After Successful Recall:
```
S'_r(D, S, R, G) = S × (e^(w[8]) × (11 - D) × S^(-w[9]) × (e^(w[10] × (1 - R)) - 1) × w[15]^(if G=2) × w[16]^(if G=4) + 1)
```

Key properties of `S_Inc = S'_r / S` (stability increase factor):
1. Higher D → smaller S_Inc (hard material grows slower)
2. Higher S → smaller S_Inc (strong memories are harder to strengthen)
3. Lower R → larger S_Inc (**spacing effect** — reviewing later = bigger boost)
4. S_Inc ≥ 1 always (successful recall never decreases stability)

#### Stability After Forgetting (Lapse):
```
S'_f(D, S, R) = w[11] × D^(-w[12]) × ((S + 1)^w[13] - 1) × e^(w[14] × (1 - R))
```

#### Same-Day Review Stability (new in FSRS-6):
```
S'(S, G) = S × e^(w[17] × (G - 3 + w[18]) × S^(-w[19]))
```
S increases faster when small, slower when large (converges).

#### Interval Calculation:
Solve `R(t, S) = desired_retention` for `t`:
```
I(r, S) = (S / factor) × (r^(1/DECAY) - 1)
```
For FSRS v4 simplified: `I(r, S) = 9 × S × (1/r - 1)`

### 1.6 Card States

```
┌──────────┐   Good/Easy    ┌──────────┐
│ Learning │ ──────────────► │  Review  │
│  (new)   │  (graduated)   │          │
└──────────┘                └────┬─────┘
      ▲                         │ Again (lapse)
      │                         ▼
      │                   ┌──────────────┐
      │                   │  Relearning  │
      │                   └──────┬───────┘
      │                          │ Good/Easy
      │                          │
      └──────────────────────────┘
```

| State | Value | Description |
|-------|-------|-------------|
| `Learning` | 1 | New card being studied for the first time |
| `Review` | 2 | Graduated card in long-term review |
| `Relearning` | 3 | Lapsed card (was Review, then rated Again) |

---

## 2. py-fsrs Library (Python)

### 2.1 Overview

| Property | Value |
|----------|-------|
| **Package** | `fsrs` on PyPI |
| **Version** | v6.3.1 (March 2026) |
| **Algorithm** | FSRS-6 (21 parameters) |
| **Stars** | 413 |
| **License** | MIT |
| **Language** | Python 100% |
| **Releases** | 36 |
| **Contributors** | 12 (lead: joshdavham, ishiko732, L-M-Sherlock) |
| **Dependencies** | Minimal (core has none; optimizer requires PyTorch) |

### 2.2 Installation

```bash
pip install fsrs              # Core scheduler
pip install "fsrs[optimizer]"  # + optimizer (adds PyTorch dependency)
```

### 2.3 Core API Surface

#### Classes:
- `Scheduler` — Main scheduler, handles review logic
- `Card` — Represents a flashcard with memory state
- `ReviewLog` — Records a single review event
- `Rating` — Enum: `Again(1)`, `Hard(2)`, `Good(3)`, `Easy(4)`
- `State` — Enum: `Learning(1)`, `Review(2)`, `Relearning(3)`
- `Optimizer` — (optional) Trains custom parameters from review logs

#### Key Methods:
```python
# Scheduler
scheduler = Scheduler(parameters, desired_retention, learning_steps, 
                      relearning_steps, maximum_interval, enable_fuzzing)
card, review_log = scheduler.review_card(card, rating)
retrievability = scheduler.get_card_retrievability(card)
rescheduled_card = scheduler.reschedule_card(card, review_logs)

# All objects support JSON serialization
json_str = obj.to_json()
obj = ClassName.from_json(json_str)

# Optimizer
optimizer = Optimizer(review_logs)
optimal_parameters = optimizer.compute_optimal_parameters()
optimal_retention = optimizer.compute_optimal_retention(optimal_parameters)
```

### 2.4 Full Review Cycle Example

```python
from fsrs import Scheduler, Card, Rating, ReviewLog
from datetime import datetime, timezone, timedelta

# 1. Initialize scheduler with defaults
scheduler = Scheduler()

# 2. Create a new card (due immediately)
card = Card()

# 3. First review — user remembers with hesitation
card, log1 = scheduler.review_card(card, Rating.Good)
print(f"Next due: {card.due}")  # ~10 minutes later (learning step)

# 4. Second review — user remembers easily  
card, log2 = scheduler.review_card(card, Rating.Good)
print(f"Next due: {card.due}")  # ~1 day later (graduated to Review)

# 5. Third review — user forgot
card, log3 = scheduler.review_card(card, Rating.Again)
print(f"State: {card.state}")   # Relearning
print(f"Next due: {card.due}")  # ~10 minutes later (relearning step)

# 6. Check current retrievability
r = scheduler.get_card_retrievability(card)
print(f"Probability of recall: {r}")

# 7. Serialize for storage
card_json = card.to_json()
log_json = log1.to_json()
# Deserialize
card_restored = Card.from_json(card_json)
```

### 2.5 Custom Parameters

```python
from datetime import timedelta

scheduler = Scheduler(
    parameters=(0.212, 1.2931, 2.3065, 8.2956, ...),  # 21 weights
    desired_retention=0.9,        # Target 90% recall
    learning_steps=(timedelta(minutes=1), timedelta(minutes=10)),
    relearning_steps=(timedelta(minutes=10),),
    maximum_interval=36500,       # ~100 years cap
    enable_fuzzing=True           # Add randomness to intervals
)
```

### 2.6 Optimizer Usage

```python
from fsrs import ReviewLog, Optimizer, Scheduler

# Collect review logs from your database
review_logs = [log1, log2, log3, ...]

optimizer = Optimizer(review_logs)

# Train optimal parameters from user's history
optimal_params = optimizer.compute_optimal_parameters()

# Find optimal retention rate (minimizes total review workload)
optimal_retention = optimizer.compute_optimal_retention(optimal_params)

# Create personalized scheduler
scheduler = Scheduler(optimal_params, optimal_retention)

# Reschedule existing cards with new parameters
for card in all_cards:
    card_logs = get_logs_for_card(card)
    card = scheduler.reschedule_card(card, card_logs)
```

> **Note**: Computed parameters may differ slightly from Anki's results because py-fsrs and the Rust-based Anki implementation update at different times.

### 2.7 Timezone Handling

**py-fsrs uses UTC only.** All datetimes must use UTC timezone. Custom datetimes are supported but must be UTC.

### 2.8 Gotchas & Limitations

1. **UTC only** — No timezone-aware scheduling; convert at application layer
2. **Optimizer requires PyTorch** — Heavy dependency (~2GB) for parameter training
3. **No built-in persistence** — You manage DB storage via JSON serialization
4. **New cards are due immediately** upon creation
5. **learning_steps=()** disables the learning phase (cards go straight to Review)
6. **Parameters may differ from Anki** — Slight implementation differences from the official Rust version

---

## 3. ts-fsrs Library (TypeScript)

### 3.1 Overview

| Property | Value |
|----------|-------|
| **Package** | `ts-fsrs` on npm |
| **Version** | FSRS-6 compatible |
| **Stars** | 634 |
| **License** | MIT |
| **Language** | TypeScript 80%, Rust 12%, JS 5% |
| **Releases** | 78 |
| **Contributors** | 20 (lead: ishiko732) |
| **Node.js** | ≥ 20.0.0 required |
| **Monorepo** | Yes (Turborepo) |

### 3.2 Packages

| Package | Purpose |
|---------|---------|
| `ts-fsrs` | Core scheduler for review flows |
| `@open-spaced-repetition/binding` | Optimizer for parameter training + CSV conversion (Rust/WASM) |

### 3.3 Installation

```bash
npm install ts-fsrs                        # Core
npm install @open-spaced-repetition/binding  # Optimizer (Rust WASM)
```

### 3.4 Core API Surface

```typescript
// Factory functions
createEmptyCard(): Card
fsrs(params?: Partial<FSRSParameters>): FSRS
generatorParameters(params?: Partial<FSRSParameters>): FSRSParameters

// FSRS class methods
scheduler.repeat(card, now): RecordLog     // Preview ALL 4 outcomes
scheduler.next(card, now, rating): RecordLogItem  // Apply specific rating
scheduler.get_retrievability(card, now): number
scheduler.next_state(state, elapsedDays, rating): FSRSState
scheduler.next_interval(stability, elapsedDays): number
scheduler.rollback(card, log): Card
scheduler.forget(card, now, resetCount?): void
scheduler.reschedule(card, reviews, options?): void

// Utility
forgetting_curve(elapsed_days, stability, decay): number

// Types
Rating: { Again: 1, Hard: 2, Good: 3, Easy: 4 }
State: { New: 0, Learning: 1, Review: 2, Relearning: 3 }
```

> **Note**: ts-fsrs has `State.New = 0` while py-fsrs starts at `State.Learning = 1`. ts-fsrs includes an explicit `New` state.

### 3.5 Full Review Cycle Example

```typescript
import { createEmptyCard, fsrs, Rating } from 'ts-fsrs'

// 1. Initialize
const scheduler = fsrs()
const card = createEmptyCard()

// 2. Preview all 4 outcomes before user answers
const preview = scheduler.repeat(card, new Date())
console.log(preview[Rating.Good].card)   // What happens if "Good"
console.log(preview[Rating.Again].card)  // What happens if "Again"

// 3. User rates "Good" — apply it
const result = scheduler.next(card, new Date(), Rating.Good)
console.log(result.card)   // Updated card state
console.log(result.log)    // ReviewLog record

// 4. Check retrievability
const r = scheduler.get_retrievability(result.card, new Date(), false)

// 5. Custom afterHandler for DB mapping
const saved = scheduler.next(card, new Date(), Rating.Good, ({ card, log }) => ({
  card: {
    ...card,
    due: card.due.getTime(),           // Convert to timestamp
    last_review: card.last_review?.getTime() ?? null,
  },
  log: {
    ...log,
    due: log.due.getTime(),
    review: log.review.getTime(),
  },
}))
```

### 3.6 Custom Parameters

```typescript
import { fsrs } from 'ts-fsrs'

const scheduler = fsrs({
  request_retention: 0.9,      // = desired_retention in py-fsrs
  maximum_interval: 36500,
  enable_fuzz: true,           // = enable_fuzzing in py-fsrs
  enable_short_term: true,
  learning_steps: ['1m', '10m'],
  relearning_steps: ['10m'],
})
```

### 3.7 Low-Level State API

```typescript
import { fsrs, Rating, type FSRSState } from 'ts-fsrs'

const scheduler = fsrs({ enable_fuzz: false })

// Work directly with memory states (no Card object needed)
const memoryState: FSRSState = {
  stability: 3.2,
  difficulty: 5.6,
}

const nextState = scheduler.next_state(memoryState, 12, Rating.Good)
const nextInterval = scheduler.next_interval(nextState.stability, 12)
```

This is useful for simulations, analytics, or custom scheduling without the full Card abstraction.

### 3.8 API Comparison: py-fsrs vs ts-fsrs

| Feature | py-fsrs | ts-fsrs |
|---------|---------|---------|
| **Create card** | `Card()` | `createEmptyCard()` |
| **Create scheduler** | `Scheduler()` | `fsrs()` |
| **Review** | `scheduler.review_card(card, rating)` → `(card, log)` | `scheduler.next(card, date, rating)` → `{card, log}` |
| **Preview all ratings** | N/A (call review_card per rating) | `scheduler.repeat(card, date)` → `{1: {...}, 2: {...}, 3: {...}, 4: {...}}` |
| **Retrievability** | `scheduler.get_card_retrievability(card)` | `scheduler.get_retrievability(card, date)` |
| **Retention param** | `desired_retention` | `request_retention` |
| **Fuzz param** | `enable_fuzzing` | `enable_fuzz` |
| **Card states** | `Learning=1, Review=2, Relearning=3` | `New=0, Learning=1, Review=2, Relearning=3` |
| **Serialization** | `.to_json()` / `.from_json()` | Native JS objects (spread/JSON.stringify) |
| **Low-level state** | N/A | `next_state()`, `next_interval()` |
| **Optimizer** | `Optimizer` class (PyTorch) | `@open-spaced-repetition/binding` (Rust/WASM) |
| **Learning steps** | `timedelta` tuples | String format `'1m'`, `'10m'` |
| **History helpers** | `reschedule_card()` | `rollback()`, `forget()`, `reschedule()` |

### 3.9 Production Readiness

**ts-fsrs is production-ready:**
- 634 stars, 20 contributors, 78 releases
- Active development (commits daily as of April 2026)
- Monorepo with Turborepo, Vitest, Biome
- TypeDoc API documentation
- CodeCov coverage tracking
- Full-stack demo available (ts-fsrs-demo)
- Supports ESM, CommonJS, UMD
- Works in browsers (WASM binding for optimizer)
- Used by multiple production apps (Anki Search Stats Extended, spaced, etc.)

---

## 4. Implementation Considerations

### 4.1 Database Schema — Card Storage

Minimum columns per card for FSRS state:

```sql
CREATE TABLE cards (
    id              UUID PRIMARY KEY,
    -- Content
    front           TEXT NOT NULL,
    back            TEXT NOT NULL,
    
    -- FSRS Memory State (critical)
    due             TIMESTAMP WITH TIME ZONE NOT NULL,  -- When card is next due
    stability       FLOAT NOT NULL DEFAULT 0,           -- S value
    difficulty      FLOAT NOT NULL DEFAULT 0,           -- D value  
    elapsed_days    INTEGER NOT NULL DEFAULT 0,         -- Days since last review
    scheduled_days  INTEGER NOT NULL DEFAULT 0,         -- Days until due
    reps            INTEGER NOT NULL DEFAULT 0,         -- Total review count
    lapses          INTEGER NOT NULL DEFAULT 0,         -- Total lapse count
    state           SMALLINT NOT NULL DEFAULT 0,        -- 0=New, 1=Learning, 2=Review, 3=Relearning
    last_review     TIMESTAMP WITH TIME ZONE,           -- Last review datetime
    
    -- Application metadata
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    user_id         UUID REFERENCES users(id),
    deck_id         UUID REFERENCES decks(id)
);

-- Index for "due today" query
CREATE INDEX idx_cards_due ON cards (user_id, state, due);
```

Review log storage:

```sql
CREATE TABLE review_logs (
    id              UUID PRIMARY KEY,
    card_id         UUID REFERENCES cards(id),
    
    -- Review data
    rating          SMALLINT NOT NULL,           -- 1=Again, 2=Hard, 3=Good, 4=Easy
    state           SMALLINT NOT NULL,           -- Card state at time of review
    due             TIMESTAMP WITH TIME ZONE,    -- When the card was due
    stability       FLOAT NOT NULL,              -- S before review
    difficulty      FLOAT NOT NULL,              -- D before review
    elapsed_days    INTEGER NOT NULL,            -- Days since previous review
    last_elapsed_days INTEGER NOT NULL,          -- Previous elapsed_days
    scheduled_days  INTEGER NOT NULL,            -- Scheduled interval
    review          TIMESTAMP WITH TIME ZONE NOT NULL,  -- When review happened
    
    -- Metadata
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_review_logs_card ON review_logs (card_id, review);
```

### 4.2 "Due Today" Queue — Efficient Query

```sql
-- Cards due for review right now
SELECT * FROM cards 
WHERE user_id = :user_id 
  AND due <= NOW()
ORDER BY 
  CASE state 
    WHEN 1 THEN 0  -- Learning first (short intervals)
    WHEN 3 THEN 1  -- Relearning second
    WHEN 2 THEN 2  -- Review last
  END,
  due ASC           -- Oldest due first within each group
LIMIT 50;
```

For a voice-first assistant, you may want a simpler priority:
```sql
-- Overdue cards first, then by staleness
SELECT *, 
  EXTRACT(EPOCH FROM (NOW() - due)) / 86400.0 AS overdue_days
FROM cards 
WHERE user_id = :user_id AND due <= NOW()
ORDER BY overdue_days DESC
LIMIT 10;
```

### 4.3 Timezone Handling

**py-fsrs is UTC-only.** Strategy for a voice assistant:

1. **Store everything in UTC** in the database
2. **Convert at the application boundary** when presenting "today's reviews" to the user
3. **Define "day boundary"** based on user's local timezone:
   ```python
   from datetime import datetime, timezone, timedelta
   import pytz
   
   user_tz = pytz.timezone("America/New_York")
   now_local = datetime.now(user_tz)
   
   # Start of today in user's timezone, converted to UTC
   start_of_day_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
   start_of_day_utc = start_of_day_local.astimezone(timezone.utc)
   
   # Query cards due before end of today
   end_of_day_utc = start_of_day_utc + timedelta(days=1)
   ```

4. **For ts-fsrs**: Same approach — pass `new Date()` (always UTC internally in JS)

### 4.4 Parameter Tuning

#### desired_retention (most impactful setting):

| Value | Effect | Use Case |
|-------|--------|----------|
| 0.95 | Very frequent reviews, high recall | Medical terms, safety-critical |
| 0.90 | Default, balanced | General learning |
| 0.85 | Fewer reviews, some forgetting | Casual learning, large decks |
| 0.80 | Minimal reviews | Low-priority material |

**Rule of thumb**: Each 5% increase in retention roughly doubles the review workload.

#### Optimizer for custom weights:

The biggest gain comes from **training custom parameters** on a user's review history:

```python
# After collecting ~200+ reviews from a user
from fsrs import Optimizer

optimizer = Optimizer(user_review_logs)
custom_params = optimizer.compute_optimal_parameters()  # 21 weights
optimal_retention = optimizer.compute_optimal_retention(custom_params)

# Now scheduler is personalized to this user's memory patterns
scheduler = Scheduler(custom_params, optimal_retention)
```

**When to retrain**: After every ~500 new reviews, or weekly for active users.

#### Default vs Custom Parameters:

| Scenario | Recommendation |
|----------|---------------|
| New user, < 100 reviews | Use **default parameters** |
| User with 100–500 reviews | Can start training, but defaults are fine |
| User with 500+ reviews | **Train custom parameters** for meaningful improvement |
| Cross-user average | Default parameters work well as a baseline |

### 4.5 Learning Steps Configuration

For a **voice-first** assistant where sessions may be less frequent:

```python
# Standard (good for app-based review)
Scheduler(
    learning_steps=(timedelta(minutes=1), timedelta(minutes=10)),
    relearning_steps=(timedelta(minutes=10),),
)

# Voice-optimized (user may not review again for hours)
Scheduler(
    learning_steps=(timedelta(minutes=10), timedelta(hours=1)),
    relearning_steps=(timedelta(minutes=30),),
)

# No learning steps (skip straight to FSRS algorithm scheduling)
Scheduler(
    learning_steps=(),
    relearning_steps=(),
)
```

---

## 5. SM-2 vs FSRS Comparison

### 5.1 Algorithm Overview

| Feature | SM-2 (SuperMemo 2, 1987) | FSRS-6 (2024) |
|---------|--------------------------|---------------|
| **Author** | Piotr Woźniak | Jarrett Ye (L-M-Sherlock) |
| **Parameters** | 0 (hardcoded formula) | 21 (trainable weights) |
| **Rating scale** | 0–5 (6 levels) | 1–4 (4 levels) |
| **Memory model** | Easiness Factor (EF) | Stability (S) + Difficulty (D) + Retrievability (R) |
| **Forgetting curve** | None (heuristic intervals) | Power-law decay: `R(t,S) = (1 + factor × t/S)^(-decay)` |
| **Interval formula** | `I = round(I × EF)` | Derived from forgetting curve + desired retention |
| **Personalization** | None (one formula for all) | Per-user parameter optimization via ML |
| **Overdue handling** | Linear increase | Converges to upper limit (better for irregular schedules) |
| **"Ease hell"** | Common problem (EF gets stuck low) | Mean reversion prevents difficulty spiral |
| **Short-term steps** | Not built in | Learning/relearning steps built in |
| **Accuracy** | Baseline | ~30% better at predicting recall (per FSRS benchmarks) |

### 5.2 SM-2 Algorithm Summary

SM-2 tracks three variables per card:
- **n**: Repetition number (successful recalls in a row)
- **EF**: Easiness Factor (starts at 2.5, minimum 1.3)
- **I**: Inter-repetition interval in days

```
if grade >= 3 (correct):
    if n == 0: I = 1
    elif n == 1: I = 6
    else: I = round(I × EF)
    n += 1
else (incorrect):
    n = 0
    I = 1

EF = EF + (0.1 - (5 - grade) × (0.08 + (5 - grade) × 0.02))
if EF < 1.3: EF = 1.3
```

### 5.3 Key Differences Explained

**1. Ease Hell vs Mean Reversion:**
SM-2's EF only goes down when you struggle and barely goes up. FSRS applies mean reversion (`D'' = w7 × D0(4) + (1-w7) × D'`) so difficulty always drifts back toward a baseline.

**2. No Forgetting Curve in SM-2:**
SM-2 doesn't model *when* you'll forget — it just multiplies the interval by EF. FSRS explicitly predicts the probability of recall at any moment.

**3. Overdue Reviews:**
SM-2 treats a card reviewed 10 days late the same as one reviewed on time (it just multiplies by EF either way). FSRS uses the actual retrievability at the moment of review, so delayed reviews that succeed get a *bigger* stability boost (spacing effect).

**4. Trainable Parameters:**
SM-2 uses the same hardcoded formula for everyone. FSRS can be trained on a user's review history to learn their personal forgetting patterns.

### 5.4 When to Use Which

| Scenario | Recommendation |
|----------|---------------|
| Quick prototype / MVP | SM-2 (simpler, 10 lines of code) |
| Production SRS app | FSRS (better accuracy, better UX) |
| User has irregular schedule | FSRS (handles overdue reviews gracefully) |
| Need personalization | FSRS (optimizer) |
| Legacy system, no migration budget | SM-2 (if it works, keep it) |
| Voice-first assistant | **FSRS** (better interval accuracy = fewer false reviews) |

### 5.5 Migration Path: SM-2 → FSRS

1. **Map ratings**: SM-2 grades 0–2 → `Again(1)`, grade 3 → `Hard(2)`, grade 4 → `Good(3)`, grade 5 → `Easy(4)`
2. **Map card state**: Use SM-2's current interval as an approximate starting stability: `S ≈ current_interval`
3. **Map difficulty**: `D ≈ (3.5 - EF) × 4 + 1` (rough mapping from EF range [1.3, 2.5] to D range [1, 10])
4. **Replay review logs** through FSRS optimizer if you have historical data:
   ```python
   from fsrs import Optimizer
   # Convert SM-2 logs to FSRS ReviewLog format
   optimizer = Optimizer(converted_logs)
   params = optimizer.compute_optimal_parameters()
   ```
5. **Reschedule all cards** with the new FSRS scheduler:
   ```python
   for card in all_cards:
       card = scheduler.reschedule_card(card, card_review_logs)
   ```

---

## 6. Voice-First Implementation Notes

### 6.1 Adapting FSRS for Voice

FSRS was designed for visual flashcards. For a voice assistant:

| Challenge | Solution |
|-----------|----------|
| No "flip card" moment | Voice prompts the question, waits for verbal answer, then reveals correct answer |
| Rating without buttons | Use voice commands: "I forgot" (Again), "That was hard" (Hard), "Got it" (Good), "Easy" (Easy) |
| Shorter sessions | Increase learning_steps to account for less frequent sessions |
| No visual review queue | Announce count: "You have 5 items to review today" |
| Ambient/passive review | Could trigger reviews based on time-of-day or context |

### 6.2 Simplified 2-Button Voice Rating

For voice UX, consider mapping to 2 buttons instead of 4:

```python
# Voice: "Did you remember?"
# "No" → Rating.Again (1)
# "Yes" → Rating.Good (3)

# This is valid — FSRS works fine with binary pass/fail
# (Anki's Pass/Fail add-on does exactly this)
```

### 6.3 Recommended Starting Configuration (Voice)

```python
scheduler = Scheduler(
    desired_retention=0.85,          # Slightly lower for voice (less precise recall)
    learning_steps=(
        timedelta(minutes=30),       # First repeat in 30 min (not 1 min)
        timedelta(hours=4),          # Second repeat in 4 hours
    ),
    relearning_steps=(
        timedelta(hours=1),          # Re-learn in 1 hour
    ),
    maximum_interval=365,            # Cap at 1 year for voice assistant
    enable_fuzzing=True,             # Avoid clustering reviews
)
```

---

## 7. Quick Reference: Card JSON Shape

### py-fsrs Card (serialized):
```json
{
  "due": "2026-04-18T14:30:00+00:00",
  "stability": 4.567,
  "difficulty": 5.234,
  "elapsed_days": 3,
  "scheduled_days": 4,
  "reps": 5,
  "lapses": 1,
  "state": 2,
  "last_review": "2026-04-14T14:30:00+00:00"
}
```

### ts-fsrs Card (native object):
```typescript
{
  due: Date,
  stability: number,
  difficulty: number,
  elapsed_days: number,
  scheduled_days: number,
  reps: number,
  lapses: number,
  state: State,        // 0=New, 1=Learning, 2=Review, 3=Relearning
  last_review?: Date
}
```

---

## 8. Resources & Links

| Resource | URL |
|----------|-----|
| py-fsrs API docs | https://open-spaced-repetition.github.io/py-fsrs |
| ts-fsrs TypeDoc | https://open-spaced-repetition.github.io/ts-fsrs/ |
| FSRS Algorithm Wiki | https://github.com/open-spaced-repetition/awesome-fsrs/wiki/The-Algorithm |
| FSRS Visualizer | https://open-spaced-repetition.github.io/anki_fsrs_visualizer/ |
| Interactive Forgetting Curve | https://interactive-forgetting-curve.streamlit.app/ |
| Awesome FSRS | https://github.com/open-spaced-repetition/awesome-fsrs |
| ts-fsrs Full-stack Demo | https://github.com/ishiko732/ts-fsrs-demo |
| FSRS Rust (canonical) | https://github.com/open-spaced-repetition/fsrs-rs |
| KDD 2022 Paper | http://www.maimemo.com/paper/ |
| HuggingFace Dataset (20k) | https://huggingface.co/datasets/open-spaced-repetition/FSRS-Anki-20k |

---

## 9. Summary: Key Takeaways for Implementation

1. **Use FSRS-6** (21 params) — it's the current version, implemented in both py-fsrs v6.3.1 and ts-fsrs
2. **Start with default parameters** — they work well. Train custom params after collecting 500+ reviews per user
3. **Store 9 fields per card**: `due`, `stability`, `difficulty`, `elapsed_days`, `scheduled_days`, `reps`, `lapses`, `state`, `last_review`
4. **Store review logs** — they're needed for the optimizer and are cheap to persist
5. **Use `desired_retention=0.85-0.90`** for voice (0.85 for casual, 0.90 for important content)
6. **py-fsrs for Python backend**, **ts-fsrs for frontend/Node.js** — APIs are nearly identical
7. **Binary pass/fail rating** (Again/Good) is perfectly valid and better for voice UX
8. **UTC everywhere** — convert at presentation layer only
9. **Fuzz intervals** in production to prevent review clustering
10. **The forgetting curve is the core insight** — FSRS doesn't just pick intervals heuristically, it models the actual probability of recall
