"""
End-to-end test for the voice review flow.
Simulates exactly what happens when Deepgram dispatches function calls:
  start_review_session → evaluate_answer → evaluate_answer → ... → done

Tests:
1. Review session starts and returns first question with instruction
2. evaluate_answer scores, advances, and returns next question
3. Calling start_review_session again mid-review does NOT reset the queue
4. _get_next_question auto-rates and advances if evaluate_answer was skipped
5. Full review cycle completes with done=true
"""
import asyncio
import json
import sys
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.voice_service import VoiceSessionManager, UnifiedVoiceSession
from models.review_models import (
    DueResponse, ReviewQuestion, EvaluateResponse, RateRequest,
)


# --- Fixtures ---

FAKE_QUESTIONS = [
    ReviewQuestion(
        question_id=str(uuid.uuid4()),
        question_text="What does an if condition check?",
        question_type="recall",
        mnemonic_hint="Think about true/false",
        technique_used="active_recall",
    ),
    ReviewQuestion(
        question_id=str(uuid.uuid4()),
        question_text="What keyword starts a conditional in Python?",
        question_type="recall",
        mnemonic_hint="Two letters",
        technique_used="active_recall",
    ),
    ReviewQuestion(
        question_id=str(uuid.uuid4()),
        question_text="What is the else clause used for?",
        question_type="recall",
        mnemonic_hint="The other path",
        technique_used="active_recall",
    ),
]


def make_manager():
    """Create a VoiceSessionManager with mocked dependencies."""
    pool = MagicMock()
    openai = MagicMock()
    scheduler = MagicMock()
    return VoiceSessionManager(pool, openai, scheduler)


def make_evaluate_response(correct: bool) -> EvaluateResponse:
    return EvaluateResponse(
        correct_answer="An if condition checks whether a condition is true",
        score="correct" if correct else "incorrect",
        feedback="Good job!" if correct else "Not quite.",
        suggested_rating=4 if correct else 2,
    )


# --- Tests ---

async def test_start_review_returns_first_question():
    """start_review_session should return first question with instruction."""
    mgr = make_manager()
    session = UnifiedVoiceSession()

    with patch("services.voice_service.ReviewService") as MockRS:
        mock_svc = MockRS.return_value
        mock_svc.get_due = AsyncMock(return_value=DueResponse(
            questions=FAKE_QUESTIONS, total_due=3
        ))

        result_json = await mgr.handle_function_call(
            session, "start_review_session", {"recent_only": False}
        )
        result = json.loads(result_json)

    assert result["due_count"] == 3, f"Expected 3 due, got {result['due_count']}"
    assert "first_question" in result, "Missing first_question"
    assert "instruction" in result, "Missing instruction field"
    assert result["first_question"]["question_id"] == FAKE_QUESTIONS[0].question_id
    assert session.review_index == 0
    assert session.active_workflow == "review"
    print("  PASS: start_review_session returns first question with instruction")
    return session


async def test_start_review_again_doesnt_reset(session: UnifiedVoiceSession):
    """Calling start_review_session again mid-review should NOT reset the queue."""
    mgr = make_manager()
    # Advance index to simulate progress
    session.review_index = 1
    session.rated_question_ids = {FAKE_QUESTIONS[0].question_id}

    with patch("services.voice_service.ReviewService") as MockRS:
        # get_due should NOT be called
        mock_svc = MockRS.return_value
        mock_svc.get_due = AsyncMock()

        result_json = await mgr.handle_function_call(
            session, "start_review_session", {"recent_only": False}
        )
        result = json.loads(result_json)

    assert result.get("session_already_active") == True, "Should flag session as already active"
    assert "instruction" in result, "Missing instruction field"
    assert result["first_question"]["question_id"] == FAKE_QUESTIONS[1].question_id, \
        f"Should return current question (index 1), got {result['first_question']['question_id']}"
    assert session.review_index == 1, "Index should NOT have been reset"
    mock_svc.get_due.assert_not_called()
    print("  PASS: start_review_session mid-review returns current question, no reset")


async def test_evaluate_answer_advances():
    """evaluate_answer should score, rate, and return next question."""
    mgr = make_manager()
    session = UnifiedVoiceSession()
    session.review_queue = [
        {
            "question_id": q.question_id,
            "question_text": q.question_text,
            "question_type": q.question_type,
            "mnemonic_hint": q.mnemonic_hint,
            "technique_used": q.technique_used,
        }
        for q in FAKE_QUESTIONS
    ]
    session.review_index = 0
    session.active_workflow = "review"

    with patch("services.voice_service.ReviewService") as MockRS:
        mock_svc = MockRS.return_value
        mock_svc.evaluate_answer = AsyncMock(return_value=make_evaluate_response(True))
        mock_svc.rate = AsyncMock()

        result_json = await mgr.handle_function_call(
            session, "evaluate_answer",
            {"question_id": FAKE_QUESTIONS[0].question_id, "user_answer": "It checks if something is true"}
        )
        result = json.loads(result_json)

    assert result["score"] == "correct", f"Expected correct, got {result['score']}"
    assert result.get("done") == False, "Should not be done yet"
    assert "next_question" in result, "Should have next_question"
    assert "instruction" in result, "Missing instruction in evaluate_answer response"
    assert result["next_question"]["question_id"] == FAKE_QUESTIONS[1].question_id
    assert session.review_index == 1, f"Index should be 1, got {session.review_index}"
    assert FAKE_QUESTIONS[0].question_id in session.rated_question_ids
    print("  PASS: evaluate_answer scores, rates, advances, returns next question with instruction")
    return session


async def test_evaluate_answer_completes_review():
    """evaluate_answer on last question should return done=true."""
    mgr = make_manager()
    session = UnifiedVoiceSession()
    session.review_queue = [
        {
            "question_id": FAKE_QUESTIONS[0].question_id,
            "question_text": FAKE_QUESTIONS[0].question_text,
            "question_type": FAKE_QUESTIONS[0].question_type,
            "mnemonic_hint": FAKE_QUESTIONS[0].mnemonic_hint,
            "technique_used": FAKE_QUESTIONS[0].technique_used,
        }
    ]
    session.review_index = 0
    session.active_workflow = "review"

    with patch("services.voice_service.ReviewService") as MockRS:
        mock_svc = MockRS.return_value
        mock_svc.evaluate_answer = AsyncMock(return_value=make_evaluate_response(True))
        mock_svc.rate = AsyncMock()

        result_json = await mgr.handle_function_call(
            session, "evaluate_answer",
            {"question_id": FAKE_QUESTIONS[0].question_id, "user_answer": "Checks if true"}
        )
        result = json.loads(result_json)

    assert result["done"] == True, "Should be done"
    assert "next_question" not in result, "Should NOT have next_question"
    assert result["reviewed_count"] == 1
    assert session.active_workflow is None, "Workflow should be cleared"
    print("  PASS: evaluate_answer on last question returns done=true")


async def test_get_next_question_auto_advances():
    """get_next_question should auto-rate skipped questions and advance."""
    mgr = make_manager()
    session = UnifiedVoiceSession()
    session.review_queue = [
        {
            "question_id": q.question_id,
            "question_text": q.question_text,
            "question_type": q.question_type,
            "mnemonic_hint": q.mnemonic_hint,
            "technique_used": q.technique_used,
        }
        for q in FAKE_QUESTIONS
    ]
    session.review_index = 0
    session.active_workflow = "review"
    # Question 0 was NOT rated (simulating LLM skipping evaluate_answer)

    with patch("services.voice_service.ReviewService") as MockRS:
        mock_svc = MockRS.return_value
        mock_svc.rate = AsyncMock()

        result_json = await mgr.handle_function_call(
            session, "get_next_question", {}
        )
        result = json.loads(result_json)
        # Give the fire-and-forget task a chance to run
        await asyncio.sleep(0.1)

    assert session.review_index == 1, f"Index should be 1 (auto-advanced), got {session.review_index}"
    assert FAKE_QUESTIONS[0].question_id in session.rated_question_ids, "Question 0 should be auto-rated"
    assert "question_id" in result, f"Should return next question, got {result}"
    assert result["question_id"] == FAKE_QUESTIONS[1].question_id
    print("  PASS: get_next_question auto-rates skipped question and advances")


async def test_next_question_function():
    """next_question (new function name) should work same as get_next_question."""
    mgr = make_manager()
    session = UnifiedVoiceSession()
    session.review_queue = [
        {
            "question_id": q.question_id,
            "question_text": q.question_text,
            "question_type": q.question_type,
            "mnemonic_hint": q.mnemonic_hint,
            "technique_used": q.technique_used,
        }
        for q in FAKE_QUESTIONS
    ]
    session.review_index = 0
    session.active_workflow = "review"

    with patch("services.voice_service.ReviewService") as MockRS:
        mock_svc = MockRS.return_value
        mock_svc.rate = AsyncMock()

        # Use "next_question" (the new function name exposed to LLM)
        result_json = await mgr.handle_function_call(
            session, "next_question", {}
        )
        result = json.loads(result_json)
        await asyncio.sleep(0.1)

    assert session.review_index == 1, f"Index should be 1, got {session.review_index}"
    assert "instruction" in result, "Missing instruction field"
    assert result["question_id"] == FAKE_QUESTIONS[1].question_id
    print("  PASS: next_question function auto-advances and returns instruction")


async def test_full_review_cycle():
    """Full cycle: start → evaluate → evaluate → evaluate → done."""
    mgr = make_manager()
    session = UnifiedVoiceSession()

    with patch("services.voice_service.ReviewService") as MockRS:
        mock_svc = MockRS.return_value
        mock_svc.get_due = AsyncMock(return_value=DueResponse(
            questions=FAKE_QUESTIONS, total_due=3
        ))
        mock_svc.evaluate_answer = AsyncMock(return_value=make_evaluate_response(True))
        mock_svc.rate = AsyncMock()

        # Step 1: Start review
        r = json.loads(await mgr.handle_function_call(
            session, "start_review_session", {"recent_only": False}
        ))
        assert r["due_count"] == 3
        current_qid = r["first_question"]["question_id"]

        # Step 2-4: Answer each question
        for i in range(3):
            r = json.loads(await mgr.handle_function_call(
                session, "evaluate_answer",
                {"question_id": current_qid, "user_answer": f"Answer {i+1}"}
            ))
            assert r["score"] == "correct"

            if i < 2:
                assert r["done"] == False, f"Question {i+1}: should not be done yet"
                assert "next_question" in r
                assert "instruction" in r, f"Question {i+1}: missing instruction"
                current_qid = r["next_question"]["question_id"]
            else:
                assert r["done"] == True, "Last question: should be done"
                assert r["reviewed_count"] == 3
                assert r["correct_count"] == 3

    assert session.active_workflow is None
    assert len(session.rated_question_ids) == 3
    print("  PASS: Full review cycle (3 questions) completes successfully")


async def test_empty_review():
    """start_review_session with no due questions returns proper message."""
    mgr = make_manager()
    session = UnifiedVoiceSession()

    with patch("services.voice_service.ReviewService") as MockRS:
        mock_svc = MockRS.return_value
        mock_svc.get_due = AsyncMock(return_value=DueResponse(questions=[], total_due=0))

        r = json.loads(await mgr.handle_function_call(
            session, "start_review_session", {"recent_only": False}
        ))

    assert r["due_count"] == 0
    assert "message" in r
    assert session.active_workflow is None
    print("  PASS: Empty review session handled correctly")


async def main():
    print("\n=== Voice Review Flow E2E Tests ===\n")
    passed = 0
    failed = 0
    tests = [
        ("1. Start review returns first question", test_start_review_returns_first_question),
        ("2. Start review mid-session doesn't reset", None),  # needs session from test 1
        ("3. evaluate_answer advances correctly", test_evaluate_answer_advances),
        ("4. evaluate_answer completes review", test_evaluate_answer_completes_review),
        ("5. get_next_question auto-advances", test_get_next_question_auto_advances),
        ("6. next_question function works", test_next_question_function),
        ("7. Full review cycle (3 questions)", test_full_review_cycle),
        ("8. Empty review session", test_empty_review),
    ]

    # Test 1
    try:
        print(f"Test 1: Start review returns first question")
        session = await test_start_review_returns_first_question()
        passed += 1
    except Exception as e:
        print(f"  FAIL: {e}")
        failed += 1
        session = None

    # Test 2 (depends on test 1)
    try:
        print(f"Test 2: Start review mid-session doesn't reset")
        if session:
            await test_start_review_again_doesnt_reset(session)
            passed += 1
        else:
            print("  SKIP: depends on test 1")
    except Exception as e:
        print(f"  FAIL: {e}")
        failed += 1

    # Tests 3-7
    for name, test_fn in tests[2:]:
        try:
            print(f"Test {name}")
            await test_fn()
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}")
            failed += 1

    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
    if failed == 0:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
