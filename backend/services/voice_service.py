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
from services.capture_service import CaptureService
from services.review_service import ReviewService
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
        "description": "Start a review quiz. Set recent_only=true to quiz ONLY on the most recent capture (use when user says 'review this', 'quiz me on what I just learned', 'review recent', or any review request after a capture). Set recent_only=false to load all due questions from spaced repetition.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum questions to load. Default 20. Only used when recent_only=false.",
                },
                "recent_only": {
                    "type": "boolean",
                    "description": "If true, quiz only on the most recently captured content. Default false.",
                }
            },
        },
    },
    {
        "name": "evaluate_answer",
        "description": "MANDATORY: Call this for EVERY user answer during a review session. You MUST call this BEFORE responding to the user. NEVER say 'Actually', 'correct', 'not quite', or evaluate the answer yourself. After this returns, follow the instruction field EXACTLY — say the feedback then read the next question. NEVER say 'Want me to capture?' or ask any question. Just give feedback and read the next question.",
        "parameters": {
            "type": "object",
            "properties": {
                "question_id": {"type": "string", "description": "The question_id from the current review question (from start_review_session or the previous evaluate_answer response)"},
                "user_answer": {"type": "string", "description": "Exactly what the user said as their answer"},
            },
            "required": ["question_id", "user_answer"],
        },
    },
    {
        "name": "next_question",
        "description": "Get the next review question. Call when user says 'next', 'skip', 'continue', 'move on', or 'mark it done'. After this returns, read the question text from the response. NEVER offer to capture or ask any question — just read the next question.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "finish_capture",
        "description": "Save knowledge from the conversation into the user's knowledge base, generating facts and review questions. When the user says 'capture it', 'save that', or 'done', summarize the KEY FACTS from your conversation and pass them as final_transcript. Do NOT ask the user to repeat what was discussed -- you have the conversation context.",
        "parameters": {
            "type": "object",
            "properties": {
                "final_transcript": {"type": "string", "description": "A clear, factual summary of the knowledge to capture from the conversation"},
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
    # -- Interview Prep Functions --
    {
        "name": "start_mock_interview",
        "description": "Start a mock technical interview session. The voice agent switches to interviewer persona. Ask questions, evaluate answers, give follow-ups. Call when user says 'mock interview', 'interview practice', 'interview me'.",
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "enum": ["python", "dsa", "system_design", "oop", "web_dev", "databases", "behavioral"],
                    "description": "Interview topic area",
                },
                "difficulty": {
                    "type": "string",
                    "enum": ["easy", "medium", "hard"],
                    "description": "Question difficulty. Default medium.",
                },
                "duration_minutes": {
                    "type": "integer",
                    "enum": [15, 30, 45],
                    "description": "Interview length in minutes. Default 30.",
                },
            },
            "required": ["topic"],
        },
    },
    {
        "name": "submit_interview_answer",
        "description": "MANDATORY during mock interview: submit the candidate's answer for evaluation. Returns score, feedback, and optionally a follow-up question.",
        "parameters": {
            "type": "object",
            "properties": {
                "interview_id": {"type": "string"},
                "question_order": {"type": "integer"},
                "user_answer": {"type": "string"},
            },
            "required": ["interview_id", "question_order", "user_answer"],
        },
    },
    {
        "name": "end_mock_interview",
        "description": "End the mock interview and get the performance summary. Call when user says 'end interview', 'I'm done', or time is up.",
        "parameters": {
            "type": "object",
            "properties": {
                "interview_id": {"type": "string"},
            },
            "required": ["interview_id"],
        },
    },
    {
        "name": "start_focus_review",
        "description": "Start a review session targeting specific weak categories only. Call when user says 'practice my weak areas', 'focus on DSA', 'review weak topics'.",
        "parameters": {
            "type": "object",
            "properties": {
                "categories": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of categories to focus on (e.g., ['dsa', 'oop'])",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max questions. Default 10.",
                },
            },
            "required": ["categories"],
        },
    },
    {
        "name": "practice_behavioral",
        "description": "Start behavioral interview practice. Asks a behavioral question, user answers, AI evaluates using STAR framework. Call when user says 'practice behavioral', 'behavioral interview', 'STAR practice'.",
        "parameters": {
            "type": "object",
            "properties": {
                "competency": {
                    "type": "string",
                    "enum": ["leadership", "teamwork", "conflict_resolution", "problem_solving", "communication", "adaptability", "initiative", "failure_handling"],
                    "description": "Which competency to practice. Random if omitted.",
                },
            },
        },
    },
    {
        "name": "evaluate_behavioral_answer",
        "description": "Evaluate a behavioral answer using STAR framework. Call after the user answers a behavioral question.",
        "parameters": {
            "type": "object",
            "properties": {
                "competency": {"type": "string"},
                "question": {"type": "string"},
                "user_answer": {"type": "string"},
            },
            "required": ["competency", "question", "user_answer"],
        },
    },
    {
        "name": "capture_behavioral_story",
        "description": "Capture a behavioral story from conversation. Extracts STAR components automatically. Call when user finishes telling a story and wants to save it.",
        "parameters": {
            "type": "object",
            "properties": {
                "narrative": {"type": "string", "description": "The full story narrative"},
                "competency": {"type": "string", "description": "Which competency this story demonstrates"},
            },
            "required": ["narrative", "competency"],
        },
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
    review_awaiting_answer: bool = False  # True when agent asked a question, waiting for user
    review_current_question_id: str | None = None  # Track current question for auto-eval
    review_teaching_retries: dict = field(default_factory=dict)  # question_id -> retry count

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

    # Interview state
    interview_id: str | None = None
    interview_topic: str | None = None
    interview_question_order: int = 0
    interview_awaiting_answer: bool = False
    interview_awaiting_follow_up: bool = False

    # Behavioral state
    behavioral_question: str | None = None
    behavioral_competency: str | None = None
    behavioral_awaiting_answer: bool = False


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
- Focused, efficient, warm, and encouraging
- Keep responses concise -- this is voice, not text. Aim for 1-2 sentences unless teaching.
- Do NOT add filler words like "Great!", "Exactly!", "Got it" before every response.

## What You Can Do

### 1. Capture Knowledge
When the user says "capture it", "save that", or "done":
- You ALREADY HAVE the conversation context. Summarize the key facts yourself and call finish_capture.
- Do NOT ask "What do you want to capture?" -- use what was just discussed.
- After processing, report: "Captured [N] facts and [M] review questions."
- Do NOT ask "Why does this matter to you?" -- automatically call save_why_it_matters with why_it_matters="Interview preparation" using the capture_id from finish_capture.
- Then offer: "Want me to quiz you on this?"

When the user is dictating or explaining something and says something FACTUALLY WRONG:
- Gently interrupt and correct them: "Actually, [correction]. Want me to capture the corrected version?"
- Do NOT silently record incorrect information.

### 2. Review (Quiz)
When the user wants to practice recall ("quiz me", "test me", "review"):
- If the user JUST captured something → call start_review_session with recent_only=true.
- Otherwise → call start_review_session with recent_only=false.

**STRICT REVIEW LOOP — follow EXACTLY:**
1. Read the question text to the user.
2. Wait for the user to finish answering. Do NOT interrupt or respond while they are speaking.
3. IMMEDIATELY call evaluate_answer(question_id, user_answer) with EXACTLY what they said. Do this BEFORE saying ANYTHING. You MUST NOT speak before calling this function.
4. WAIT for the evaluate_answer response. Read ONLY the feedback and instruction from the response. Do NOT add your own evaluation.
5. The response contains next_question — read it immediately. If done=true, give the summary.
6. Repeat from step 2.

**ABSOLUTE RULES FOR REVIEW MODE:**
- You are NOT allowed to evaluate answers yourself. NEVER say "Actually...", "That's right", "Not quite", "Correct", or ANY judgment before calling evaluate_answer.
- You are NOT allowed to say "Want me to capture/save that?" during review. NEVER offer to capture during review.
- You are NOT allowed to ask "Ready for the next question?" or "Would you like to continue?". Just read the next question.
- If the user says "next", "skip", or "move on" → call next_question.
- If you accidentally responded without calling evaluate_answer → call next_question immediately to advance.
- REMEMBER: The user's speech may contain STT artifacts (e.g., "ash" means "hash", "curly braces" might sound like "braces"). Pass the raw speech to evaluate_answer — the backend handles interpretation.

### 3. Teach a Topic
When the user wants to learn ("teach me about...", "explain...", "help me understand..."):
- Teach them DIRECTLY from your own knowledge. Do NOT call any API function.
- Break complex topics into digestible pieces. Explain one concept at a time.
- Use analogies and examples to make concepts stick.
- After explaining a concept, ask a quick recall question to check understanding.
- If they get it wrong, re-explain differently. If right, move on.
- When the teaching is done, offer: "Want me to capture the key points for your review?"
- If they say yes, summarize what you taught and call finish_capture.

### 4. Search Knowledge
When the user asks about something they previously learned ("What did I learn about...", "What do I know about..."):
- Call search_knowledge.
- If no results: "I don't have that in your knowledge base. Want me to teach you about it?"

### 5. General Q&A
When the user asks a factual question NOT about their own knowledge:
- Answer directly from your knowledge. Keep it concise.
- After answering: "Want me to save that to your knowledge base?" If yes, summarize and call finish_capture.

### 6. Stats & Progress
When user asks about progress ("How am I doing?", "What's my streak?"):
- Call get_user_context and report numbers conversationally.

### 7. Evening Reflection
When user wants to reflect or it's evening and they haven't reflected:
- Prompt: "What did you learn today?"
- After they share, call submit_reflection.

## Greeting
Start with a brief contextual greeting based on USER CONTEXT:
- If reviews are due: mention them and offer to start. When the user says "yes", "yeah", "sure", or any affirmative → IMMEDIATELY call start_review_session(recent_only=false). Do NOT ask follow-up questions like "all due or specific topic?".
- If it's evening and no reflection done: suggest reflection.
- If no reviews due and user is preparing for interviews: suggest a mock interview or behavioral practice.
- Otherwise: warm greeting, ask what they'd like to do.
One sentence only.

## Intent Rules
1. "Tell me about X" / "Explain X" / "Teach me X" -> Teach directly (no API call).
2. "What is X?" -> Quick answer. If "tell me more", teach in depth.
3. "What did I learn about X?" -> Always SEARCH (their knowledge base).
4. "Capture it" / "Save that" -> Summarize conversation and call finish_capture immediately.
5. "Review" / "Quiz me" after a capture -> start_review_session with recent_only=true.
6. "Review" / "Quiz me" with no recent capture -> start_review_session with recent_only=false.
7. "Review what I just learned" / "Quiz me on this" -> ALWAYS recent_only=true.
8. If the user corrects something they said ("actually it's X", "I meant X") -> Re-capture with corrected content by calling finish_capture again with the corrected facts.
9. Multiple intents -> Handle sequentially.
10. Off-topic -> Brief response, redirect to learning.

## Mid-Conversation Switching
- In Review: Pause, handle new request, offer to resume: "Continue review? [N] questions left."
- For quick questions during Review: Answer inline, then resume.

### 8. Mock Interview
When the user wants interview practice ("mock interview", "interview me on DSA"):
- Call start_mock_interview with topic, difficulty, duration.
- SWITCH PERSONA: You are now a Senior Engineer Interviewer. Professional, probing, neutral.
- Do NOT give hints or help during the interview. Let the candidate think.
- After each answer, call submit_interview_answer. Read feedback briefly.
- If follow_up_question is returned, ask it before moving to the next question.
- When done or user says "end interview", call end_mock_interview and read the summary.
- After interview, switch back to your normal ReCall persona.

### 9. Focus Review
When user says "practice my weak areas" or "focus on [topic]":
- Call start_focus_review with the specified categories.
- Follow the same review loop as normal review (evaluate_answer, next_question).

### 10. Behavioral Interview Practice
When user wants behavioral practice ("behavioral interview", "STAR practice"):
- Call practice_behavioral with optional competency.
- Read the behavioral question.
- After they answer, call evaluate_behavioral_answer.
- Give detailed STAR feedback: what had clear Situation, what lacked specific Action, etc.
- Offer: "Want to save this story?" → call capture_behavioral_story.

## CRITICAL RULES
- NEVER give away answers before the user attempts them in review.
- Keep voice responses SHORT. 1-2 sentences max. Up to 4 sentences only when teaching.
- Use natural spoken language -- no bullet points or markdown.
- If a function fails, handle gracefully -- suggest trying again.
- If user is silent: "I'm here when you're ready."

## FORBIDDEN PHRASES DURING REVIEW (never say these)
- "Want me to capture/save this?"
- "Would you like to continue?"
- "Want me to explain more?"
- "Ready for the next question?"
- "Want me to give you an example?"
- "Want me to teach you?"
- "How can I assist you?"
- "Let me know if you'd like to..."
- "Alright, let me know..."
- "Want to continue with another topic?"
Instead: just give brief feedback and read the next question.

## REVIEW MODE RULES (HIGHEST PRIORITY)
When a review session is active, these rules OVERRIDE everything else:
1. EVERY user response after a question is an ANSWER. Call evaluate_answer IMMEDIATELY. Do NOT speak first.
2. NEVER self-evaluate. NEVER say "Actually", "That's right", "Correct", "Exactly", "Not quite", or ANY judgment without calling evaluate_answer first.
3. NEVER offer to capture or save during review. You are in REVIEW mode, not CAPTURE mode.
4. NEVER ask ANY question starting with "Want me to...?", "Would you like to...?", "Ready for...?". Just proceed.
5. After evaluate_answer returns: read the feedback field (1 sentence), then IMMEDIATELY read the next_question text from the response. Do NOT add anything else. Do NOT ask if they want to continue.
6. When evaluate_answer returns retry_question: follow the instruction field exactly. Teach briefly, ask them to explain back, then call evaluate_answer AGAIN with same question_id.
7. When user says "skip", "next", "move on", "mark it done" → call next_question.
8. If you accidentally spoke without calling evaluate_answer → call next_question immediately.
9. VOICE STYLE: Speak directly to the user. Keep feedback to ONE sentence. Then read next question.
10. The review session ends ONLY when evaluate_answer returns done=true. Do NOT end it yourself. NEVER say "all done" or stop reviewing unless done=true.
11. YOUR JOB IN REVIEW: feedback → next question → wait → evaluate → repeat. Nothing else. No offers, no questions, no suggestions.
12. The instruction field in evaluate_answer response tells you EXACTLY what to say. Follow it word for word."""


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
                        "keyterms": ["ReCall", "spaced repetition", "FSRS", "mnemonic",
                                      "VectorDB", "vector database", "embedding", "embeddings",
                                      "PostgreSQL", "FastAPI", "Python", "JavaScript",
                                      "API", "REST", "WebSocket", "LLM", "GPT", "RAG"],
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

    async def server_side_evaluate(
        self,
        session: UnifiedVoiceSession,
        user_text: str,
    ) -> dict | None:
        """Auto-evaluate a user's answer server-side during review mode.
        Called by the WebSocket handler when it detects the user is answering
        a review question but the LLM didn't call evaluate_answer.
        Returns the evaluation result dict, or None if not in review mode."""
        if not session.review_awaiting_answer:
            return None
        if not session.review_current_question_id:
            return None
        if not user_text.strip():
            return None

        # Short utterances like "yes", "next", "no" are not answers
        stripped = user_text.strip().lower()
        # Exact match skip phrases
        skip_phrases = {"yes", "no", "yeah", "yep", "nope", "next", "next question",
                        "continue", "move on", "skip", "ok", "okay", "right",
                        "got it", "i see", "understood", "makes sense", "sure",
                        "uh huh", "mm hmm", "hmm", "hm", "uh", "that's right",
                        "alright", "all right", "i got it", "i understand"}
        if stripped.rstrip("!.,") in skip_phrases or stripped in skip_phrases:
            return None

        # Keyword-based skip: if utterance contains navigation words and is short, skip it
        nav_keywords = {"next", "skip", "move on", "continue", "pass", "go ahead"}
        if len(stripped.split()) <= 6 and any(kw in stripped for kw in nav_keywords):
            return None

        # Very short utterances (< 3 words) are likely not real answers
        if len(stripped.split()) < 3:
            return None

        logger.info(f"Server-side auto-eval: question={session.review_current_question_id}, answer={user_text[:80]}")
        result = await self._evaluate_answer(
            session.review_current_question_id,
            user_text,
            session,
        )
        return result

    async def _dispatch(
        self,
        session: UnifiedVoiceSession,
        fn: str,
        params: dict[str, Any],
    ) -> dict:
        """Route function calls with state-based validation."""

        if fn == "get_user_context":
            ctx = await self.get_user_context()
            session.user_context = ctx
            return ctx

        elif fn == "start_review_session":
            # Auto-detect: if there's a recent capture in this session, default to reviewing it
            # unless the LLM explicitly passes recent_only=false
            recent_only = params.get("recent_only")
            if recent_only is True:
                return await self._review_recent_capture(session)
            if recent_only is False:
                return await self._start_review_session(session, params.get("limit", 20))
            # recent_only not specified — auto-decide based on session state
            if session.last_capture_id:
                return await self._review_recent_capture(session)
            return await self._start_review_session(session, params.get("limit", 20))

        elif fn in ("get_next_question", "next_question"):
            # Escape hatch: auto-rates skipped question and advances
            if not session.review_queue:
                return {"error": "No review session active. Call start_review_session first."}
            return await self._get_next_question(session)

        elif fn == "evaluate_answer":
            if not session.review_queue:
                return {"error": "No review session active."}
            return await self._evaluate_answer(
                params.get("question_id", ""),
                params.get("user_answer", ""),
                session,
            )

        elif fn == "finish_capture":
            # Block capture during active review — LLM should not offer capture mid-review
            if session.active_workflow == "review" and session.review_queue:
                logger.warning("Blocked finish_capture during active review session")
                remaining = len(session.review_queue) - session.review_index
                return {
                    "error": "Cannot capture during review. You are in review mode.",
                    "instruction": f"Continue the review. {remaining} questions remaining. Read the next question.",
                }
            return await self._finish_capture(
                session, params.get("final_transcript", "")
            )

        elif fn == "save_why_it_matters":
            if session.active_workflow == "review" and session.review_queue:
                return {"error": "Cannot save during review. Continue the review."}
            if not session.last_capture_id:
                return {"error": "No recent capture. Call finish_capture first."}
            return await self._save_why_it_matters(
                params.get("capture_id", ""),
                params.get("why_it_matters", ""),
            )

        elif fn == "search_knowledge":
            return await self._search_knowledge(params.get("query", ""))

        elif fn == "submit_reflection":
            return await self._submit_reflection(
                session, params.get("content", "")
            )

        elif fn == "end_session":
            return await self._end_session(session)

        elif fn == "start_mock_interview":
            return await self._start_mock_interview(session, params)

        elif fn == "submit_interview_answer":
            return await self._submit_interview_answer(session, params)

        elif fn == "end_mock_interview":
            return await self._end_mock_interview(session, params)

        elif fn == "start_focus_review":
            return await self._start_focus_review(session, params)

        elif fn == "practice_behavioral":
            return await self._practice_behavioral(session, params)

        elif fn == "evaluate_behavioral_answer":
            return await self._evaluate_behavioral_answer(session, params)

        elif fn == "capture_behavioral_story":
            return await self._capture_behavioral_story(session, params)

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
        """Load due questions into the session review queue.
        If a review session is already active, return the current question instead of resetting."""
        # Don't reset an active session — return current question
        if session.review_queue and session.review_index < len(session.review_queue):
            q = session.review_queue[session.review_index]
            session.review_awaiting_answer = True
            session.review_current_question_id = q["question_id"]
            remaining = len(session.review_queue) - session.review_index
            qnum = session.review_index + 1
            qtotal = len(session.review_queue)
            return {
                "due_count": len(session.review_queue),
                "session_already_active": True,
                "instruction": f"Review already active. Say: 'Question {qnum} of {qtotal}: {q['question_text']}' — NOTHING ELSE.",
                "remaining": remaining,
                "first_question": {
                    "question_id": q["question_id"],
                    "question_text": q["question_text"],
                    "question_type": q["question_type"],
                    "mnemonic_hint": q.get("mnemonic_hint"),
                    "question_number": session.review_index + 1,
                    "total_questions": len(session.review_queue),
                },
            }

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
            session.review_awaiting_answer = False
            session.review_current_question_id = None
            return {"due_count": 0, "message": "No reviews due right now! You could try a mock interview, practice behavioral questions, or capture new content."}

        # Return first question automatically
        first = session.review_queue[0]
        session.review_awaiting_answer = True
        session.review_current_question_id = first["question_id"]
        total = len(session.review_queue)
        return {
            "due_count": total,
            "instruction": f"Say: 'You have {total} reviews. Question 1 of {total}: {first['question_text']}' — NOTHING ELSE. Wait for answer, then call evaluate_answer.",
            "first_question": {
                "question_id": first["question_id"],
                "question_text": first["question_text"],
                "question_type": first["question_type"],
                "mnemonic_hint": first.get("mnemonic_hint"),
                "question_number": 1,
                "total_questions": len(session.review_queue),
            },
        }

    async def _get_next_question(self, session: UnifiedVoiceSession) -> dict:
        # Always advance past the current question when next_question is called
        current_idx = session.review_index
        if current_idx < len(session.review_queue):
            current_q = session.review_queue[current_idx]
            qid = current_q["question_id"]
            if qid not in session.rated_question_ids:
                # Auto-rate with rating 4 (Easy) — user skipped = already knows it
                session.rated_question_ids.add(qid)
                # Schedule the auto-rate in background (fire-and-forget)
                import asyncio
                asyncio.create_task(self._auto_rate_question(qid, 4))
            # ALWAYS advance index — whether rated already (teaching mode) or not (skip)
            session.review_index += 1
            session.reviewed_count += 1
            session.session_reviews += 1

        if session.review_index >= len(session.review_queue):
            # Check if more due questions exist before declaring done
            more = await self._reload_due_questions(session)
            if more:
                q = session.review_queue[session.review_index]
                session.review_awaiting_answer = True
                session.review_current_question_id = q["question_id"]
                qnum = session.review_index + 1
                qtotal = len(session.review_queue)
                return {
                    "done": False,
                    "instruction": f"More questions due. Say: 'Next question, number {qnum} of {qtotal}: {q['question_text']}' — NOTHING ELSE.",
                    "question_id": q["question_id"],
                    "question_text": q["question_text"],
                    "question_type": q["question_type"],
                    "mnemonic_hint": q.get("mnemonic_hint"),
                    "question_number": qnum,
                    "total_questions": qtotal,
                }
            session.active_workflow = None
            session.review_awaiting_answer = False
            session.review_current_question_id = None
            return {
                "done": True,
                "reviewed_count": session.reviewed_count,
                "correct_count": session.review_correct,
                "message": "All questions reviewed!",
            }
        q = session.review_queue[session.review_index]
        session.review_awaiting_answer = True
        session.review_current_question_id = q["question_id"]
        qnum = session.review_index + 1
        qtotal = len(session.review_queue)
        return {
            "done": False,
            "instruction": f"Say: 'Question {qnum} of {qtotal}: {q['question_text']}' — NOTHING ELSE. Wait for answer, then call evaluate_answer.",
            "question_id": q["question_id"],
            "question_text": q["question_text"],
            "question_type": q["question_type"],
            "mnemonic_hint": q.get("mnemonic_hint"),
            "question_number": qnum,
            "total_questions": qtotal,
        }

    async def _evaluate_answer(self, question_id: str, user_answer: str, session: UnifiedVoiceSession) -> dict:
        """Evaluate, auto-rate via FSRS, and either teach (poor) or advance (good)."""
        session.review_awaiting_answer = False
        session.review_current_question_id = None
        # Clear answer buffer and cancel pending auto-eval to prevent race
        if hasattr(session, '_answer_buffer'):
            session._answer_buffer = ""
        if hasattr(session, '_auto_eval_task') and session._auto_eval_task and not session._auto_eval_task.done():
            session._auto_eval_task.cancel()
        # Set cooldown to ignore late-arriving speech fragments from previous answer
        session._eval_cooldown_until = time.monotonic() + 4.0
        valid_ids = {q["question_id"] for q in session.review_queue}
        if question_id not in valid_ids:
            return {"error": "Question not found in current review session"}

        # 1. Evaluate the answer
        svc = ReviewService(self.db_pool, self.openai, self.scheduler)
        req = EvaluateRequest(question_id=question_id, user_answer=user_answer)
        resp = await svc.evaluate_answer(req)

        if resp.score == "correct":
            session.review_correct += 1

        # 2. Auto-rate using the LLM's suggested rating (maps correctness to FSRS)
        rating = resp.suggested_rating or 3
        rating = max(1, min(4, rating))
        if question_id not in session.rated_question_ids:
            try:
                rate_req = RateRequest(question_id=question_id, rating=rating)
                await svc.rate(rate_req)
                session.rated_question_ids.add(question_id)
            except Exception as e:
                logger.warning(f"Auto-rate failed for {question_id}: {e}")

        # 3. Build response with feedback
        result: dict[str, Any] = {
            "correct_answer": resp.correct_answer,
            "score": resp.score,
            "feedback": resp.feedback,
        }

        retries = session.review_teaching_retries.get(question_id, 0)

        # 4. Wrong or partial on FIRST attempt -> teach and re-ask same question
        if (resp.score == "wrong" or resp.score == "partial") and retries == 0:
            session.review_teaching_retries[question_id] = 1
            current_q = next((q for q in session.review_queue if q["question_id"] == question_id), None)
            result["done"] = False
            result["instruction"] = (
                "The user's understanding is incomplete or incorrect.\n"
                f"1. Briefly explain the correct concept: '{resp.correct_answer}' in simple terms (1-2 sentences)\n"
                "2. Ask them to explain it back in their own words\n"
                "3. When they answer, call evaluate_answer AGAIN with the SAME question_id\n"
                "DO NOT offer to capture/save. DO NOT ask if they want to continue. Just teach and re-ask."
            )
            result["retry_question"] = {
                "question_id": question_id,
                "question_text": current_q["question_text"] if current_q else "",
            }
            # Longer cooldown for retry: ignore late fragments from original answer
            # while LLM teaches and user listens before re-answering
            session._eval_cooldown_until = time.monotonic() + 12.0
            session.review_awaiting_answer = True
            session.review_current_question_id = question_id
            return result

        # 5. Correct, or second attempt (pass or fail) -> advance
        session.review_index += 1
        session.reviewed_count += 1
        session.session_reviews += 1

        if session.review_index >= len(session.review_queue):
            # Check if more due questions exist before declaring done
            more = await self._reload_due_questions(session)
            if more:
                nq = session.review_queue[session.review_index]
                result["done"] = False
                qnum = session.review_index + 1
                qtotal = len(session.review_queue)
                result["instruction"] = (
                    f"Say brief feedback, then say: 'Next question, number {qnum} of {qtotal}: "
                    f"{nq['question_text']}' — NOTHING ELSE."
                )
                result["next_question"] = {
                    "question_id": nq["question_id"],
                    "question_text": nq["question_text"],
                    "question_type": nq["question_type"],
                    "mnemonic_hint": nq.get("mnemonic_hint"),
                    "question_number": session.review_index + 1,
                    "total_questions": len(session.review_queue),
                }
                session.review_awaiting_answer = True
                session.review_current_question_id = nq["question_id"]
            else:
                result["done"] = True
                result["reviewed_count"] = session.reviewed_count
                result["correct_count"] = session.review_correct
                session.active_workflow = None
                session.review_awaiting_answer = False
                session.review_current_question_id = None
        else:
            nq = session.review_queue[session.review_index]
            result["done"] = False
            qnum = session.review_index + 1
            qtotal = len(session.review_queue)
            if resp.score == "wrong" or resp.score == "partial":
                result["instruction"] = (
                    f"Say: '{resp.feedback}' Then say: 'Next question, number {qnum} of {qtotal}: "
                    f"{nq['question_text']}' — NOTHING ELSE. Do NOT ask any questions. Do NOT offer to capture."
                )
            else:
                result["instruction"] = (
                    f"Say brief praise, then IMMEDIATELY say: 'Next question, number {qnum} of {qtotal}: "
                    f"{nq['question_text']}' — NOTHING ELSE. Do NOT ask any questions. Do NOT offer to capture."
                )
            result["next_question"] = {
                "question_id": nq["question_id"],
                "question_text": nq["question_text"],
                "question_type": nq["question_type"],
                "mnemonic_hint": nq.get("mnemonic_hint"),
                "question_number": qnum,
                "total_questions": qtotal,
            }
            session.review_awaiting_answer = True
            session.review_current_question_id = nq["question_id"]

        return result

    async def _auto_rate_question(self, question_id: str, rating: int) -> None:
        """Fire-and-forget: rate a skipped question with a default rating."""
        try:
            svc = ReviewService(self.db_pool, self.openai, self.scheduler)
            req = RateRequest(question_id=question_id, rating=rating)
            await svc.rate(req)
        except Exception as e:
            logger.warning(f"Background auto-rate failed for {question_id}: {e}")

    async def _reload_due_questions(self, session: UnifiedVoiceSession) -> bool:
        """Check for more due questions and append them to the review queue.
        Returns True if new questions were loaded, False if none remain."""
        try:
            already_seen = {q["question_id"] for q in session.review_queue}
            svc = ReviewService(self.db_pool, self.openai, self.scheduler)
            due_resp = await svc.get_due(limit=20)
            new_questions = [
                {
                    "question_id": q.question_id,
                    "question_text": q.question_text,
                    "question_type": q.question_type,
                    "mnemonic_hint": q.mnemonic_hint,
                    "technique_used": q.technique_used,
                }
                for q in due_resp.questions
                if q.question_id not in already_seen
            ]
            if new_questions:
                session.review_queue.extend(new_questions)
                logger.info(f"Reloaded {len(new_questions)} more due questions (total queue: {len(session.review_queue)})")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to reload due questions: {e}")
            return False

    async def _review_recent_capture(self, session: UnifiedVoiceSession) -> dict:
        """Load review questions only from the most recent capture."""
        if not session.last_capture_id:
            return {"error": "No recent capture. Capture something first, then ask to be quizzed on it."}

        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch(
                    """SELECT q.id, q.question_text, q.question_type, q.mnemonic_hint, q.technique_used
                       FROM questions q
                       JOIN extracted_points ep ON q.extracted_point_id = ep.id
                       WHERE ep.capture_id = $1
                       ORDER BY q.created_at""",
                    uuid.UUID(session.last_capture_id),
                )
        except Exception as e:
            logger.error(f"Failed to load recent capture questions: {e}")
            return {"error": "Failed to load questions for recent capture."}

        if not rows:
            return {"due_count": 0, "message": "No questions were generated for that capture."}

        session.review_queue = [
            {
                "question_id": str(r["id"]),
                "question_text": r["question_text"],
                "question_type": r["question_type"],
                "mnemonic_hint": r["mnemonic_hint"],
                "technique_used": r["technique_used"],
            }
            for r in rows
        ]
        session.review_index = 0
        session.rated_question_ids = set()
        session.active_workflow = "review"

        first = session.review_queue[0]
        session.review_awaiting_answer = True
        session.review_current_question_id = first["question_id"]
        return {
            "due_count": len(session.review_queue),
            "source": "recent_capture",
            "instruction": "Read the question to the user. When they answer, call evaluate_answer with the question_id and their answer. Do NOT evaluate their answer yourself.",
            "first_question": {
                "question_id": first["question_id"],
                "question_text": first["question_text"],
                "question_type": first["question_type"],
                "mnemonic_hint": first.get("mnemonic_hint"),
                "question_number": 1,
                "total_questions": len(session.review_queue),
            },
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

    # -- Interview Prep dispatch methods --

    async def _start_mock_interview(self, session: UnifiedVoiceSession, params: dict) -> dict:
        from services.interview_service import InterviewService
        svc = InterviewService(self.db_pool, self.openai, self.scheduler)
        topic = params.get("topic", "general")
        difficulty = params.get("difficulty", "medium")
        duration = params.get("duration_minutes", 30)
        try:
            result = await svc.start_interview(topic, difficulty, duration)
        except ValueError as e:
            return {"error": str(e)}
        session.interview_id = result["interview_id"]
        session.interview_topic = topic
        session.interview_question_order = 1
        session.interview_awaiting_answer = True
        session.active_workflow = "interview"
        return {
            "interview_id": result["interview_id"],
            "total_questions": result["total_questions"],
            "instruction": "You are now a Senior Engineer Interviewer. Read the first question. After the user answers, call submit_interview_answer.",
            "first_question": result.get("first_question"),
        }

    async def _submit_interview_answer(self, session: UnifiedVoiceSession, params: dict) -> dict:
        from services.interview_service import InterviewService
        svc = InterviewService(self.db_pool, self.openai, self.scheduler)
        interview_id = params.get("interview_id", session.interview_id or "")
        order = params.get("question_order", session.interview_question_order)
        user_answer = params.get("user_answer", "")
        if not interview_id:
            return {"error": "No active interview. Call start_mock_interview first."}
        try:
            result = await svc.evaluate_interview_answer(interview_id, order, user_answer)
        except ValueError as e:
            return {"error": str(e)}
        session.interview_awaiting_answer = False
        if result.get("follow_up_question"):
            session.interview_awaiting_follow_up = True
        elif result.get("next_question"):
            session.interview_question_order = result["next_question"]["question_order"]
            session.interview_awaiting_answer = True
        return result

    async def _end_mock_interview(self, session: UnifiedVoiceSession, params: dict) -> dict:
        from services.interview_service import InterviewService
        svc = InterviewService(self.db_pool, self.openai, self.scheduler)
        interview_id = params.get("interview_id", session.interview_id or "")
        if not interview_id:
            return {"error": "No active interview."}
        try:
            result = await svc.complete_interview(interview_id)
        except ValueError as e:
            return {"error": str(e)}
        session.interview_id = None
        session.interview_topic = None
        session.interview_question_order = 0
        session.interview_awaiting_answer = False
        session.interview_awaiting_follow_up = False
        session.active_workflow = None
        return result

    async def _start_focus_review(self, session: UnifiedVoiceSession, params: dict) -> dict:
        categories = params.get("categories", [])
        limit = params.get("limit", 10)
        if not categories:
            return {"error": "No categories specified."}
        svc = ReviewService(self.db_pool, self.openai, self.scheduler)
        due_resp = await svc.get_focus_session(categories, limit)
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
            return {"due_count": 0, "message": "No questions due in those categories. Try a mock interview on this topic, or practice your weak areas instead."}
        first = session.review_queue[0]
        session.review_awaiting_answer = True
        session.review_current_question_id = first["question_id"]
        return {
            "due_count": len(session.review_queue),
            "instruction": "Focus review started. Read the question to the user. Call evaluate_answer after they answer.",
            "first_question": {
                "question_id": first["question_id"],
                "question_text": first["question_text"],
                "question_type": first["question_type"],
                "mnemonic_hint": first.get("mnemonic_hint"),
                "question_number": 1,
                "total_questions": len(session.review_queue),
            },
        }

    async def _practice_behavioral(self, session: UnifiedVoiceSession, params: dict) -> dict:
        from services.behavioral_service import BehavioralService
        svc = BehavioralService(self.db_pool, self.openai)
        competency = params.get("competency")
        try:
            result = await svc.get_practice_question(competency)
        except ValueError as e:
            return {"error": str(e)}
        session.behavioral_question = result["question"]
        session.behavioral_competency = result["competency"]
        session.behavioral_awaiting_answer = True
        session.active_workflow = "behavioral"
        return {
            "question": result["question"],
            "competency": result["competency"],
            "tips": result["tips"],
            "instruction": "Read the behavioral question. After the user answers, call evaluate_behavioral_answer.",
        }

    async def _evaluate_behavioral_answer(self, session: UnifiedVoiceSession, params: dict) -> dict:
        from services.behavioral_service import BehavioralService
        svc = BehavioralService(self.db_pool, self.openai)
        competency = params.get("competency", session.behavioral_competency or "general")
        question = params.get("question", session.behavioral_question or "")
        user_answer = params.get("user_answer", "")
        try:
            result = await svc.evaluate_practice_answer(competency, question, user_answer)
        except ValueError as e:
            return {"error": str(e)}
        session.behavioral_awaiting_answer = False
        result["instruction"] = "Give detailed STAR feedback. Ask if they want to save this story."
        return result

    async def _capture_behavioral_story(self, session: UnifiedVoiceSession, params: dict) -> dict:
        from services.behavioral_service import BehavioralService
        svc = BehavioralService(self.db_pool, self.openai)
        narrative = params.get("narrative", "")
        competency = params.get("competency", session.behavioral_competency or "")
        if not narrative or not competency:
            return {"error": "Missing narrative or competency."}
        try:
            result = await svc.capture_story(narrative, competency)
        except ValueError as e:
            return {"error": str(e)}
        session.active_workflow = None
        session.behavioral_question = None
        session.behavioral_competency = None
        session.behavioral_awaiting_answer = False
        return result

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
                       VALUES ($1, $2, $3, NOW() - make_interval(secs => $4), NOW())""",
                    uuid.UUID(session.session_id),
                    "unified",
                    duration,
                    float(duration),
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
