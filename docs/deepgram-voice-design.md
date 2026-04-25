# Deepgram Voice Agent Integration — Architecture Design
**Version:** 1.0  
**Date:** April 18, 2026  
**Status:** Ready for implementation  
**Depends on:** `docs/system-design.md`, `docs/voice-ai-infrastructure-research.md`

---

## 1. Architecture Overview

### 1.1 High-Level Design

ReCall replaces the current browser-based voice layer (Web Speech API STT + OpenAI TTS-1) with the **Deepgram Voice Agent API** — a unified WebSocket API that handles STT (Flux), LLM orchestration, and TTS (Aura-2) in a single persistent connection.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          BROWSER (Next.js)                              │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │              Voice Session UI (new page: /voice)                │    │
│  │                                                                 │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                      │    │
│  │  │ Capture  │  │ Review   │  │  Teach   │  ← mode selector     │    │
│  │  └──────────┘  └──────────┘  └──────────┘                      │    │
│  │                                                                 │    │
│  │  ┌─────────────────────────────────────────────────────────┐    │    │
│  │  │  useVoiceAgent hook                                     │    │    │
│  │  │  • MediaRecorder → raw audio chunks                     │    │    │
│  │  │  • WebSocket to backend /ws/voice                       │    │    │
│  │  │  • Receives audio playback chunks + transcript events   │    │    │
│  │  │  • Plays TTS audio via AudioContext (streaming)         │    │    │
│  │  └─────────────────────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │ WebSocket (WSS)
                                   │ binary audio frames + JSON control messages
                                   │
┌──────────────────────────────────▼──────────────────────────────────────┐
│                        FASTAPI BACKEND                                  │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  /ws/voice — WebSocket endpoint                                │    │
│  │                                                                 │    │
│  │  1. Authenticates + parses mode from query params               │    │
│  │  2. Opens WSS connection to Deepgram Voice Agent API            │    │
│  │  3. Sends agent config (instructions, functions, STT/TTS/LLM)   │    │
│  │  4. Bridges audio: client ↔ Deepgram                            │    │
│  │  5. Intercepts function_call events → runs backend services     │    │
│  │  6. Sends function results back to Deepgram                     │    │
│  │  7. Forwards transcript + status events to client               │    │
│  └──────────────────────────┬──────────────────────────────────────┘    │
│                             │                                           │
│  ┌──────────────────────────▼──────────────────────────────────────┐    │
│  │  VoiceSessionManager (new: services/voice_service.py)          │    │
│  │                                                                 │    │
│  │  • Builds Deepgram config per mode (capture/review/teach)       │    │
│  │  • Dispatches function calls to existing services               │    │
│  │  • Manages session state (review queue, teach chunk index)      │    │
│  │  • Enforces max session duration (cost control)                 │    │
│  │  • Accumulates transcripts for capture mode                    │    │
│  └──────────────────────────┬──────────────────────────────────────┘    │
│                             │                                           │
│  ┌──────────────────────────▼──────────────────────────────────────┐    │
│  │  Existing Services (unchanged)                                 │    │
│  │  • CaptureService.process()                                    │    │
│  │  • ReviewService.get_due() / evaluate_answer() / rate()        │    │
│  │  • TeachService.start() / respond()                            │    │
│  │  • KnowledgeService.search()                                   │    │
│  └──────────────────────────┬──────────────────────────────────────┘    │
│                             │                                           │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │ WSS
┌──────────────────────────────▼──────────────────────────────────────────┐
│                     DEEPGRAM VOICE AGENT API                            │
│                     (wss://agent.deepgram.com/agent)                    │
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │  STT (Flux)  │  │ LLM (BYO:   │  │ TTS (Aura-2) │                  │
│  │  turn detect │  │ GPT-4.1-nano)│  │  streaming   │                  │
│  │  barge-in    │  │ fn calling   │  │  sub-200ms   │                  │
│  └──────────────┘  └──────────────┘  └──────────────┘                  │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Server-Side Proxy — Decision

**Decision: Server-side WebSocket proxy (client → backend → Deepgram).**

Rationale:
- **Security**: Deepgram API key never leaves the backend. Client has no access to it.
- **Function calling**: When Deepgram calls a function (e.g., `search_knowledge`), the backend executes it against the database directly — no additional HTTP round-trip from the client.
- **State management**: Review queue, teach session state, transcript accumulation all live server-side with direct DB access.
- **Cost control**: Backend enforces max session duration and rate limits.
- **Simplicity**: Client sends raw audio and receives audio + JSON events — it doesn't need to know about Deepgram at all.

### 1.3 BYO LLM Strategy

**Decision: BYO LLM using GPT-4.1-nano (standard conversations) and GPT-4.1-mini (answer evaluation).**

Rationale:
- We already use these models for text-based capture/review. Using the same models for voice ensures consistent quality.
- Deepgram BYO LLM pricing: **$0.050/min** ($3.00/hr) vs $0.075/min ($4.50/hr) with Deepgram's default LLM — **33% savings**.
- GPT-4.1-nano is fast enough for conversational latency. It's our generation model.
- GPT-4.1-mini is used for evaluation tasks (invoked via function calling, not as the agent LLM).

Configuration: Deepgram will route LLM calls to the OpenAI API using our API key, specified in the agent config's `llm` block. The agent LLM handles conversation flow and decides when to call functions. Evaluation and extraction are done by our backend services (which call GPT-4.1-mini/nano themselves via function call responses).

---

## 2. WebSocket Connection Design

### 2.1 FastAPI WebSocket Endpoint

**New file: `backend/routers/voice_ws.py`**

```
Endpoint: ws://localhost:8000/ws/voice?mode={capture|review|teach}&session_id={optional}
```

| Parameter | Type | Required | Description |
|---|---|---|---|
| `mode` | query string | Yes | `capture`, `review`, or `teach` |
| `session_id` | query string | No | Existing teach session ID (for resume). Ignored in other modes. |
| `topic` | query string | No | Topic for teach mode (starts new session). Ignored in other modes. |

### 2.2 Authentication & Session Management

Phase 1 (single-user, no auth): The WebSocket endpoint validates the mode parameter and opens. No token required.

Future (multi-user): Add JWT token in the WebSocket query string `?token=xxx` or in the first message. Validate before opening the Deepgram connection.

**Session tracking**: Each WebSocket connection creates an in-memory `VoiceSession` object (not DB-persisted) with:
- `session_id`: UUID generated on connect
- `mode`: capture | review | teach
- `started_at`: timestamp (for max duration enforcement)
- `transcript_buffer`: accumulated transcript text (capture mode)
- `review_queue`: list of due questions (review mode)
- `review_index`: current question index (review mode)
- `teach_session_id`: DB teach session ID (teach mode)
- `teach_chunk_index`: current chunk (teach mode)

### 2.3 Connection Lifecycle

```
Client                          Backend                         Deepgram
  │                                │                                │
  ├──── WS connect ───────────────►│                                │
  │     ?mode=review               │                                │
  │                                │── validate params              │
  │                                │── create VoiceSession          │
  │                                │── load mode state              │
  │                                │   (e.g., get_due questions)    │
  │                                │                                │
  │                                ├── WSS connect ────────────────►│
  │                                │   wss://agent.deepgram.com     │
  │                                │                                │
  │                                ├── send SettingsConfiguration ─►│
  │                                │   (instructions, functions,    │
  │                                │    LLM, STT, TTS config)      │
  │                                │                                │
  │◄── JSON: {type:"ready"} ──────┤◄── Settings applied ──────────┤
  │                                │                                │
  │                                │     ┌──── CONVERSATION ────┐   │
  │── binary audio chunks ────────►│─────►  audio to Deepgram   │   │
  │                                │     │                      │   │
  │                                │◄────┤  TTS audio back      │   │
  │◄── binary audio chunks ────────┤     │                      │   │
  │                                │     │                      │   │
  │                                │◄────┤  transcript event    │   │
  │◄── JSON: {type:"transcript"}──┤     │                      │   │
  │                                │     │                      │   │
  │                                │◄────┤  function_call event │   │
  │                                │     │  (e.g. rate_question) │   │
  │                                │── execute service call     │   │
  │                                │── send function result ───►│   │
  │                                │     │                      │   │
  │◄── JSON: {type:"status"} ─────┤     │  (agent continues)   │   │
  │                                │     └──────────────────────┘   │
  │                                │                                │
  │── JSON: {type:"end"} ─────────►│                                │
  │  (or max duration reached)     │── close WSS ──────────────────►│
  │                                │── run cleanup                  │
  │                                │   (capture: process transcript)│
  │◄── JSON: {type:"session_end"} ┤                                │
  │◄── WS close ──────────────────┤                                │
```

### 2.4 Audio Format

| Direction | Format | Sample Rate | Encoding | Channels |
|---|---|---|---|---|
| Client → Backend → Deepgram | Linear16 PCM | 16000 Hz | 16-bit little-endian | Mono |
| Deepgram → Backend → Client | Linear16 PCM | 24000 Hz | 16-bit little-endian | Mono |

The frontend captures audio using `MediaRecorder` with `audio/webm;codecs=opus` or the Web Audio API's `AudioWorklet` to produce raw PCM. **Recommended: AudioWorklet** for raw PCM at 16kHz to avoid transcoding.

### 2.5 WebSocket Message Protocol (Client ↔ Backend)

**Client → Backend:**

| Message | Format | Description |
|---|---|---|
| Audio data | Binary (PCM bytes) | Raw mic audio, continuous stream |
| `{"type":"end"}` | JSON | User ends session |
| `{"type":"config","settings":{...}}` | JSON | Runtime config updates (e.g., change voice) |

**Backend → Client:**

| Message | Format | Description |
|---|---|---|
| Audio data | Binary (PCM bytes) | TTS audio from Deepgram, continuous stream |
| `{"type":"ready"}` | JSON | Connection established, agent ready |
| `{"type":"transcript","role":"user","text":"...","is_final":bool}` | JSON | User speech transcript |
| `{"type":"transcript","role":"agent","text":"..."}` | JSON | Agent response text |
| `{"type":"status","state":"...","detail":{...}}` | JSON | Mode-specific status (see below) |
| `{"type":"function_result","name":"...","result":{...}}` | JSON | Notifies client of a function execution result |
| `{"type":"session_end","summary":{...}}` | JSON | Session complete, final stats |
| `{"type":"error","message":"...","code":"..."}` | JSON | Error occurred |

**Status events by mode:**

| Mode | State | Detail |
|---|---|---|
| capture | `transcribing` | `{transcript_length: int}` |
| capture | `processing` | `{message: "Extracting knowledge..."}` |
| capture | `complete` | `{capture_id, facts_count, questions_count}` |
| review | `asking` | `{question_index, total, question_text, question_type}` |
| review | `listening` | `{question_id}` |
| review | `evaluating` | `{question_id}` |
| review | `feedback` | `{score, feedback, suggested_rating, correct_answer}` |
| review | `rating` | `{question_id}` — waiting for voice rating |
| review | `rated` | `{rating, next_due, interval_days}` |
| review | `complete` | `{reviewed_count, session_duration_s}` |
| teach | `teaching` | `{chunk_index, total, title, content, analogy}` |
| teach | `asking_recall` | `{recall_question}` |
| teach | `evaluating` | `{chunk_index}` |
| teach | `feedback` | `{score, feedback}` |
| teach | `complete` | `{topic, chunks_covered, capture_id}` |

---

## 3. Voice Modes

### 3.1 Mode A: Voice Capture

**Purpose**: User speaks freely. Deepgram transcribes in real-time. When the user is done, the full transcript is processed through the capture pipeline.

#### State Machine

```
┌─────────┐    user speaks     ┌──────────────┐
│  IDLE   │ ─────────────────► │ TRANSCRIBING │ ◄──┐
└─────────┘                    └──────┬───────┘    │
                                      │            │
                               silence/pause       │ user speaks again
                                      │            │
                                      ▼            │
                               ┌──────────────┐    │
                               │   PAUSED     │ ───┘
                               └──────┬───────┘
                                      │
                          user says "done" / "that's it" / "save"
                          OR 10s silence after last speech
                          OR user clicks end button
                                      │
                                      ▼
                               ┌──────────────┐
                               │ PROCESSING   │ ← backend calls CaptureService.process()
                               └──────┬───────┘
                                      │
                                      ▼
                               ┌──────────────┐
                               │  COMPLETE    │ → agent speaks summary, session ends
                               └──────────────┘
```

#### How It Works

1. **Agent instructions** tell the Deepgram agent to act as a silent listener/note-taker. The agent does NOT respond conversationally during transcription — it only acknowledges briefly ("Got it", "Noted") on long pauses.
2. **Transcript accumulation**: The backend accumulates all `user_transcript` events into `VoiceSession.transcript_buffer`.
3. **End detection**: The agent is instructed to call the `finish_capture` function when the user signals they're done (voice commands: "done", "that's it", "save", "I'm done"). The function also triggers on 10 seconds of silence after the last speech.
4. **Processing**: `finish_capture` function handler:
   - Takes the accumulated transcript
   - Calls `CaptureService.process(CaptureRequest(raw_text=transcript, source_type="voice"))`
   - Agent speaks summary: "Captured 4 facts and generated 6 review questions."
5. **"Why does this matter?"**: After capture processing, the agent asks the user "Why does this matter to you?" The response gets stored as `why_it_matters` on the capture.

#### Deepgram Function for Capture

```json
{
  "name": "finish_capture",
  "description": "Called when the user finishes dictating. Processes the accumulated transcript into knowledge facts and review questions.",
  "parameters": {
    "type": "object",
    "properties": {
      "final_transcript": {
        "type": "string",
        "description": "The complete transcript of everything the user said"
      }
    },
    "required": ["final_transcript"]
  }
}
```

### 3.2 Mode B: Voice Review (Pimsleur-Style Anticipation Loop)

**Purpose**: AI-driven spaced repetition review through conversation. Follows the Pimsleur anticipation pattern: question → pause → answer → feedback → rating.

#### State Machine

```
┌──────────┐
│  INIT    │ ← load due questions via ReviewService.get_due()
└────┬─────┘
     │ questions loaded
     ▼
┌──────────┐    agent speaks question
│ ASKING   │ ──────────────────────────┐
└──────────┘                           │
     ▲                                 ▼
     │                          ┌──────────────┐
     │                          │  LISTENING   │ ← user speaks answer
     │                          └──────┬───────┘
     │                                 │ user_transcript received
     │                                 ▼
     │                          ┌──────────────┐
     │                          │ EVALUATING   │ ← backend: ReviewService.evaluate_answer()
     │                          └──────┬───────┘
     │                                 │ evaluation complete
     │                                 ▼
     │                          ┌──────────────┐
     │                          │  FEEDBACK    │ ← agent speaks feedback + correct answer
     │                          └──────┬───────┘
     │                                 │ agent asks "How did you do?"
     │                                 ▼
     │                          ┌──────────────┐
     │                          │   RATING     │ ← user says rating word
     │                          └──────┬───────┘
     │                                 │ parsed to 1-4, FSRS updated
     │         more questions          │
     └────────────────────────────┐    │
                                  │    │ no more questions
                                  │    ▼
                               ┌──────────────┐
                               │  COMPLETE    │ → agent speaks session summary
                               └──────────────┘
```

#### Voice Rating Mapping

The agent is instructed to ask "How did you do? Say again, hard, good, or easy." The user's response is parsed by a function call:

| Voice Command | FSRS Rating | Meaning |
|---|---|---|
| "again" / "forgot" / "didn't know" / "no idea" | 1 (Again) | Complete failure |
| "hard" / "barely" / "struggled" / "difficult" | 2 (Hard) | Significant difficulty |
| "good" / "got it" / "knew it" / "correct" | 3 (Good) | Correct with effort |
| "easy" / "too easy" / "obvious" / "no problem" | 4 (Easy) | Effortless recall |

Parsing is done **by the LLM** (the Deepgram agent LLM interprets the user's intent) and passed as a parameter to the `rate_question` function.

#### Review Loop — Function Call Sequence

1. On session start, backend calls `ReviewService.get_due(limit=20)` and stores questions in `VoiceSession.review_queue`.
2. Agent is instructed to call `get_next_question()` to start.
3. Agent receives question text → speaks it to the user.
4. User answers → agent calls `evaluate_answer(question_id, user_answer)`.
5. Backend runs `ReviewService.evaluate_answer()` → returns feedback.
6. Agent speaks feedback and correct answer → asks for rating.
7. User rates → agent calls `rate_question(question_id, rating)`.
8. Backend runs `ReviewService.rate()` → returns interval info.
9. Agent speaks "Scheduled for review in 3 days" → calls `get_next_question()`.
10. Loop repeats until queue is empty or user says "stop" / "I'm done".

#### Deepgram Functions for Review

```json
[
  {
    "name": "get_next_question",
    "description": "Get the next review question to ask the user. Returns null when all questions are done.",
    "parameters": { "type": "object", "properties": {} }
  },
  {
    "name": "evaluate_answer",
    "description": "Evaluate the user's spoken answer against the correct answer. Call this after the user answers a question.",
    "parameters": {
      "type": "object",
      "properties": {
        "question_id": { "type": "string", "description": "The question ID" },
        "user_answer": { "type": "string", "description": "What the user said" }
      },
      "required": ["question_id", "user_answer"]
    }
  },
  {
    "name": "rate_question",
    "description": "Submit the user's self-rating for a question. Map the user's words to a rating: 'again'=1, 'hard'=2, 'good'=3, 'easy'=4.",
    "parameters": {
      "type": "object",
      "properties": {
        "question_id": { "type": "string", "description": "The question ID" },
        "rating": { "type": "integer", "enum": [1, 2, 3, 4], "description": "FSRS rating: 1=Again, 2=Hard, 3=Good, 4=Easy" }
      },
      "required": ["question_id", "rating"]
    }
  }
]
```

### 3.3 Mode C: Voice Teach

**Purpose**: AI teaches a topic in chunks, testing recall after each chunk. Maps directly to existing `TeachService`.

#### State Machine

```
┌──────────┐
│  INIT    │ ← TeachService.start(topic) or resume session
└────┬─────┘
     │ plan generated, first chunk loaded
     ▼
┌──────────────┐    agent speaks chunk content + analogy
│  TEACHING    │ ──────────────────────────────────┐
└──────────────┘                                   │
     ▲                                             ▼
     │                                      ┌──────────────┐
     │                                      │ ASKING_RECALL │ ← agent asks recall question
     │                                      └──────┬───────┘
     │                                             │ user answers
     │                                             ▼
     │                                      ┌──────────────┐
     │                                      │ EVALUATING   │ ← TeachService.respond()
     │                                      └──────┬───────┘
     │                                             │
     │                                             ▼
     │                                      ┌──────────────┐
     │                                      │  FEEDBACK    │ ← agent speaks feedback
     │        more chunks                   └──────┬───────┘
     └────────────────────────────────┐            │
                                      │            │ last chunk
                                      │            ▼
                                      │     ┌──────────────┐
                                      │     │  COMPLETE    │ → agent speaks summary
                                      │     └──────────────┘
                                      │
                                      └── agent calls get_next_teach_chunk()
                                          which returns next chunk content
```

#### Teach Loop — Function Call Sequence

1. Backend calls `TeachService.start(TeachStartRequest(topic=topic))` → gets first chunk.
2. Agent speaks: chunk title, content, analogy.
3. Agent asks the recall question.
4. User answers → agent calls `submit_teach_answer(session_id, answer)`.
5. Backend calls `TeachService.respond()` → returns score, feedback, and next chunk (or summary).
6. Agent speaks feedback.
7. If not complete: agent speaks next chunk → asks next recall question → repeat.
8. If complete: agent speaks summary, session ends.

#### Deepgram Functions for Teach

```json
[
  {
    "name": "get_current_teach_chunk",
    "description": "Get the current teaching chunk to present to the user. Includes title, content, analogy, and recall question.",
    "parameters": { "type": "object", "properties": {} }
  },
  {
    "name": "submit_teach_answer",
    "description": "Submit the user's answer to the current recall question.",
    "parameters": {
      "type": "object",
      "properties": {
        "answer": { "type": "string", "description": "The user's answer to the recall question" }
      },
      "required": ["answer"]
    }
  }
]
```

---

## 4. Function Calling Design

### 4.1 Function Registry

All functions are registered with the Deepgram agent at connection setup. The backend intercepts `function_call_request` events from Deepgram, executes the corresponding service method, and returns the result via `function_call_response`.

| Function | Available In | Backend Service | Description |
|---|---|---|---|
| `search_knowledge` | All modes | `KnowledgeService.search()` | Search user's knowledge base by semantic query |
| `finish_capture` | Capture | `CaptureService.process()` | Process accumulated transcript into facts + questions |
| `get_next_question` | Review | `VoiceSession.review_queue` | Dequeue next review question |
| `evaluate_answer` | Review | `ReviewService.evaluate_answer()` | LLM-evaluate user's answer |
| `rate_question` | Review | `ReviewService.rate()` | Apply FSRS rating |
| `get_current_teach_chunk` | Teach | `VoiceSession` state | Return current chunk content |
| `submit_teach_answer` | Teach | `TeachService.respond()` | Evaluate recall answer, advance chunk |
| `end_session` | All modes | `VoiceSession` cleanup | Gracefully end the voice session |

### 4.2 Function Schemas (Complete)

```json
[
  {
    "name": "search_knowledge",
    "description": "Search the user's personal knowledge base. Use when the user asks a question about something they previously learned or captured. Returns relevant facts with sources.",
    "parameters": {
      "type": "object",
      "properties": {
        "query": {
          "type": "string",
          "description": "The search query — what the user wants to know about"
        }
      },
      "required": ["query"]
    }
  },
  {
    "name": "finish_capture",
    "description": "Called when the user finishes speaking/dictating content to capture. Processes the transcript into structured knowledge facts and generates review questions. Call this when the user says 'done', 'that's it', 'save', 'I'm done', or similar.",
    "parameters": {
      "type": "object",
      "properties": {
        "final_transcript": {
          "type": "string",
          "description": "The complete text of everything the user said to capture"
        }
      },
      "required": ["final_transcript"]
    }
  },
  {
    "name": "get_next_question",
    "description": "Get the next review question to ask the user. Returns the question text and metadata. Returns null when all questions have been reviewed.",
    "parameters": {
      "type": "object",
      "properties": {}
    }
  },
  {
    "name": "evaluate_answer",
    "description": "Evaluate the user's spoken answer to a review question. Returns correctness score, feedback, the correct answer, and a suggested rating.",
    "parameters": {
      "type": "object",
      "properties": {
        "question_id": {
          "type": "string",
          "description": "The UUID of the question being answered"
        },
        "user_answer": {
          "type": "string",
          "description": "The user's spoken answer, transcribed"
        }
      },
      "required": ["question_id", "user_answer"]
    }
  },
  {
    "name": "rate_question",
    "description": "Submit the user's self-rated difficulty for a review question. Interpret the user's words: 'again'/'forgot'=1, 'hard'/'struggled'=2, 'good'/'got it'=3, 'easy'/'obvious'=4. This updates the spaced repetition schedule.",
    "parameters": {
      "type": "object",
      "properties": {
        "question_id": {
          "type": "string",
          "description": "The UUID of the question being rated"
        },
        "rating": {
          "type": "integer",
          "enum": [1, 2, 3, 4],
          "description": "1=Again, 2=Hard, 3=Good, 4=Easy"
        }
      },
      "required": ["question_id", "rating"]
    }
  },
  {
    "name": "get_current_teach_chunk",
    "description": "Get the current teaching chunk to present to the user. Returns the chunk title, content, analogy, and recall question.",
    "parameters": {
      "type": "object",
      "properties": {}
    }
  },
  {
    "name": "submit_teach_answer",
    "description": "Submit the user's answer to the current recall question in teach mode. Returns feedback, score, and whether the session is complete. If not complete, also returns the next chunk.",
    "parameters": {
      "type": "object",
      "properties": {
        "answer": {
          "type": "string",
          "description": "The user's spoken answer to the recall question"
        }
      },
      "required": ["answer"]
    }
  },
  {
    "name": "end_session",
    "description": "End the voice session gracefully. Call this when the user says 'stop', 'exit', 'quit', 'I'm done', or similar. In capture mode, this also processes any remaining transcript.",
    "parameters": {
      "type": "object",
      "properties": {}
    }
  }
]
```

### 4.3 Function Dispatch (Backend)

New file: **`backend/services/voice_service.py`**

The `VoiceSessionManager` class handles function dispatch:

```
function_call_request from Deepgram
        │
        ▼
VoiceSessionManager.handle_function_call(name, params)
        │
        ├── "search_knowledge"    → KnowledgeService.search(query)
        │                           return {answer, sources, has_answer}
        │
        ├── "finish_capture"      → CaptureService.process(CaptureRequest(...))
        │                           return {capture_id, facts_count, questions_count}
        │
        ├── "get_next_question"   → pop from self.review_queue
        │                           return {question_id, question_text, question_type, mnemonic_hint}
        │                           or {done: true} if empty
        │
        ├── "evaluate_answer"     → ReviewService.evaluate_answer(EvaluateRequest(...))
        │                           return {correct_answer, score, feedback, suggested_rating}
        │
        ├── "rate_question"       → ReviewService.rate(RateRequest(...))
        │                           return {next_due, interval_days, state_label}
        │
        ├── "get_current_teach_chunk" → read from self.teach_state
        │                           return {chunk_title, chunk_content, chunk_analogy, recall_question}
        │
        ├── "submit_teach_answer" → TeachService.respond(TeachRespondRequest(...))
        │                           return {feedback, score, is_complete, next_chunk?, summary?}
        │
        └── "end_session"         → cleanup, return {summary}
```

---

## 5. Deepgram Configuration

### 5.1 Agent Settings Configuration Message

Sent immediately after the WebSocket to Deepgram opens. This is the `SettingsConfiguration` message per the Deepgram Voice Agent API protocol.

```json
{
  "type": "SettingsConfiguration",
  "audio": {
    "input": {
      "encoding": "linear16",
      "sample_rate": 16000
    },
    "output": {
      "encoding": "linear16",
      "sample_rate": 24000,
      "container": "none"
    }
  },
  "agent": {
    "listen": {
      "model": "nova-3",
      "language": "en",
      "keywords": ["ReCall:2", "spaced repetition:1", "FSRS:2", "mnemonic:1"]
    },
    "think": {
      "provider": {
        "type": "open_ai",
        "model": "gpt-4.1-nano",
        "temperature": 0.4
      },
      "functions": [ /* mode-specific functions, see Section 4.2 */ ]
    },
    "speak": {
      "model": "aura-2-andromeda-en"
    }
  }
}
```

### 5.2 System Prompts Per Mode

#### Capture Mode System Prompt

```
You are ReCall, a personal memory assistant. The user is dictating information they want to remember.

Your role:
- Listen actively and stay silent while the user speaks
- On brief pauses, give a short acknowledgment: "Got it" or "Noted"
- Do NOT ask follow-up questions during dictation
- Do NOT rephrase or summarize during dictation
- When the user says "done", "that's it", "save", or "I'm done", call the finish_capture function with the complete transcript
- After capture is processed, tell the user how many facts and questions were extracted
- Then ask: "Why does this matter to you?" — capture their one-sentence reflection
- If the user asks a question about something they previously learned, use search_knowledge

Keep responses very brief. This is a dictation mode, not a conversation.
```

#### Review Mode System Prompt

```
You are ReCall, conducting a spaced repetition review session using the Pimsleur anticipation method.

Your role:
1. Start by calling get_next_question to get the first question
2. Read the question clearly and naturally
3. Pause and wait for the user to answer (do NOT give hints)
4. After the user answers, call evaluate_answer with their response
5. Share the feedback:
   - If correct: brief praise + the exact correct answer
   - If partial: acknowledge what they got right, then the full correct answer
   - If wrong: encouraging tone, then the full correct answer
6. Ask: "How did you do? Say again, hard, good, or easy."
7. Call rate_question with the parsed rating (again=1, hard=2, good=3, easy=4)
8. Briefly confirm: "Scheduled for review in [X days]."
9. Call get_next_question for the next one

If the user has a mnemonic_hint, mention it AFTER they answer (not before — don't give away the answer).
If the user says "stop" or "I'm done", call end_session.
If the user asks about something from their knowledge base, use search_knowledge.

Be encouraging but concise. Keep the pace steady — this should feel like a focused study session.
```

#### Teach Mode System Prompt

```
You are ReCall, teaching the user a topic using proven memory techniques.

Your role:
1. Start by calling get_current_teach_chunk to get the first chunk
2. Present the chunk naturally:
   - State the chunk title
   - Explain the content clearly and conversationally
   - If there's an analogy, weave it in naturally
3. After presenting, ask the recall question
4. Wait for the user to answer
5. Call submit_teach_answer with their response
6. Share the feedback:
   - If correct: praise and reinforce
   - If partial: acknowledge what's right, fill in gaps
   - If wrong: encouraging, re-explain briefly
7. If not complete, the function returns the next chunk — present it
8. If complete, congratulate them and share the summary

Teaching style:
- Be conversational and warm, like a patient tutor
- Use "we" language: "Let's look at...", "Now we'll explore..."
- If the user asks to repeat, re-explain the current chunk differently
- If the user asks a question about something else, use search_knowledge

Never rush. Let the user absorb each chunk before moving on.
```

### 5.3 STT Settings

| Setting | Value | Rationale |
|---|---|---|
| Model | `nova-3` | Best accuracy for streaming. Flux is voice-agent-optimized but nova-3 has broader language support and is used within the Voice Agent API's listen pipeline. |
| Language | `en` | English-only for Phase 1 |
| Keywords | `ReCall:2`, `FSRS:2`, domain terms | Boost recognition of app-specific terms |
| Smart formatting | Enabled (default) | Punctuation, casing, numerals |
| Endpointing | Default (Deepgram manages) | Voice Agent API handles turn detection internally |

### 5.4 TTS Settings

| Setting | Value | Rationale |
|---|---|---|
| Model | `aura-2-andromeda-en` | Clear, professional female voice. Good pacing for educational content. |
| Encoding | `linear16` | Raw PCM for minimal client-side processing |
| Sample rate | `24000` | Default for Aura-2 |

Alternative voices to offer: `aura-2-asteria-en` (warmer), `aura-2-orion-en` (male). User preference stored in localStorage.

### 5.5 LLM Settings

| Setting | Value | Rationale |
|---|---|---|
| Provider | `open_ai` | BYO LLM — use our existing OpenAI key |
| Model | `gpt-4.1-nano` | Fast, cheap, good for conversational flow. Same model we use for text generation. |
| Temperature | `0.4` | Low for factual accuracy, slight variation for natural conversation |
| Max tokens | `300` | Agent responses should be short in voice. Longer outputs handled by function results. |

---

## 6. Frontend Integration

### 6.1 New Page: `/voice`

**New file: `frontend/app/voice/page.tsx`**

A full-screen conversational voice interface with three mode tabs.

```
┌────────────────────────────────────────────┐
│  ← Back          ReCall Voice              │
│                                            │
│  ┌──────────┬──────────┬──────────┐        │
│  │ Capture  │ Review   │  Teach   │        │
│  └──────────┴──────────┴──────────┘        │
│                                            │
│  ┌────────────────────────────────────┐    │
│  │                                    │    │
│  │         ◉  (pulsing orb)          │    │
│  │      "Listening..."               │    │
│  │                                    │    │
│  │                                    │    │
│  └────────────────────────────────────┘    │
│                                            │
│  ┌────────────────────────────────────┐    │
│  │  Live Transcript                   │    │
│  │  Agent: "What is the time..."      │    │
│  │  You: "O(log n) because..."        │    │
│  │  Agent: "Correct! Binary search..."│    │
│  └────────────────────────────────────┘    │
│                                            │
│  ┌────────────────────────────────────┐    │
│  │  Review: 3/8  ●●●○○○○○            │    │
│  │  Duration: 2:34                    │    │
│  └────────────────────────────────────┘    │
│                                            │
│          [ End Session ]                   │
│                                            │
└────────────────────────────────────────────┘
```

#### UI Elements

| Element | Description |
|---|---|
| **Mode tabs** | Capture / Review / Teach — switches mode before session starts |
| **Orb indicator** | Animated circle — pulses when listening, glows when agent is speaking, idle when waiting |
| **Status text** | Current state: "Listening...", "Thinking...", "Speaking..." |
| **Live transcript** | Scrolling conversation transcript with role labels (Agent / You) |
| **Progress bar** | Review: question count. Teach: chunk count. Capture: word count. |
| **Duration timer** | Elapsed time for cost awareness |
| **End button** | Graceful session end |
| **Teach topic input** | Text field shown only in Teach mode before session starts |

### 6.2 New Hook: `useVoiceAgent`

**New file: `frontend/hooks/useVoiceAgent.ts`**

```typescript
// Public API of useVoiceAgent hook:
{
  // State
  status: "idle" | "connecting" | "ready" | "active" | "error";
  isAgentSpeaking: boolean;
  isUserSpeaking: boolean;
  transcript: TranscriptEntry[];   // {role, text, timestamp}
  modeState: ModeState;            // mode-specific status (review progress, etc.)
  error: string | null;
  sessionDuration: number;         // seconds

  // Actions
  connect(mode: "capture" | "review" | "teach", options?: { topic?: string; sessionId?: string }): Promise<void>;
  disconnect(): void;
}
```

#### Hook Internals

1. **`connect()`**: Requests mic permission via `getUserMedia({ audio: { sampleRate: 16000, channelCount: 1 } })`. Opens WebSocket to `ws://localhost:8000/ws/voice?mode=X`. Creates an `AudioWorklet` processor to downsample mic input to 16kHz linear16 PCM and send binary frames over the WebSocket.
2. **Audio playback**: Incoming binary frames from the WebSocket are queued into an `AudioContext` buffer and played back using a playback `AudioWorklet`. This provides gapless streaming TTS playback.
3. **Transcript handling**: JSON messages with `type: "transcript"` are appended to the `transcript` state array.
4. **Status handling**: JSON messages with `type: "status"` update `modeState`.
5. **`disconnect()`**: Sends `{"type":"end"}`, waits for `session_end`, closes WebSocket, stops mic.

### 6.3 Audio Processing Components

**New file: `frontend/lib/audio-worklet-processor.js`** — AudioWorklet for mic input (PCM 16kHz mono).  
**New file: `frontend/lib/audio-playback.ts`** — Streaming PCM playback via AudioContext.

### 6.4 Fallback When Deepgram Is Unavailable

- If WebSocket connection fails or Deepgram returns an error, the UI shows a toast: "Voice agent unavailable. Using text mode."
- Capture mode falls back to the existing `useVoiceCapture` hook (browser Web Speech API).
- Review mode falls back to the existing text-based review UI.
- A `NEXT_PUBLIC_VOICE_AGENT_ENABLED` env var controls whether the voice page is shown in navigation (default `true`).

### 6.5 Navigation

Add "Voice" to the sidebar in `frontend/components/layout/Sidebar.tsx` (or equivalent navigation component). Icon: microphone. Links to `/voice`.

---

## 7. API Design

### 7.1 New Endpoints

| Endpoint | Type | Description |
|---|---|---|
| `ws://localhost:8000/ws/voice` | WebSocket | Main voice agent endpoint |
| `GET /api/voice/status` | HTTP | Check if Deepgram voice agent is available (API key configured, service reachable) |

### 7.2 Voice Status Endpoint

**File: `backend/routers/voice.py`** (add to existing)

```
GET /api/voice/status

Response 200:
{
  "available": true,
  "provider": "deepgram",
  "modes": ["capture", "review", "teach"]
}

Response 200 (no API key):
{
  "available": false,
  "provider": null,
  "modes": []
}
```

### 7.3 WebSocket Message Protocol

See Section 2.5 for the complete protocol. Summary:

**Inbound (client → backend):**
- Binary: PCM audio frames
- JSON: `{"type":"end"}` — end session
- JSON: `{"type":"config", "settings": {...}}` — runtime config updates

**Outbound (backend → client):**
- Binary: TTS audio frames
- JSON: ready, transcript, status, function_result, session_end, error events

### 7.4 Deepgram WebSocket Protocol (Backend ↔ Deepgram)

The backend communicates with Deepgram using the Voice Agent API WebSocket protocol:

**Backend → Deepgram:**
- `SettingsConfiguration` — initial agent setup
- Binary audio frames — user mic audio
- `FunctionCallResponse` — result of a function execution
- `UpdateInstructions` — update agent instructions mid-session (if needed)
- `InjectAgentMessage` — force agent to speak a specific message

**Deepgram → Backend:**
- `Welcome` — connection confirmed
- `SettingsApplied` — configuration accepted
- `UserStartedSpeaking` — user began talking
- `ConversationText` — transcript of user or agent speech
- `AgentThinking` — agent is processing
- `FunctionCallRequest` — agent wants to call a function
- `AgentAudioDone` — agent finished speaking current utterance
- `Error` — error from Deepgram

### 7.5 Existing Endpoints (Unchanged)

The following existing endpoints continue to work as-is. The voice layer calls the same service methods these endpoints use:

- `POST /api/captures` → `CaptureService.process()`
- `GET /api/reviews/due` → `ReviewService.get_due()`
- `POST /api/reviews/submit` → `ReviewService.evaluate_answer()`
- `POST /api/reviews/rate` → `ReviewService.rate()`
- `POST /api/teach/start` → `TeachService.start()`
- `POST /api/teach/respond` → `TeachService.respond()`
- `POST /api/knowledge/search` → `KnowledgeService.search()`
- `POST /api/voice/tts` → OpenAI TTS-1 (kept as fallback)

---

## 8. Error Handling & Edge Cases

### 8.1 Network Disconnection Mid-Conversation

| Scenario | Handling |
|---|---|
| Client → Backend WS drops | Backend detects disconnect, closes Deepgram WS, cleans up session. In capture mode, any accumulated transcript is saved and processed (best-effort). In review mode, any unrated questions remain in their current FSRS state (no data loss). |
| Backend → Deepgram WS drops | Backend attempts one reconnect with the same `SettingsConfiguration`. If reconnect fails, sends `{"type":"error","message":"Voice service disconnected","code":"deepgram_disconnect"}` to client. Client shows "Connection lost" and offers retry or text fallback. |
| Internet loss (both directions) | Client detects WS close, shows offline state. On reconnect, client opens a new session. No data is lost from previous operations (all DB writes are transactional). |

### 8.2 Deepgram API Errors

| Error | Handling |
|---|---|
| Invalid API key | Backend logs error, returns `{"type":"error","code":"auth_failed"}` to client. Client shows "Voice agent unavailable" and offers text mode. |
| Rate limit (429) | Backend returns `{"type":"error","code":"rate_limited"}`. Client shows "Too many voice sessions. Try again in a minute." |
| Deepgram service down (5xx) | Backend returns `{"type":"error","code":"service_unavailable"}`. Client falls back to existing Web Speech API voice. |
| Invalid audio format | Backend logs, sends error to client. Unlikely with correct AudioWorklet config. |

### 8.3 Empty Transcripts

- If the user connects but says nothing for 30 seconds, the agent prompts: "I'm listening. Go ahead whenever you're ready."
- If the user in capture mode says "done" but the transcript is empty, the agent responds: "I didn't catch anything. Could you try again?"
- The `finish_capture` function handler validates that `final_transcript` is non-empty before calling `CaptureService.process()`.

### 8.4 Rate Limiting for Voice Sessions

- **Max concurrent sessions per IP**: 2 (prevents abuse)
- **Max session duration**: 15 minutes (enforced by backend timer)
- **Session duration warning**: At 12 minutes, agent says: "We've been going for 12 minutes. I'll wrap up in 3 minutes."
- **At 15 minutes**: Backend sends `end_session`, closes connection.
- **Rate limiter**: Max 10 voice session starts per hour per IP (uses existing `rate_limiter.py`).

### 8.5 Cost Controls

| Control | Mechanism |
|---|---|
| Max session duration | 15-minute hard cap (configurable via `MAX_VOICE_SESSION_MINUTES` env var) |
| Session counting | Backend logs session start/end + duration to a `voice_sessions` table for cost tracking |
| Daily budget | Optional `MAX_VOICE_MINUTES_PER_DAY` env var. Backend checks cumulative daily usage before allowing new sessions. Default: 60 minutes. |
| Kill switch | `DEEPGRAM_ENABLED=false` env var disables voice agent entirely. `/api/voice/status` returns `available: false`. |

### 8.6 Barge-In

Deepgram Voice Agent API handles barge-in natively. When the user speaks while the agent is speaking:
1. Deepgram stops TTS output.
2. Deepgram sends `UserStartedSpeaking` event.
3. Backend forwards the event to the client as `{"type":"status","state":"user_speaking"}`.
4. Client stops audio playback immediately (clears audio buffer).
5. Normal flow resumes with the user's new utterance.

---

## 9. Migration Strategy

### 9.1 Coexistence Plan

The Deepgram voice agent **does not replace** the existing voice layer immediately. Both coexist:

| Component | Status | Purpose |
|---|---|---|
| `useVoiceCapture` (Web Speech API) | **Kept** | Fallback for browsers without mic permission for AudioWorklet, or when Deepgram is unavailable |
| `useVoiceReview` (Web Speech API + OpenAI TTS) | **Kept** | Fallback for review when Deepgram is down |
| `POST /api/voice/tts` (OpenAI TTS-1) | **Kept** | Fallback TTS endpoint, also used by existing non-voice-agent pages |
| `useVoiceAgent` (new) | **Added** | Primary voice experience on `/voice` page |
| `/ws/voice` (new) | **Added** | Deepgram Voice Agent WebSocket proxy |
| `/voice` page (new) | **Added** | Dedicated voice conversation UI |

### 9.2 Feature Flag

```env
# .env
DEEPGRAM_API_KEY=your_key_here        # Required for voice agent
DEEPGRAM_ENABLED=true                  # Kill switch
MAX_VOICE_SESSION_MINUTES=15           # Cost control
MAX_VOICE_MINUTES_PER_DAY=60           # Daily budget
```

```env
# .env.local (frontend)
NEXT_PUBLIC_VOICE_AGENT_ENABLED=true   # Show /voice in navigation
```

### 9.3 Config Changes

**`backend/config.py`** — add new settings:

| Setting | Type | Default | Description |
|---|---|---|---|
| `DEEPGRAM_API_KEY` | str | `""` | Deepgram API key |
| `DEEPGRAM_ENABLED` | bool | `False` | Enable/disable voice agent |
| `MAX_VOICE_SESSION_MINUTES` | int | `15` | Max session duration |
| `MAX_VOICE_MINUTES_PER_DAY` | int | `60` | Daily voice minute budget |
| `DEEPGRAM_VOICE_MODEL` | str | `"aura-2-andromeda-en"` | Default TTS voice |
| `DEEPGRAM_STT_MODEL` | str | `"nova-3"` | STT model |
| `DEEPGRAM_LLM_MODEL` | str | `"gpt-4.1-nano"` | Agent LLM model |

### 9.4 Existing Voice UI Pages

The existing capture and review pages keep their current voice toggles (`VoiceCaptureButton.tsx`, `VoiceControls.tsx`). These use the Web Speech API and are unaffected. Users who want the full conversational experience go to `/voice`.

---

## 10. Data Flow Diagrams

### 10.1 Capture Mode Flow

```
User speaks into mic
        │
        ▼
AudioWorklet captures PCM 16kHz
        │
        ▼ binary frames
Frontend WebSocket ──────────────────► Backend /ws/voice?mode=capture
                                              │
                                              ▼ binary frames
                                       Deepgram Voice Agent API
                                              │
                                    ┌─────────┴─────────┐
                                    ▼                   ▼
                              STT (Nova-3)        LLM (GPT-4.1-nano)
                              transcribes         follows capture prompt
                                    │                   │
                                    ▼                   │
                              ConversationText          │
                              (user transcript)         │
                                    │                   │
                         ┌──────────┘                   │
                         ▼                              │
                  Backend accumulates              Agent occasionally
                  transcript in                    says "Got it"
                  VoiceSession.transcript_buffer        │
                         │                              ▼
                         │                    TTS audio → client
                         │                    (agent acknowledgment)
                         │
        User says "done" │
                         ▼
              Deepgram sends FunctionCallRequest
              name: "finish_capture"
              params: {final_transcript: "...accumulated text..."}
                         │
                         ▼
              Backend: CaptureService.process(
                CaptureRequest(raw_text=transcript, source_type="voice")
              )
                         │
                         ▼
              ┌──────────┴──────────┐
              │  LLM extract facts  │ (GPT-4.1-nano)
              │  LLM gen questions  │ (GPT-4.1-nano)
              │  Generate embeddings│ (text-embedding-3-small)
              │  Generate mnemonics │ (GPT-4.1-nano)
              └──────────┬──────────┘
                         │
                         ▼
              DB: INSERT captures, extracted_points, questions
                         │
                         ▼
              Backend sends FunctionCallResponse to Deepgram
              {capture_id, facts_count: 4, questions_count: 6}
                         │
                         ▼
              Agent speaks: "I captured 4 facts and created 6 review questions.
                            Why does this matter to you?"
                         │
                         ▼ TTS audio
              Client ◄──── Backend ◄──── Deepgram
                         │
              User speaks reflection → captured as why_it_matters
                         │
                         ▼
              Session ends
```

### 10.2 Review Mode Flow

```
Session starts
        │
        ▼
Backend: ReviewService.get_due(limit=20)
        │
        ▼
VoiceSession.review_queue = [q1, q2, q3, ..., q20]
VoiceSession.review_index = 0
        │
        ▼
Agent calls get_next_question()
        │
        ▼
Backend: dequeue q1 from review_queue
         return {question_id, question_text, question_type, mnemonic_hint}
        │
        ▼
Agent speaks question ──► TTS audio ──► Client speakers
        │
        ▼ (pause — anticipation)
User speaks answer ──► PCM audio ──► Backend ──► Deepgram STT
        │
        ▼
Deepgram: ConversationText (user transcript)
Agent calls evaluate_answer(question_id, user_answer)
        │
        ▼
Backend: ReviewService.evaluate_answer(
           EvaluateRequest(question_id=q1.id, user_answer="user said...")
         )
         → LLM (GPT-4.1-mini) evaluates
         → returns {correct_answer, score, feedback, suggested_rating}
        │
        ▼
Backend sends FunctionCallResponse to Deepgram
        │
        ▼
Agent speaks feedback + correct answer
Agent: "How did you do? Again, hard, good, or easy?"
        │
        ▼ TTS audio → Client
User speaks: "good"
        │
        ▼ PCM → Deepgram STT
Agent calls rate_question(question_id, rating=3)
        │
        ▼
Backend: ReviewService.rate(
           RateRequest(question_id=q1.id, rating=3)
         )
         → py-fsrs schedules next review
         → DB update questions, INSERT review_logs
         → returns {next_due, interval_days: 3.2, state_label: "Review"}
        │
        ▼
Agent: "Got it. Next review in 3 days."
Agent calls get_next_question() → q2
        │
        ▼
(loop repeats for q2, q3, ..., until queue empty)
        │
        ▼
get_next_question() returns {done: true}
        │
        ▼
Agent: "Great session! You reviewed 8 questions in 4 minutes."
Session ends
```

### 10.3 Teach Mode Flow

```
User selects Teach mode, enters topic: "Binary search"
        │
        ▼
Backend: TeachService.start(
           TeachStartRequest(topic="Binary search")
         )
         → LLM (GPT-4.1-nano) generates teaching plan
         → DB: INSERT teach_sessions
         → returns {session_id, total_chunks: 3, chunk_0...}
        │
        ▼
VoiceSession.teach_session_id = session_id
VoiceSession.teach_state = {chunks, current_index: 0}
        │
        ▼
Agent calls get_current_teach_chunk()
        │
        ▼
Backend returns: {
  chunk_title: "What is Binary Search?",
  chunk_content: "Binary search is an efficient algorithm...",
  chunk_analogy: "Like finding a name in a phone book...",
  recall_question: "In your own words, what is binary search?"
}
        │
        ▼
Agent speaks chunk content + analogy (conversationally)
        │
        ▼ TTS audio → Client
Agent asks recall question: "In your own words, what is binary search?"
        │
        ▼ (pause)
User speaks answer ──► PCM → Deepgram STT → transcript
        │
        ▼
Agent calls submit_teach_answer(answer="user's response...")
        │
        ▼
Backend: TeachService.respond(
           TeachRespondRequest(session_id=..., answer="user's response...")
         )
         → LLM (GPT-4.1-nano) evaluates recall answer
         → DB: advance chunk index
         → returns {feedback, score, is_complete: false,
                    chunk_title: "How Binary Search Works", ...}
        │
        ▼
Agent speaks feedback
Agent presents next chunk content + analogy
Agent asks next recall question
        │
        ▼
(loop repeats for chunk 1, 2, ...)
        │
        ▼
submit_teach_answer() returns {is_complete: true, summary: "..."}
        │
        ▼
Backend: CaptureService.process() auto-captures the lesson content
         → extracts facts, generates review questions
        │
        ▼
Agent: "Great job! You've completed the lesson on Binary Search.
        We covered 3 concepts. Your learning has been captured
        and review questions have been scheduled."
        │
        ▼
Session ends
```

---

## 11. New Files Summary

### Backend (new files)

| File | Purpose |
|---|---|
| `backend/routers/voice_ws.py` | FastAPI WebSocket endpoint `/ws/voice`. Handles connection lifecycle, bridges audio between client and Deepgram, intercepts function calls. |
| `backend/services/voice_service.py` | `VoiceSessionManager` class. Builds Deepgram config per mode, dispatches function calls to existing services, manages in-memory session state. |
| `backend/models/voice_models.py` | Pydantic models for voice WebSocket messages (inbound/outbound JSON types). |

### Backend (modified files)

| File | Change |
|---|---|
| `backend/config.py` | Add `DEEPGRAM_API_KEY`, `DEEPGRAM_ENABLED`, `MAX_VOICE_SESSION_MINUTES`, `MAX_VOICE_MINUTES_PER_DAY`, `DEEPGRAM_VOICE_MODEL`, `DEEPGRAM_STT_MODEL`, `DEEPGRAM_LLM_MODEL` settings |
| `backend/main.py` | Mount new WebSocket router. Initialize Deepgram state (just the config, no persistent client needed). |
| `backend/routers/voice.py` | Add `GET /api/voice/status` endpoint |
| `backend/requirements.txt` | Add `websockets>=12.0` (for Deepgram WSS client connection from backend) |

### Frontend (new files)

| File | Purpose |
|---|---|
| `frontend/app/voice/page.tsx` | Voice conversation page UI |
| `frontend/hooks/useVoiceAgent.ts` | Main hook: WebSocket management, mic capture, audio playback, state |
| `frontend/components/voice/VoiceOrb.tsx` | Animated orb indicator (listening/speaking/idle states) |
| `frontend/components/voice/VoiceTranscript.tsx` | Scrolling live transcript display |
| `frontend/components/voice/VoiceProgress.tsx` | Mode-specific progress bar |
| `frontend/components/voice/VoiceModeSelector.tsx` | Capture/Review/Teach tab selector |
| `frontend/lib/audio-worklet-processor.js` | AudioWorklet script for PCM mic capture at 16kHz |
| `frontend/lib/audio-playback.ts` | Streaming PCM audio playback via AudioContext |

### Frontend (modified files)

| File | Change |
|---|---|
| `frontend/components/layout/Sidebar.tsx` (or equivalent nav) | Add "Voice" link to `/voice` |
| `frontend/types/api.ts` | Add voice WebSocket message types |

### Database

| Change | Description |
|---|---|
| New table: `voice_sessions` | Tracks session starts, ends, duration, mode — for cost monitoring. Not required for core functionality. |

```sql
CREATE TABLE IF NOT EXISTS voice_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mode TEXT NOT NULL,          -- 'capture' | 'review' | 'teach'
    duration_seconds INT,
    questions_reviewed INT DEFAULT 0,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ
);
```

---

## 12. Key Architecture Decisions

| # | Decision | Rationale | Alternatives Considered |
|---|---|---|---|
| 1 | **Server-side WebSocket proxy** (client → backend → Deepgram) | Security (API key protection), function calling runs server-side with direct DB access, cost control enforcement | Direct client-to-Deepgram: simpler but exposes API key, requires HTTP round-trips for function results |
| 2 | **BYO LLM (GPT-4.1-nano)** via Deepgram | 33% cost reduction ($0.050/min vs $0.075/min), consistent model across text and voice modes | Deepgram default LLM: simpler setup but different behavior from text mode, more expensive |
| 3 | **Deepgram Voice Agent API** over OpenAI Realtime | 50% cheaper ($3/hr BYO vs ~$8.64/hr), BYO LLM flexibility, $200 free credit, function calling built-in | OpenAI Realtime: better speech-to-speech quality but 2x cost, no BYO LLM, vendor lock-in |
| 4 | **AudioWorklet for mic input** (not MediaRecorder) | Raw PCM output without transcoding overhead, exact sample rate control (16kHz), lower latency | MediaRecorder with WebM/Opus: simpler API but requires server-side transcoding to PCM, adds latency |
| 5 | **Three distinct modes** (capture/review/teach) sharing one WebSocket endpoint | Different system prompts and function sets per mode, but same connection infrastructure. Reduces code duplication. | Separate endpoints per mode: cleaner separation but more duplicated connection logic |
| 6 | **Keep existing Web Speech API voice as fallback** | Deepgram is an external dependency. Browser STT works offline. Users in regions with poor connectivity still have a voice option. | Remove old voice: simpler codebase but no fallback |
| 7 | **Function calling via Deepgram agent** (not custom orchestration) | Deepgram handles when to call functions based on conversation context. We just define the functions and handle execution. Less custom orchestration code. | Custom orchestration: more control over flow but requires building turn detection, function trigger logic, and state machine ourselves |
| 8 | **In-memory session state** (not DB-persisted) | Voice sessions are ephemeral (max 15 min). Persisting mid-conversation state adds complexity with no benefit. All important data (reviews, captures) is written to DB immediately via service calls. | DB-persisted session: enables resume-after-crash but adds latency on every state change for a 15-minute session |
| 9 | **15-minute max session** | Cost control ($0.75 max per session at $0.050/min). Aligns with research showing spaced repetition sessions should be short (5-10 min). | No limit: simpler but costs could spiral with long sessions |
| 10 | **nova-3 for STT** (not Flux directly) | Deepgram Voice Agent API uses nova-3 as its default listen model within the agent pipeline. The agent API manages Flux-level turn detection internally. We configure nova-3 with keyword boosting. | Flux: would be specified if using raw STT API, but within Voice Agent API, nova-3 is the configurable model |

---

## 13. Dependencies & Requirements

### Backend Dependencies (add to `requirements.txt`)

```
websockets>=12.0
```

No Deepgram SDK needed — the backend communicates with Deepgram via raw WebSocket using the `websockets` library. The Voice Agent API protocol is JSON + binary audio over WSS, which is straightforward to implement directly.

### Frontend Dependencies

No new npm packages. The Web Audio API (`AudioContext`, `AudioWorklet`) and WebSocket API are browser-native.

### External Services

| Service | Purpose | Cost | Free Tier |
|---|---|---|---|
| Deepgram Voice Agent API | STT + orchestration + TTS | $0.050/min (BYO LLM) | $200 credit |
| OpenAI API (existing) | LLM for agent + evaluation + extraction | Existing usage | Existing |

### Estimated Cost Per User Session

| Mode | Typical Duration | Deepgram Cost | OpenAI Cost (functions) | Total |
|---|---|---|---|---|
| Capture | 2-3 min | $0.10-0.15 | ~$0.01 (extraction) | ~$0.11-0.16 |
| Review (8 questions) | 4-5 min | $0.20-0.25 | ~$0.04 (8 evaluations) | ~$0.24-0.29 |
| Teach (3 chunks) | 5-7 min | $0.25-0.35 | ~$0.03 (plan + evals) | ~$0.28-0.38 |

At $200 free credit: **~700-1800 sessions** before any charge.
