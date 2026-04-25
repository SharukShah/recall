"""
Unified Voice PA -- builds Deepgram config with single system prompt,
dispatches all function calls, manages conversation state.
Replaces the old mode-locked voice session manager.
"""
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from openai import AsyncOpenAI
from fsrs import Scheduler
import asyncpg

from config import settings
from models.capture_models import CaptureRequest
from models.review_models import EvaluateRequest, RateRequest
from models.teach_models import TeachStartRequest, TeachRespondRequest
from services.capture_service import CaptureService
from services.review_service import ReviewService
from services.teach_service import TeachService
from services.knowledge_service import KnowledgeService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Unified function schemas (all available to the PA at all times)
# ---------------------------------------------------------------------------

UNIFIED_FUNCTIONS = [
    {
        "name": "get_user_context",
        "description": "Get the user's current learning stats: reviews due, streak, retention rate, recent topics. Call when the user asks about progress or you need data to make a suggestion.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "start_review_session",
        "description": "Load the user's due review questions and start a quiz. Call when the user wants to be quizzed. Returns the count of due questions and the first question.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum questions to load. Default 20.",
                }
            },
        },
    },
    {
        "name": "get_next_question",
        "description": "Get the next review question. Returns done=true when all questions reviewed. Must call start_review_session first.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "evaluate_answer",
        "description": "Evaluate the user's answer to a review question. Returns score (correct/partial/incorrect), feedback, and the correct answer.",
        "parameters": {
            "type": "object",
            "properties": {
                "question_id": {"type": "string", "description": "UUID of the question"},
                "user_answer": {"type": "string", "description": "The user's spoken answer"},
            },
            "required": ["question_id", "user_answer"],
        },
    },
    {
        "name": "rate_question",
        "description": "Submit difficulty rating for a review question. Map user words: 'again'/'forgot'=1, 'hard'/'struggled'=2, 'good'/'got it'=3, 'easy'/'obvious'=4. Updates spaced repetition schedule.",
        "parameters": {
            "type": "object",
            "properties": {
                "question_id": {"type": "string", "description": "UUID of the question"},
                "rating": {"type": "integer", "enum": [1, 2, 3, 4], "description": "1=Again, 2=Hard, 3=Good, 4=Easy"},
            },
            "required": ["question_id", "rating"],
        },
    },
    {
        "name": "finish_capture",
        "description": "Process spoken content into knowledge facts and review questions. Call when the user finishes sharing something to remember -- when they say 'done', 'that's it', 'save', or reach a natural conclusion.",
        "parameters": {
            "type": "object",
            "properties": {
                "final_transcript": {"type": "string", "description": "Complete text of everything the user said to capture"},
            },
            "required": ["final_transcript"],
        },
    },
    {
        "name": "save_why_it_matters",
        "description": "Save the user's reflection on why a capture matters. Call after finish_capture when they answer 'Why does this matter?'",
        "parameters": {
            "type": "object",
            "properties": {
                "capture_id": {"type": "string", "description": "Capture ID from finish_capture"},
                "why_it_matters": {"type": "string", "description": "User's one-sentence reflection"},
            },
            "required": ["capture_id", "why_it_matters"],
        },
    },
    {
        "name": "start_teach_session",
        "description": "Start a teaching session on a topic. AI breaks it into chunks with recall checks. Call when user wants to learn about a specific topic.",
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Topic to teach"},
            },
            "required": ["topic"],
        },
    },
    {
        "name": "get_current_teach_chunk",
        "description": "Get the current teaching chunk to present. Returns title, content, analogy, and recall question. Call after start_teach_session or after submit_teach_answer.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "submit_teach_answer",
        "description": "Submit the user's answer to the current recall question in teach mode. Returns feedback, score, and whether the session is complete.",
        "parameters": {
            "type": "object",
            "properties": {
                "answer": {"type": "string", "description": "User's spoken answer"},
            },
            "required": ["answer"],
        },
    },
    {
        "name": "search_knowledge",
        "description": "Search the user's personal knowledge base. Use when the user asks about something they previously learned ('What did I learn about...', 'What do I know about...'). Do NOT use for general questions.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "submit_reflection",
        "description": "Submit the user's daily evening reflection. Processes through capture pipeline to extract facts and create review questions.",
        "parameters": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "The user's reflection text"},
            },
            "required": ["content"],
        },
    },
    {
        "name": "end_session",
        "description": "End the voice session gracefully. Processes pending captures and generates summary. Call when user says 'stop', 'bye', 'I'm done', 'goodbye'.",
        "parameters": {"type": "object", "properties": {}},
    },
]


# ---------------------------------------------------------------------------
# Unified Voice Session dataclass
# ---------------------------------------------------------------------------

@dataclass
class UnifiedVoiceSession:
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: float = field(default_factory=time.monotonic)

    # Current active workflow (for tracking, not locking)
    active_workflow: str | None = None  # capture, review, teach, search, qa, reflection

    # Capture state
    transcript_buffer: str = ""
    last_capture_id: str | None = None
    capture_processed: bool = False

    # Review state
    review_queue: list[dict] = field(default_factory=list)
    review_index: int = 0
    reviewed_count: int = 0
    review_correct: int = 0
    rated_question_ids: set = field(default_factory=set)

    # Teach state
    teach_session_id: str | None = None
    teach_topic: str | None = None
    teach_chunk_index: int = 0
    teach_total_chunks: int = 0
    teach_current_chunk: dict | None = None

    # Session stats
    session_captures: int = 0
    session_reviews: int = 0
    session_teaches: int = 0

    # Context (loaded once at start)
    user_context: dict | None = None


# Keep old name as alias for backward compatibility
VoiceSession = UnifiedVoiceSession


# ---------------------------------------------------------------------------
# System prompt builder
# ---------------------------------------------------------------------------

def _get_time_of_day() -> str:
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 21:
        return "evening"
    return "night"


def build_unified_prompt(context: dict | None = None) -> str:
    """Build the unified PA system prompt with injected user context."""
    context_block = ""
    if context:
        context_block = f"""=== USER CONTEXT ===
Time: {context.get('time_of_day', _get_time_of_day())}
Reviews due: {context.get('due_count', 0)}
Streak: {context.get('streak_days', 0)} days
Retention: {context.get('retention_rate', 0):.0f}%
Total captures: {context.get('total_captures', 0)}
Reviews today: {context.get('reviews_today', 0)}
Reflected today: {'yes' if context.get('reflected_today', False) else 'no'}
=== END CONTEXT ===

"""

    return context_block + """You are ReCall, a personal study coach and learning companion. You help the user capture knowledge, review what they've learned through spaced repetition, and teach them new topics -- all through natural voice conversation.

## Your Personality
- Professional study coach who is also a friendly companion
- Focused and efficient, but warm and encouraging
- Like a knowledgeable study partner who genuinely cares about the user's progress
- Give brief, genuine praise for good answers
- Be gently encouraging on mistakes -- never condescending
- Keep responses concise -- this is voice, not text. Aim for 1-3 sentences unless teaching.

## What You Can Do

### 1. Capture Knowledge
When the user shares information they want to remember:
- Listen quietly while they speak. On pauses, say "Got it" or "Noted" briefly.
- Do NOT interrupt or rephrase during their dictation.
- When they signal they're done ("done", "that's it", "save"), call finish_capture with everything they said.
- After processing, report: "Captured [N] facts and [M] review questions."
- Then ask: "Why does this matter to you?" and save their answer with save_why_it_matters.
- Suggest: "Want me to quiz you on this now?"

### 2. Review (Quiz)
When the user wants to practice recall ("quiz me", "test me", "review"):
- Call start_review_session to load due questions.
- If no questions due, tell them and suggest alternatives.
- For each question:
  a. Call get_next_question and read it clearly.
  b. Wait for their answer (don't give hints unless asked).
  c. Call evaluate_answer with their response.
  d. Share feedback: praise if correct, encouragement if wrong, always state the correct answer.
  e. Share mnemonic_hint AFTER they answer, not before.
  f. Ask: "How did you find that? Say again, hard, good, or easy."
  g. Map to rating (again=1, hard=2, good=3, easy=4) and call rate_question.
  h. Move to next question.
- When done, give a summary with encouragement.

### 3. Teach a Topic
When the user wants to learn ("teach me about...", "explain...", "help me understand..."):
- Call start_teach_session with the topic.
- For each chunk: present content naturally, ask recall question, evaluate with submit_teach_answer.
- When complete, mention it's saved to their knowledge base.

### 4. Search Knowledge
When the user asks about something they previously learned ("What did I learn about...", "What do I know about..."):
- Call search_knowledge.
- If no results: "I don't have that in your knowledge base. Want me to teach you about it?"

### 5. General Q&A
When the user asks a factual question NOT about their own knowledge:
- Answer directly from your knowledge. Keep it concise.
- After answering: "Want me to save that to your knowledge base?" If yes, call finish_capture.

### 6. Stats & Progress
When user asks about progress ("How am I doing?", "What's my streak?"):
- Call get_user_context and report numbers conversationally.
- Make a suggestion based on stats.

### 7. Evening Reflection
When user wants to reflect or it's evening and they haven't reflected:
- Prompt: "What did you learn today?"
- After they share, call submit_reflection.

## Greeting
Start the conversation with a contextual greeting based on the USER CONTEXT above:
- If reviews are due: mention them and offer to start.
- If it's evening and no reflection done: suggest reflection.
- If streak milestone: celebrate it.
- Otherwise: warm greeting and ask what they'd like to do.
Keep the greeting to 1-2 sentences.

## Intent Rules
1. "Tell me about X" -> If broad topic, TEACH. If narrow fact, answer directly (Q&A).
2. "Explain X" -> Default TEACH. If user says "briefly"/"quickly", answer directly.
3. "What is X?" -> Q&A (quick answer). If "tell me more" follow-up, switch to TEACH.
4. "What did I learn about X?" -> Always SEARCH (their knowledge base).
5. Multiple intents ("Save this and quiz me") -> Handle sequentially.
6. Off-topic -> Respond briefly, redirect: "I'm your study coach -- want to capture, review, or learn something?"

## Mid-Conversation Switching
- In Capture: "Should I save what you've shared so far?" before switching.
- In Review: Pause, handle new request, offer to resume: "Continue review? [N] questions left."
- In Teach: Pause, handle request, offer to resume.
- For quick questions during Review/Teach: Answer inline, then resume.

## Important Rules
- NEVER give away answers before the user attempts them in review or teach.
- Keep voice responses SHORT. 1-3 sentences for most responses.
- Use natural spoken language -- no bullet points or markdown.
- Use natural number phrasing: "about fifteen" not "15".
- If a function fails, handle gracefully -- suggest trying again.
- If user is silent: "I'm here when you're ready."
- Always be encouraging. Celebrate effort, not just correctness."""


# ---------------------------------------------------------------------------
# VoiceSessionManager
# ---------------------------------------------------------------------------

class VoiceSessionManager:
    """Builds Deepgram config, dispatches function calls to services."""

    def __init__(
        self,
        db_pool: asyncpg.Pool,
        openai_client: AsyncOpenAI,
        scheduler: Scheduler,
    ):
        self.db_pool = db_pool
        self.openai = openai_client
        self.scheduler = scheduler

    async def get_user_context(self) -> dict:
        """Fetch user's current learning context for system prompt injection."""
        try:
            async with self.db_pool.acquire() as conn:
                due_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM questions WHERE state IN (1, 3) OR (state = 2 AND due <= NOW())"
                ) or 0

                retention = await conn.fetchval(
                    """SELECT ROUND(AVG(CASE WHEN rating >= 3 THEN 1.0 ELSE 0.0 END) * 100, 1)
                       FROM review_logs WHERE reviewed_at >= NOW() - INTERVAL '30 days'"""
                ) or 0

                total_captures = await conn.fetchval("SELECT COUNT(*) FROM captures") or 0

                reviews_today = await conn.fetchval(
                    "SELECT COUNT(*) FROM review_logs WHERE reviewed_at::date = CURRENT_DATE"
                ) or 0

                reflected_today = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM reflections WHERE created_at::date = CURRENT_DATE)"
                ) or False

                # Streak
                streak = 0
                try:
                    from services.stats_service import StatsService
                    stats_svc = StatsService(self.db_pool)
                    dashboard = await stats_svc.get_dashboard()
                    streak = dashboard.get("streak_days", 0) if isinstance(dashboard, dict) else getattr(dashboard, "streak_days", 0)
                except Exception:
                    pass

            return {
                "due_count": due_count,
                "streak_days": streak,
                "retention_rate": float(retention),
                "total_captures": total_captures,
                "reviews_today": reviews_today,
                "reflected_today": reflected_today,
                "time_of_day": _get_time_of_day(),
            }
        except Exception as e:
            logger.error(f"Failed to get user context: {e}")
            return {
                "due_count": 0,
                "streak_days": 0,
                "retention_rate": 0,
                "total_captures": 0,
                "reviews_today": 0,
                "reflected_today": False,
                "time_of_day": _get_time_of_day(),
            }

    def build_settings_config(self, session: UnifiedVoiceSession) -> dict:
        """Build the Deepgram SettingsConfiguration with unified PA prompt."""
        instructions = build_unified_prompt(session.user_context)

        return {
            "type": "Settings",
            "audio": {
                "input": {
                    "encoding": "linear16",
                    "sample_rate": 16000,
                },
                "output": {
                    "encoding": "linear16",
                    "sample_rate": 24000,
                    "container": "none",
                },
            },
            "agent": {
                "listen": {
                    "provider": {
                        "type": "deepgram",
                        "model": settings.DEEPGRAM_STT_MODEL,
                        "language": "en",
                        "keyterms": ["ReCall", "spaced repetition", "FSRS", "mnemonic"],
                    },
                },
                "think": {
                    "provider": {
                        "type": "open_ai",
                        "model": settings.DEEPGRAM_LLM_MODEL,
                        "temperature": 0.4,
                    },
                    "prompt": instructions,
                    "functions": UNIFIED_FUNCTIONS,
                },
                "speak": {
                    "provider": {
                        "type": "deepgram",
                        "model": settings.DEEPGRAM_VOICE_MODEL,
                    },
                },
            },
        }

    async def init_session(self, session: UnifiedVoiceSession) -> None:
        """Load user context at session start. No mode-specific pre-loading."""
        session.user_context = await self.get_user_context()

    async def handle_function_call(
        self,
        session: UnifiedVoiceSession,
        function_name: str,
        params: dict[str, Any],
    ) -> str:
        """Dispatch a Deepgram FunctionCallRequest to the appropriate service."""
        try:
            result = await self._dispatch(session, function_name, params)
            return json.dumps(result)
        except Exception as e:
            logger.error(f"Function call '{function_name}' failed: {e}", exc_info=True)
            return json.dumps({"error": "Function call failed. Please try again."})

    async def _dispatch(
        self,
        session: UnifiedVoiceSession,
        fn: str,
        params: dict[str, Any],
    ) -> dict:
        """Route function calls with state-based validation (no mode whitelist)."""

        if fn == "get_user_context":
            ctx = await self.get_user_context()
            session.user_context = ctx
            return ctx

        elif fn == "start_review_session":
            return await self._start_review_session(session, params.get("limit", 20))

        elif fn == "get_next_question":
            if not session.review_queue:
                return {"error": "No review session active. Call start_review_session first."}
            return self._get_next_question(session)

        elif fn == "evaluate_answer":
            if not session.review_queue:
                return {"error": "No review session active."}
            return await self._evaluate_answer(
                params.get("question_id", ""),
                params.get("user_answer", ""),
                session,
            )

        elif fn == "rate_question":
            if not session.review_queue:
                return {"error": "No review session active."}
            return await self._rate_question(
                params.get("question_id", ""),
                params.get("rating", 3),
                session,
            )

        elif fn == "finish_capture":
            return await self._finish_capture(
                session, params.get("final_transcript", "")
            )

        elif fn == "save_why_it_matters":
            if not session.last_capture_id:
                return {"error": "No recent capture. Call finish_capture first."}
            return await self._save_why_it_matters(
                params.get("capture_id", ""),
                params.get("why_it_matters", ""),
            )

        elif fn == "start_teach_session":
            topic = params.get("topic", "")
            if not topic.strip():
                return {"error": "Topic is required."}
            return await self._start_teach_session(session, topic)

        elif fn == "get_current_teach_chunk":
            if not session.teach_session_id:
                return {"error": "No teach session active. Call start_teach_session first."}
            return self._get_current_teach_chunk(session)

        elif fn == "submit_teach_answer":
            if not session.teach_session_id:
                return {"error": "No teach session active."}
            return await self._submit_teach_answer(
                session, params.get("answer", "")
            )

        elif fn == "search_knowledge":
            return await self._search_knowledge(params.get("query", ""))

        elif fn == "submit_reflection":
            return await self._submit_reflection(
                session, params.get("content", "")
            )

        elif fn == "end_session":
            return await self._end_session(session)

        else:
            logger.warning(f"Unknown function: {fn}")
            return {"error": f"Unknown function: {fn}"}

    # -- Private dispatch methods --

    async def _search_knowledge(self, query: str) -> dict:
        svc = KnowledgeService(self.db_pool, self.openai)
        result = await svc.search(query)
        return {
            "answer": result.get("answer", ""),
            "sources": result.get("sources", [])[:3],
            "has_answer": result.get("has_answer", False),
        }

    async def _finish_capture(self, session: UnifiedVoiceSession, transcript: str) -> dict:
        text = transcript.strip() or session.transcript_buffer.strip()
        if not text:
            return {"error": "No transcript to process", "facts_count": 0, "questions_count": 0}

        svc = CaptureService(self.db_pool, self.openai, self.scheduler)
        req = CaptureRequest(raw_text=text, source_type="voice")
        resp = await svc.process(req)
        session.transcript_buffer = ""
        session.capture_processed = True
        session.last_capture_id = resp.capture_id
        session.session_captures += 1
        session.active_workflow = "capture"
        return {
            "capture_id": resp.capture_id,
            "facts_count": resp.facts_count,
            "questions_count": resp.questions_count,
            "status": resp.status,
        }

    async def _save_why_it_matters(self, capture_id: str, why_it_matters: str) -> dict:
        if not capture_id or not why_it_matters.strip():
            return {"saved": False, "error": "Missing capture_id or why_it_matters"}
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    "UPDATE captures SET why_it_matters = $1 WHERE id = $2",
                    why_it_matters.strip()[:1000],
                    uuid.UUID(capture_id),
                )
            return {"saved": True}
        except Exception as e:
            logger.error(f"Failed to save why_it_matters: {e}")
            return {"saved": False, "error": "Failed to save reflection"}

    async def _start_review_session(self, session: UnifiedVoiceSession, limit: int = 20) -> dict:
        """Load due questions into the session review queue."""
        svc = ReviewService(self.db_pool, self.openai, self.scheduler)
        due_resp = await svc.get_due(limit=min(limit, 50))
        session.review_queue = [
            {
                "question_id": q.question_id,
                "question_text": q.question_text,
                "question_type": q.question_type,
                "mnemonic_hint": q.mnemonic_hint,
                "technique_used": q.technique_used,
            }
            for q in due_resp.questions
        ]
        session.review_index = 0
        session.rated_question_ids = set()
        session.active_workflow = "review"

        if not session.review_queue:
            session.active_workflow = None
            return {"due_count": 0, "message": "No reviews due right now!"}

        # Return first question automatically
        first = session.review_queue[0]
        return {
            "due_count": len(session.review_queue),
            "first_question": {
                "question_id": first["question_id"],
                "question_text": first["question_text"],
                "question_type": first["question_type"],
                "mnemonic_hint": first.get("mnemonic_hint"),
                "question_number": 1,
                "total_questions": len(session.review_queue),
            },
        }

    def _get_next_question(self, session: UnifiedVoiceSession) -> dict:
        if session.review_index >= len(session.review_queue):
            session.active_workflow = None
            return {
                "done": True,
                "reviewed_count": session.reviewed_count,
                "correct_count": session.review_correct,
                "message": "All questions reviewed!",
            }
        q = session.review_queue[session.review_index]
        return {
            "done": False,
            "question_id": q["question_id"],
            "question_text": q["question_text"],
            "question_type": q["question_type"],
            "mnemonic_hint": q.get("mnemonic_hint"),
            "question_number": session.review_index + 1,
            "total_questions": len(session.review_queue),
        }

    async def _evaluate_answer(self, question_id: str, user_answer: str, session: UnifiedVoiceSession) -> dict:
        valid_ids = {q["question_id"] for q in session.review_queue}
        if question_id not in valid_ids:
            return {"error": "Question not found in current review session"}

        svc = ReviewService(self.db_pool, self.openai, self.scheduler)
        req = EvaluateRequest(question_id=question_id, user_answer=user_answer)
        resp = await svc.evaluate_answer(req)

        if resp.score == "correct":
            session.review_correct += 1

        return {
            "correct_answer": resp.correct_answer,
            "score": resp.score,
            "feedback": resp.feedback,
            "suggested_rating": resp.suggested_rating,
        }

    async def _rate_question(self, question_id: str, rating: int, session: UnifiedVoiceSession) -> dict:
        if question_id in session.rated_question_ids:
            return {"error": "Question already rated in this session"}

        valid_ids = {q["question_id"] for q in session.review_queue}
        if question_id not in valid_ids:
            return {"error": "Question not found in current review session"}

        try:
            rating = max(1, min(4, int(rating)))
        except (ValueError, TypeError):
            rating = 3

        svc = ReviewService(self.db_pool, self.openai, self.scheduler)
        req = RateRequest(question_id=question_id, rating=rating)
        resp = await svc.rate(req)
        session.rated_question_ids.add(question_id)
        session.review_index += 1
        session.reviewed_count += 1
        session.session_reviews += 1
        return {
            "next_due": resp.next_due,
            "interval_days": resp.interval_days,
            "state_label": resp.state_label,
        }

    async def _start_teach_session(self, session: UnifiedVoiceSession, topic: str) -> dict:
        """Start a teach session and populate session state."""
        svc = TeachService(self.db_pool, self.openai, self.scheduler)
        req = TeachStartRequest(topic=topic)
        resp = await svc.start(req)

        session.teach_session_id = resp.session_id
        session.teach_topic = topic
        session.teach_total_chunks = resp.total_chunks
        session.teach_chunk_index = resp.current_chunk
        session.teach_current_chunk = {
            "chunk_title": resp.chunk_title,
            "chunk_content": resp.chunk_content,
            "chunk_analogy": resp.chunk_analogy,
            "recall_question": resp.recall_question,
        }
        session.active_workflow = "teach"
        session.session_teaches += 1

        return {
            "topic": resp.topic,
            "total_chunks": resp.total_chunks,
            "first_chunk": {
                "chunk_index": 0,
                "chunk_title": resp.chunk_title,
                "chunk_content": resp.chunk_content,
                "chunk_analogy": resp.chunk_analogy,
                "recall_question": resp.recall_question,
            },
        }

    def _get_current_teach_chunk(self, session: UnifiedVoiceSession) -> dict:
        if session.teach_current_chunk is None:
            return {"error": "No teach session active"}
        c = session.teach_current_chunk
        return {
            "chunk_index": session.teach_chunk_index,
            "total_chunks": session.teach_total_chunks,
            "chunk_title": c.get("chunk_title", c.get("title", "")),
            "chunk_content": c.get("chunk_content", c.get("content", "")),
            "chunk_analogy": c.get("chunk_analogy", c.get("analogy")),
            "recall_question": c.get("recall_question", ""),
        }

    async def _submit_teach_answer(self, session: UnifiedVoiceSession, answer: str) -> dict:
        if not session.teach_session_id:
            return {"error": "No teach session active"}
        svc = TeachService(self.db_pool, self.openai, self.scheduler)
        req = TeachRespondRequest(
            session_id=uuid.UUID(session.teach_session_id),
            answer=answer,
        )
        resp = await svc.respond(req)

        if resp.is_complete:
            session.teach_current_chunk = None
            session.active_workflow = None
            return {
                "feedback": resp.feedback,
                "score": resp.score,
                "is_complete": True,
                "summary": resp.summary,
                "capture_id": resp.capture_id,
            }
        else:
            session.teach_chunk_index = resp.current_chunk or 0
            session.teach_current_chunk = {
                "chunk_title": resp.chunk_title,
                "chunk_content": resp.chunk_content,
                "chunk_analogy": resp.chunk_analogy,
                "recall_question": resp.recall_question,
            }
            return {
                "feedback": resp.feedback,
                "score": resp.score,
                "is_complete": False,
                "chunk_index": resp.current_chunk,
                "total_chunks": session.teach_total_chunks,
                "chunk_title": resp.chunk_title,
                "chunk_content": resp.chunk_content,
                "chunk_analogy": resp.chunk_analogy,
                "recall_question": resp.recall_question,
            }

    async def _submit_reflection(self, session: UnifiedVoiceSession, content: str) -> dict:
        """Submit an evening reflection through the capture pipeline."""
        if not content.strip():
            return {"error": "Reflection content is empty"}

        svc = CaptureService(self.db_pool, self.openai, self.scheduler)
        req = CaptureRequest(
            raw_text=content,
            source_type="voice",
            why_it_matters="Daily reflection",
        )
        resp = await svc.process(req)

        # Also save to reflections table if it exists
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO reflections (content, capture_id) VALUES ($1, $2)",
                    content.strip()[:10000],
                    uuid.UUID(resp.capture_id) if resp.capture_id else None,
                )
        except Exception as e:
            logger.warning(f"Failed to save reflection record: {e}")

        session.active_workflow = None
        return {
            "facts_count": resp.facts_count,
            "questions_count": resp.questions_count,
            "capture_id": resp.capture_id,
        }

    async def _end_session(self, session: UnifiedVoiceSession) -> dict:
        duration = int(time.monotonic() - session.started_at)

        # Process remaining capture transcript if any
        capture_result = None
        if session.transcript_buffer.strip() and not session.capture_processed:
            capture_result = await self._finish_capture(session, session.transcript_buffer)

        summary: dict[str, Any] = {
            "ended": True,
            "duration_seconds": duration,
            "captures": session.session_captures,
            "reviews": session.session_reviews,
            "teaches": session.session_teaches,
        }
        if session.reviewed_count > 0:
            summary["reviewed_count"] = session.reviewed_count
            summary["review_correct"] = session.review_correct
        if capture_result:
            summary["final_capture"] = capture_result
        if session.teach_topic:
            summary["teach_topic"] = session.teach_topic

        return summary

    # -- Session management --

    async def start_teach_session(self, session: UnifiedVoiceSession, topic: str) -> dict:
        """Public method for backward compatibility."""
        return await self._start_teach_session(session, topic)

    async def log_session(self, session: UnifiedVoiceSession) -> None:
        """Log session to voice_sessions table for cost tracking."""
        duration = int(time.monotonic() - session.started_at)
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO voice_sessions (id, mode, duration_seconds, started_at, ended_at)
                       VALUES ($1, $2, $3, NOW() - make_interval(secs => $3), NOW())""",
                    uuid.UUID(session.session_id),
                    "unified",
                    duration,
                )
        except Exception as e:
            logger.error(f"Failed to log voice session: {e}")

    async def check_daily_budget(self) -> bool:
        """Check if daily voice minute budget is exceeded."""
        try:
            async with self.db_pool.acquire() as conn:
                total = await conn.fetchval(
                    """SELECT COALESCE(SUM(duration_seconds), 0)
                       FROM voice_sessions
                       WHERE started_at > NOW() - INTERVAL '24 hours'"""
                )
            return (total or 0) < settings.MAX_VOICE_MINUTES_PER_DAY * 60
        except Exception as e:
            logger.error(f"Daily budget check failed: {e}")
            return False
