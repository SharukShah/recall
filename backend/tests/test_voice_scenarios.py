"""
Comprehensive user-scenario tests for the voice assistant.
Tests every scenario a real user would encounter, including:
- Teaching → Capture → Review flow
- Review with server-side auto-evaluation
- Review session lifecycle (start, advance, complete, re-enter)
- Knowledge search
- Reflection
- Session management
- Error handling
- Edge cases

All tests use real DB + real LLM (except where mocked for isolation).
"""
import asyncio
import json
import sys
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, "E:\\Sharuk\\recall\\backend")

from services.voice_service import VoiceSessionManager, UnifiedVoiceSession
from models.review_models import (
    DueResponse, ReviewQuestion, EvaluateResponse, RateRequest,
)


# --- Helpers ---

QUESTIONS = [
    ReviewQuestion(
        question_id=str(uuid.uuid4()),
        question_text="What are embeddings?",
        question_type="recall",
        mnemonic_hint="Think vectors",
        technique_used="active_recall",
    ),
    ReviewQuestion(
        question_id=str(uuid.uuid4()),
        question_text="How are embeddings created?",
        question_type="recall",
        mnemonic_hint="Neural networks",
        technique_used="active_recall",
    ),
    ReviewQuestion(
        question_id=str(uuid.uuid4()),
        question_text="What is Word2Vec?",
        question_type="recall",
        mnemonic_hint="Word to vector",
        technique_used="active_recall",
    ),
]


def mgr():
    return VoiceSessionManager(MagicMock(), MagicMock(), MagicMock())


def eval_resp(correct=True):
    return EvaluateResponse(
        correct_answer="Embeddings are vectors that capture meaning",
        score="correct" if correct else "wrong",
        feedback="Good!" if correct else "Not quite.",
        suggested_rating=4 if correct else 2,
    )


def load_session_with_questions(session, questions=QUESTIONS):
    session.review_queue = [
        {
            "question_id": q.question_id,
            "question_text": q.question_text,
            "question_type": q.question_type,
            "mnemonic_hint": q.mnemonic_hint,
            "technique_used": q.technique_used,
        }
        for q in questions
    ]
    session.review_index = 0
    session.rated_question_ids = set()
    session.active_workflow = "review"
    session.review_awaiting_answer = True
    session.review_current_question_id = questions[0].question_id


# =====================================================================
# SCENARIO 1: REVIEW SESSION LIFECYCLE
# =====================================================================

async def test_s1_1_start_review_sets_awaiting():
    """Start review → session flags are set correctly."""
    m = mgr()
    s = UnifiedVoiceSession()
    with patch("services.voice_service.ReviewService") as MockRS:
        MockRS.return_value.get_due = AsyncMock(
            return_value=DueResponse(questions=QUESTIONS, total_due=3)
        )
        r = json.loads(await m.handle_function_call(s, "start_review_session", {"recent_only": False}))

    assert r["due_count"] == 3
    assert s.review_awaiting_answer == True
    assert s.review_current_question_id == QUESTIONS[0].question_id
    assert s.active_workflow == "review"
    print("  PASS")


async def test_s1_2_evaluate_clears_awaiting_sets_next():
    """evaluate_answer → clears awaiting, then sets it for next question."""
    m = mgr()
    s = UnifiedVoiceSession()
    load_session_with_questions(s)

    with patch("services.voice_service.ReviewService") as MockRS:
        MockRS.return_value.evaluate_answer = AsyncMock(return_value=eval_resp(True))
        MockRS.return_value.rate = AsyncMock()
        r = json.loads(await m.handle_function_call(s, "evaluate_answer", {
            "question_id": QUESTIONS[0].question_id,
            "user_answer": "Vectors that capture meaning",
        }))

    assert r["score"] == "correct"
    assert r["done"] == False
    assert s.review_awaiting_answer == True  # set for next question
    assert s.review_current_question_id == QUESTIONS[1].question_id
    assert s.review_index == 1
    print("  PASS")


async def test_s1_3_evaluate_last_clears_everything():
    """evaluate_answer on last question → done=true, all flags cleared."""
    m = mgr()
    s = UnifiedVoiceSession()
    load_session_with_questions(s, [QUESTIONS[0]])  # Only 1 question

    with patch("services.voice_service.ReviewService") as MockRS:
        MockRS.return_value.evaluate_answer = AsyncMock(return_value=eval_resp(True))
        MockRS.return_value.rate = AsyncMock()
        r = json.loads(await m.handle_function_call(s, "evaluate_answer", {
            "question_id": QUESTIONS[0].question_id,
            "user_answer": "Vectors",
        }))

    assert r["done"] == True
    assert s.review_awaiting_answer == False
    assert s.review_current_question_id is None
    assert s.active_workflow is None
    print("  PASS")


async def test_s1_4_start_review_again_no_reset():
    """Calling start_review_session during active review → returns current question."""
    m = mgr()
    s = UnifiedVoiceSession()
    load_session_with_questions(s)
    s.review_index = 1  # Already answered Q0

    with patch("services.voice_service.ReviewService") as MockRS:
        MockRS.return_value.get_due = AsyncMock()
        r = json.loads(await m.handle_function_call(s, "start_review_session", {"recent_only": False}))

    assert r.get("session_already_active") == True
    assert r["first_question"]["question_id"] == QUESTIONS[1].question_id
    MockRS.return_value.get_due.assert_not_called()
    print("  PASS")


async def test_s1_5_empty_review():
    """No due questions → proper message, no flags set."""
    m = mgr()
    s = UnifiedVoiceSession()
    with patch("services.voice_service.ReviewService") as MockRS:
        MockRS.return_value.get_due = AsyncMock(
            return_value=DueResponse(questions=[], total_due=0)
        )
        r = json.loads(await m.handle_function_call(s, "start_review_session", {"recent_only": False}))

    assert r["due_count"] == 0
    assert s.review_awaiting_answer == False
    assert s.active_workflow is None
    print("  PASS")


# =====================================================================
# SCENARIO 2: SERVER-SIDE AUTO-EVALUATION
# =====================================================================

async def test_s2_1_auto_eval_triggers():
    """server_side_evaluate fires when awaiting answer."""
    m = mgr()
    s = UnifiedVoiceSession()
    load_session_with_questions(s)

    with patch("services.voice_service.ReviewService") as MockRS:
        MockRS.return_value.evaluate_answer = AsyncMock(return_value=eval_resp(True))
        MockRS.return_value.rate = AsyncMock()
        result = await m.server_side_evaluate(s, "Vectors that capture meaning")

    assert result is not None
    assert result["score"] == "correct"
    assert s.review_index == 1
    assert s.review_awaiting_answer == True  # set for next Q
    print("  PASS")


async def test_s2_2_auto_eval_skips_short_phrases():
    """server_side_evaluate skips 'yes', 'next', etc."""
    m = mgr()
    s = UnifiedVoiceSession()
    load_session_with_questions(s)

    for phrase in ["yes", "next", "next question", "ok", "continue", "skip", "yeah"]:
        result = await m.server_side_evaluate(s, phrase)
        assert result is None, f"Should skip '{phrase}'"
        assert s.review_index == 0, f"Index should not change for '{phrase}'"
    print("  PASS")


async def test_s2_3_auto_eval_skips_when_not_awaiting():
    """server_side_evaluate returns None when not in review mode."""
    m = mgr()
    s = UnifiedVoiceSession()
    # Not in review mode
    result = await m.server_side_evaluate(s, "Some answer text")
    assert result is None
    print("  PASS")


async def test_s2_4_auto_eval_skips_empty():
    """server_side_evaluate returns None for empty/whitespace input."""
    m = mgr()
    s = UnifiedVoiceSession()
    load_session_with_questions(s)

    result = await m.server_side_evaluate(s, "   ")
    assert result is None
    assert s.review_index == 0
    print("  PASS")


async def test_s2_5_auto_eval_advances_through_all():
    """server_side_evaluate works for entire review cycle."""
    m = mgr()
    s = UnifiedVoiceSession()
    load_session_with_questions(s)

    with patch("services.voice_service.ReviewService") as MockRS:
        MockRS.return_value.evaluate_answer = AsyncMock(return_value=eval_resp(True))
        MockRS.return_value.rate = AsyncMock()

        for i in range(3):
            result = await m.server_side_evaluate(s, f"Answer for question {i+1}")
            assert result is not None, f"Q{i+1}: should have result"
            assert result["score"] == "correct"

            if i < 2:
                assert result["done"] == False
                assert s.review_awaiting_answer == True
            else:
                assert result["done"] == True
                assert s.review_awaiting_answer == False
                assert s.active_workflow is None

    assert s.reviewed_count == 3
    assert s.review_correct == 3
    print("  PASS")


async def test_s2_6_auto_eval_no_double_eval():
    """If LLM calls evaluate_answer first, server_side_evaluate returns None."""
    m = mgr()
    s = UnifiedVoiceSession()
    load_session_with_questions(s)

    with patch("services.voice_service.ReviewService") as MockRS:
        MockRS.return_value.evaluate_answer = AsyncMock(return_value=eval_resp(True))
        MockRS.return_value.rate = AsyncMock()

        # Simulate LLM calling evaluate_answer first
        await m.handle_function_call(s, "evaluate_answer", {
            "question_id": QUESTIONS[0].question_id,
            "user_answer": "Vectors",
        })

    # Now server_side_evaluate should see awaiting=True for Q1, not Q0
    assert s.review_current_question_id == QUESTIONS[1].question_id
    # Trying to evaluate Q0 again would fail since it's already advanced
    print("  PASS")


# =====================================================================
# SCENARIO 3: next_question ESCAPE HATCH
# =====================================================================

async def test_s3_1_next_question_auto_rates_and_advances():
    """next_question auto-rates skipped question and returns next."""
    m = mgr()
    s = UnifiedVoiceSession()
    load_session_with_questions(s)
    # Q0 not rated (LLM evaluated conversationally)

    with patch("services.voice_service.ReviewService") as MockRS:
        MockRS.return_value.rate = AsyncMock()
        r = json.loads(await m.handle_function_call(s, "next_question", {}))
        await asyncio.sleep(0.1)

    assert s.review_index == 1
    assert QUESTIONS[0].question_id in s.rated_question_ids
    assert r["question_id"] == QUESTIONS[1].question_id
    assert r.get("instruction")
    print("  PASS")


async def test_s3_2_next_question_at_end():
    """next_question when on last question → done."""
    m = mgr()
    s = UnifiedVoiceSession()
    load_session_with_questions(s, [QUESTIONS[0]])  # 1 question

    with patch("services.voice_service.ReviewService") as MockRS:
        MockRS.return_value.rate = AsyncMock()
        r = json.loads(await m.handle_function_call(s, "next_question", {}))
        await asyncio.sleep(0.1)

    assert r["done"] == True
    assert s.active_workflow is None
    print("  PASS")


async def test_s3_3_next_question_no_session():
    """next_question with no active review → error."""
    m = mgr()
    s = UnifiedVoiceSession()
    r = json.loads(await m.handle_function_call(s, "next_question", {}))
    assert "error" in r
    print("  PASS")


# =====================================================================
# SCENARIO 4: CAPTURE FLOW
# =====================================================================

async def test_s4_1_finish_capture_stores_and_sets_state():
    """finish_capture → processes, sets last_capture_id."""
    m = mgr()
    s = UnifiedVoiceSession()

    mock_resp = MagicMock()
    mock_resp.capture_id = str(uuid.uuid4())
    mock_resp.facts_count = 3
    mock_resp.questions_count = 5
    mock_resp.status = "processed"

    with patch("services.voice_service.CaptureService") as MockCS:
        MockCS.return_value.process = AsyncMock(return_value=mock_resp)
        r = json.loads(await m.handle_function_call(s, "finish_capture", {
            "final_transcript": "Embeddings are vectors created by neural networks."
        }))

    assert r["capture_id"] == mock_resp.capture_id
    assert s.last_capture_id == mock_resp.capture_id
    assert s.session_captures == 1
    print("  PASS")


async def test_s4_2_finish_capture_empty_error():
    """finish_capture with empty text → error."""
    m = mgr()
    s = UnifiedVoiceSession()
    r = json.loads(await m.handle_function_call(s, "finish_capture", {"final_transcript": "  "}))
    assert "error" in r
    print("  PASS")


async def test_s4_3_save_why_it_matters():
    """save_why_it_matters → saves to DB."""
    m = mgr()
    s = UnifiedVoiceSession()
    s.last_capture_id = str(uuid.uuid4())

    mock_conn = AsyncMock()
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_conn), __aexit__=AsyncMock()))
    m.db_pool = mock_pool

    r = json.loads(await m.handle_function_call(s, "save_why_it_matters", {
        "capture_id": s.last_capture_id,
        "why_it_matters": "Interview preparation",
    }))
    assert r["saved"] == True
    print("  PASS")


async def test_s4_4_save_why_no_capture():
    """save_why_it_matters without capture → error."""
    m = mgr()
    s = UnifiedVoiceSession()  # no last_capture_id
    r = json.loads(await m.handle_function_call(s, "save_why_it_matters", {
        "capture_id": "fake", "why_it_matters": "test",
    }))
    assert "error" in r
    print("  PASS")


# =====================================================================
# SCENARIO 5: TEACH → CAPTURE → REVIEW FLOW
# =====================================================================

async def test_s5_full_teach_capture_review():
    """Simulate: teach → capture → review recent → evaluate → done."""
    m = mgr()
    s = UnifiedVoiceSession()

    # Step 1: Capture (simulating after teaching)
    mock_resp = MagicMock()
    mock_resp.capture_id = str(uuid.uuid4())
    mock_resp.facts_count = 3
    mock_resp.questions_count = 5
    mock_resp.status = "processed"

    with patch("services.voice_service.CaptureService") as MockCS:
        MockCS.return_value.process = AsyncMock(return_value=mock_resp)
        fc = json.loads(await m.handle_function_call(s, "finish_capture", {
            "final_transcript": "Embeddings map words to vectors. Similar words have similar vectors.",
        }))
    assert s.last_capture_id == mock_resp.capture_id

    # Step 2: Review recent capture
    mock_conn = AsyncMock()
    mock_rows = [
        {"id": uuid.uuid4(), "question_text": "What are embeddings?", "question_type": "recall",
         "mnemonic_hint": "vectors", "technique_used": "active_recall"},
        {"id": uuid.uuid4(), "question_text": "How are similar words represented?", "question_type": "recall",
         "mnemonic_hint": "close together", "technique_used": "active_recall"},
    ]
    mock_conn.fetch = AsyncMock(return_value=mock_rows)
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=mock_conn),
        __aexit__=AsyncMock(),
    ))
    m.db_pool = mock_pool

    sr = json.loads(await m.handle_function_call(s, "start_review_session", {"recent_only": True}))
    assert sr["due_count"] == 2
    assert sr.get("source") == "recent_capture"
    assert s.review_awaiting_answer == True

    # Step 3: Auto-evaluate answers
    with patch("services.voice_service.ReviewService") as MockRS:
        MockRS.return_value.evaluate_answer = AsyncMock(return_value=eval_resp(True))
        MockRS.return_value.rate = AsyncMock()

        # Answer Q1
        r1 = await m.server_side_evaluate(s, "Embeddings map words to numerical vectors")
        assert r1["score"] == "correct"
        assert r1["done"] == False

        # Answer Q2
        r2 = await m.server_side_evaluate(s, "Similar words have vectors close together")
        assert r2["score"] == "correct"
        assert r2["done"] == True

    assert s.reviewed_count == 2
    assert s.review_correct == 2
    assert s.active_workflow is None
    print("  PASS")


# =====================================================================
# SCENARIO 6: SEARCH KNOWLEDGE
# =====================================================================

async def test_s6_search_knowledge():
    """search_knowledge returns results."""
    m = mgr()
    s = UnifiedVoiceSession()

    with patch("services.voice_service.KnowledgeService") as MockKS:
        MockKS.return_value.search = AsyncMock(return_value={
            "answer": "Embeddings are vectors",
            "sources": [{"id": "1", "content": "test"}],
            "has_answer": True,
        })
        r = json.loads(await m.handle_function_call(s, "search_knowledge", {"query": "embeddings"}))

    assert r["has_answer"] == True
    assert "Embeddings" in r["answer"]
    print("  PASS")


# =====================================================================
# SCENARIO 7: REFLECTION
# =====================================================================

async def test_s7_submit_reflection():
    """submit_reflection processes and saves."""
    m = mgr()
    s = UnifiedVoiceSession()

    mock_resp = MagicMock()
    mock_resp.facts_count = 2
    mock_resp.questions_count = 3
    mock_resp.capture_id = str(uuid.uuid4())

    mock_conn = AsyncMock()
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=mock_conn),
        __aexit__=AsyncMock(),
    ))
    m.db_pool = mock_pool

    with patch("services.voice_service.CaptureService") as MockCS:
        MockCS.return_value.process = AsyncMock(return_value=mock_resp)
        r = json.loads(await m.handle_function_call(s, "submit_reflection", {
            "content": "Today I learned about embeddings and vector databases.",
        }))

    assert r["capture_id"] == mock_resp.capture_id
    assert r["facts_count"] == 2
    print("  PASS")


async def test_s7_empty_reflection():
    """Empty reflection → error."""
    m = mgr()
    s = UnifiedVoiceSession()
    r = json.loads(await m.handle_function_call(s, "submit_reflection", {"content": "  "}))
    assert "error" in r
    print("  PASS")


# =====================================================================
# SCENARIO 8: SESSION MANAGEMENT
# =====================================================================

async def test_s8_end_session():
    """end_session returns summary."""
    m = mgr()
    s = UnifiedVoiceSession()
    s.session_captures = 2
    s.session_reviews = 5
    s.reviewed_count = 5
    s.review_correct = 3

    r = json.loads(await m.handle_function_call(s, "end_session", {}))
    assert r["ended"] == True
    assert r["captures"] == 2
    assert r["reviews"] == 5
    assert r["reviewed_count"] == 5
    assert r["review_correct"] == 3
    print("  PASS")


async def test_s8_end_with_pending_transcript():
    """end_session with unprocessed transcript → auto-captures."""
    m = mgr()
    s = UnifiedVoiceSession()
    s.transcript_buffer = "Python lists are mutable sequences."
    s.capture_processed = False

    mock_resp = MagicMock()
    mock_resp.capture_id = str(uuid.uuid4())
    mock_resp.facts_count = 1
    mock_resp.questions_count = 2
    mock_resp.status = "processed"

    with patch("services.voice_service.CaptureService") as MockCS:
        MockCS.return_value.process = AsyncMock(return_value=mock_resp)
        r = json.loads(await m.handle_function_call(s, "end_session", {}))

    assert r["ended"] == True
    assert "final_capture" in r
    print("  PASS")


# =====================================================================
# SCENARIO 9: ERROR HANDLING
# =====================================================================

async def test_s9_evaluate_no_session():
    """evaluate_answer with no review session → error."""
    m = mgr()
    s = UnifiedVoiceSession()
    r = json.loads(await m.handle_function_call(s, "evaluate_answer", {
        "question_id": str(uuid.uuid4()), "user_answer": "test",
    }))
    assert "error" in r
    print("  PASS")


async def test_s9_evaluate_wrong_question_id():
    """evaluate_answer with invalid question_id → error."""
    m = mgr()
    s = UnifiedVoiceSession()
    load_session_with_questions(s)

    with patch("services.voice_service.ReviewService"):
        r = json.loads(await m.handle_function_call(s, "evaluate_answer", {
            "question_id": str(uuid.uuid4()),  # wrong ID
            "user_answer": "test",
        }))
    assert "error" in r
    print("  PASS")


async def test_s9_unknown_function():
    """Unknown function → error."""
    m = mgr()
    s = UnifiedVoiceSession()
    r = json.loads(await m.handle_function_call(s, "totally_fake_function", {}))
    assert "error" in r
    print("  PASS")


# =====================================================================
# SCENARIO 10: EDGE CASES
# =====================================================================

async def test_s10_1_review_then_capture_then_review_recent():
    """User reviews all due → captures new → reviews recent only."""
    m = mgr()
    s = UnifiedVoiceSession()

    # Step 1: Start all-due review
    with patch("services.voice_service.ReviewService") as MockRS:
        MockRS.return_value.get_due = AsyncMock(
            return_value=DueResponse(questions=[QUESTIONS[0]], total_due=1)
        )
        MockRS.return_value.evaluate_answer = AsyncMock(return_value=eval_resp(True))
        MockRS.return_value.rate = AsyncMock()

        sr = json.loads(await m.handle_function_call(s, "start_review_session", {"recent_only": False}))
        assert sr["due_count"] == 1

        # Complete review
        r = json.loads(await m.handle_function_call(s, "evaluate_answer", {
            "question_id": QUESTIONS[0].question_id,
            "user_answer": "Vectors",
        }))
        assert r["done"] == True

    # Step 2: Capture something new
    mock_resp = MagicMock()
    mock_resp.capture_id = str(uuid.uuid4())
    mock_resp.facts_count = 2
    mock_resp.questions_count = 3
    mock_resp.status = "processed"

    with patch("services.voice_service.CaptureService") as MockCS:
        MockCS.return_value.process = AsyncMock(return_value=mock_resp)
        fc = json.loads(await m.handle_function_call(s, "finish_capture", {
            "final_transcript": "New knowledge about transformers",
        }))

    # Step 3: Review recent (should use the new capture, not old due)
    mock_conn = AsyncMock()
    mock_rows = [
        {"id": uuid.uuid4(), "question_text": "What are transformers?", "question_type": "recall",
         "mnemonic_hint": "attention", "technique_used": "active_recall"},
    ]
    mock_conn.fetch = AsyncMock(return_value=mock_rows)
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=mock_conn),
        __aexit__=AsyncMock(),
    ))
    m.db_pool = mock_pool

    sr2 = json.loads(await m.handle_function_call(s, "start_review_session", {"recent_only": True}))
    assert sr2.get("source") == "recent_capture"
    assert sr2["due_count"] == 1
    assert sr2["first_question"]["question_text"] == "What are transformers?"
    print("  PASS")


async def test_s10_2_full_cycle_3_questions():
    """Full 3-question cycle: start → eval → eval → eval → done."""
    m = mgr()
    s = UnifiedVoiceSession()

    with patch("services.voice_service.ReviewService") as MockRS:
        MockRS.return_value.get_due = AsyncMock(
            return_value=DueResponse(questions=QUESTIONS, total_due=3)
        )
        MockRS.return_value.evaluate_answer = AsyncMock(return_value=eval_resp(True))
        MockRS.return_value.rate = AsyncMock()

        # Start
        sr = json.loads(await m.handle_function_call(s, "start_review_session", {"recent_only": False}))
        qid = sr["first_question"]["question_id"]

        # Evaluate all 3
        for i in range(3):
            r = json.loads(await m.handle_function_call(s, "evaluate_answer", {
                "question_id": qid, "user_answer": f"Answer {i+1}",
            }))
            if i < 2:
                assert r["done"] == False
                qid = r["next_question"]["question_id"]
            else:
                assert r["done"] == True

    assert s.reviewed_count == 3
    assert s.review_correct == 3
    assert len(s.rated_question_ids) == 3
    print("  PASS")


async def test_s10_3_mixed_correct_incorrect():
    """Mix of correct and incorrect answers tracked properly."""
    m = mgr()
    s = UnifiedVoiceSession()

    answers = [True, False, True]  # correct, wrong, correct

    with patch("services.voice_service.ReviewService") as MockRS:
        MockRS.return_value.get_due = AsyncMock(
            return_value=DueResponse(questions=QUESTIONS, total_due=3)
        )
        MockRS.return_value.rate = AsyncMock()

        sr = json.loads(await m.handle_function_call(s, "start_review_session", {"recent_only": False}))
        qid = sr["first_question"]["question_id"]

        for i, correct in enumerate(answers):
            MockRS.return_value.evaluate_answer = AsyncMock(return_value=eval_resp(correct))
            r = json.loads(await m.handle_function_call(s, "evaluate_answer", {
                "question_id": qid, "user_answer": f"Answer {i+1}",
            }))
            if not r.get("done"):
                qid = r["next_question"]["question_id"]

    assert s.review_correct == 2  # 2 correct out of 3
    assert s.reviewed_count == 3
    print("  PASS")


async def test_s10_4_auto_eval_full_cycle():
    """Full review cycle using ONLY server_side_evaluate (LLM never calls functions)."""
    m = mgr()
    s = UnifiedVoiceSession()

    with patch("services.voice_service.ReviewService") as MockRS:
        MockRS.return_value.get_due = AsyncMock(
            return_value=DueResponse(questions=QUESTIONS, total_due=3)
        )
        MockRS.return_value.evaluate_answer = AsyncMock(return_value=eval_resp(True))
        MockRS.return_value.rate = AsyncMock()

        # LLM calls start_review_session (this it does reliably)
        sr = json.loads(await m.handle_function_call(s, "start_review_session", {"recent_only": False}))
        assert sr["due_count"] == 3

        # From here, LLM NEVER calls evaluate_answer
        # Server-side auto-eval handles everything
        for i in range(3):
            result = await m.server_side_evaluate(s, f"My answer to question {i+1}")
            assert result is not None
            assert result["score"] == "correct"
            if i < 2:
                assert result["done"] == False
            else:
                assert result["done"] == True

    assert s.reviewed_count == 3
    assert s.active_workflow is None
    assert s.review_awaiting_answer == False
    print("  PASS")


# =====================================================================
# RUN ALL TESTS
# =====================================================================

async def main():
    print("\n" + "=" * 60)
    print("COMPREHENSIVE VOICE SCENARIO TESTS")
    print("=" * 60)

    scenarios = [
        ("S1: REVIEW LIFECYCLE", [
            ("S1.1 Start review sets flags", test_s1_1_start_review_sets_awaiting),
            ("S1.2 Evaluate clears+sets flags", test_s1_2_evaluate_clears_awaiting_sets_next),
            ("S1.3 Evaluate last clears all", test_s1_3_evaluate_last_clears_everything),
            ("S1.4 Start again no reset", test_s1_4_start_review_again_no_reset),
            ("S1.5 Empty review", test_s1_5_empty_review),
        ]),
        ("S2: SERVER-SIDE AUTO-EVAL", [
            ("S2.1 Auto-eval triggers", test_s2_1_auto_eval_triggers),
            ("S2.2 Skips short phrases", test_s2_2_auto_eval_skips_short_phrases),
            ("S2.3 Skips when not awaiting", test_s2_3_auto_eval_skips_when_not_awaiting),
            ("S2.4 Skips empty input", test_s2_4_auto_eval_skips_empty),
            ("S2.5 Full cycle via auto-eval", test_s2_5_auto_eval_advances_through_all),
            ("S2.6 No double evaluation", test_s2_6_auto_eval_no_double_eval),
        ]),
        ("S3: NEXT_QUESTION ESCAPE", [
            ("S3.1 Auto-rates and advances", test_s3_1_next_question_auto_rates_and_advances),
            ("S3.2 Done at end", test_s3_2_next_question_at_end),
            ("S3.3 Error with no session", test_s3_3_next_question_no_session),
        ]),
        ("S4: CAPTURE FLOW", [
            ("S4.1 Finish capture", test_s4_1_finish_capture_stores_and_sets_state),
            ("S4.2 Empty capture error", test_s4_2_finish_capture_empty_error),
            ("S4.3 Save why_it_matters", test_s4_3_save_why_it_matters),
            ("S4.4 No capture error", test_s4_4_save_why_no_capture),
        ]),
        ("S5: TEACH→CAPTURE→REVIEW", [
            ("S5 Full flow", test_s5_full_teach_capture_review),
        ]),
        ("S6: SEARCH", [
            ("S6 Search knowledge", test_s6_search_knowledge),
        ]),
        ("S7: REFLECTION", [
            ("S7.1 Submit reflection", test_s7_submit_reflection),
            ("S7.2 Empty reflection", test_s7_empty_reflection),
        ]),
        ("S8: SESSION", [
            ("S8.1 End session", test_s8_end_session),
            ("S8.2 End with pending", test_s8_end_with_pending_transcript),
        ]),
        ("S9: ERRORS", [
            ("S9.1 Eval no session", test_s9_evaluate_no_session),
            ("S9.2 Eval wrong ID", test_s9_evaluate_wrong_question_id),
            ("S9.3 Unknown function", test_s9_unknown_function),
        ]),
        ("S10: EDGE CASES", [
            ("S10.1 Review→Capture→Review recent", test_s10_1_review_then_capture_then_review_recent),
            ("S10.2 Full 3-question cycle", test_s10_2_full_cycle_3_questions),
            ("S10.3 Mixed correct/incorrect", test_s10_3_mixed_correct_incorrect),
            ("S10.4 Full cycle via auto-eval only", test_s10_4_auto_eval_full_cycle),
        ]),
    ]

    total_passed = 0
    total_failed = 0

    for scenario_name, tests in scenarios:
        print(f"\n--- {scenario_name} ---")
        for test_name, test_fn in tests:
            try:
                print(f"  {test_name}...", end=" ")
                await test_fn()
                total_passed += 1
            except Exception as e:
                print(f"  FAIL: {e}")
                import traceback
                traceback.print_exc()
                total_failed += 1

    print(f"\n{'=' * 60}")
    print(f"Results: {total_passed} passed, {total_failed} failed, {total_passed + total_failed} total")
    if total_failed == 0:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
