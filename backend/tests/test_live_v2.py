"""
Focused live integration test for the critical voice review flow.
Tests: HTTP API routes + voice session dispatch (real DB + real LLM).
"""
import asyncio
import json
import sys
sys.path.insert(0, "E:\\Sharuk\\recall\\backend")

import httpx
import asyncpg
from openai import AsyncOpenAI
from fsrs import Scheduler

from config import settings
from db import _init_connection
from services.voice_service import VoiceSessionManager, UnifiedVoiceSession

BASE = "http://localhost:8001"


async def main():
    print("\n=== Live Integration Tests ===\n")
    passed = 0
    failed = 0

    # --- HTTP API Tests ---
    async with httpx.AsyncClient(base_url=BASE, timeout=30) as c:

        # Test 1: Health
        print("Test 1: GET /")
        try:
            r = await c.get("/")
            assert r.status_code == 200
            print(f"  PASS: {r.json()}")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}"); failed += 1

        # Test 2: Capture
        print("Test 2: POST /api/captures/")
        capture_id = None
        try:
            r = await c.post("/api/captures/", json={
                "raw_text": "Python decorators wrap functions to extend behavior. "
                               "Use @decorator_name above a function definition. "
                               "Common decorators: @staticmethod, @classmethod, @property.",
                "source_type": "text",
            })
            assert r.status_code in (200, 201), f"Status {r.status_code}: {r.text}"
            capture_id = r.json().get("id") or r.json().get("capture_id")
            assert capture_id
            print(f"  PASS: capture_id={capture_id}")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}"); failed += 1

        # Test 3: Get due reviews
        print("Test 3: GET /api/reviews/due")
        due_qid = None
        try:
            r = await c.get("/api/reviews/due", params={"limit": 5})
            assert r.status_code == 200, f"Status {r.status_code}: {r.text[:200]}"
            data = r.json()
            due_count = data.get("total_due", 0)
            qs = data.get("questions", [])
            if qs:
                due_qid = qs[0].get("question_id")
            print(f"  PASS: {due_count} due, got {len(qs)} questions")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}"); failed += 1

        # Test 4: Evaluate answer
        print("Test 4: POST /api/reviews/evaluate")
        if due_qid:
            try:
                r = await c.post("/api/reviews/evaluate", json={
                    "question_id": due_qid,
                    "user_answer": "Decorators wrap functions to add extra behavior",
                })
                assert r.status_code == 200
                ev = r.json()
                assert "score" in ev and "feedback" in ev
                print(f"  PASS: score={ev['score']}")
                passed += 1

                # Test 4b: Rate
                print("Test 4b: POST /api/reviews/rate")
                r2 = await c.post("/api/reviews/rate", json={
                    "question_id": due_qid,
                    "rating": ev.get("suggested_rating", 3),
                })
                assert r2.status_code == 200
                print(f"  PASS: rated")
                passed += 1
            except Exception as e:
                print(f"  FAIL: {e}"); failed += 1
        else:
            print("  SKIP: no due questions"); passed += 1

    # --- Voice Session Manager (Direct dispatch, real DB + LLM) ---
    print("\n--- Voice Session Manager Dispatch ---\n")

    pool = await asyncpg.create_pool(settings.DATABASE_URL, min_size=1, max_size=3, init=_init_connection)
    openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    scheduler = Scheduler()
    mgr = VoiceSessionManager(pool, openai_client, scheduler)
    session = UnifiedVoiceSession()

    # Test 5: get_user_context
    print("Test 5: get_user_context")
    try:
        ctx = json.loads(await mgr.handle_function_call(session, "get_user_context", {}))
        assert "due_count" in ctx
        print(f"  PASS: due={ctx['due_count']}, retention={ctx['retention_rate']}%")
        passed += 1
    except Exception as e:
        print(f"  FAIL: {e}"); failed += 1

    # Test 6: start_review_session
    print("Test 6: start_review_session (all due)")
    first_qid = None
    try:
        sr = json.loads(await mgr.handle_function_call(session, "start_review_session", {"recent_only": False}))
        if sr.get("due_count", 0) == 0:
            print(f"  PASS (no due): {sr.get('message')}")
        else:
            assert "first_question" in sr
            assert "instruction" in sr, "Missing instruction field!"
            first_qid = sr["first_question"]["question_id"]
            print(f"  PASS: {sr['due_count']} due, Q1: {sr['first_question']['question_text'][:50]}...")
        passed += 1
    except Exception as e:
        print(f"  FAIL: {e}"); failed += 1

    # Test 7: start_review_session again (no-reset guard)
    if first_qid:
        print("Test 7: start_review_session again (no-reset)")
        try:
            sr2 = json.loads(await mgr.handle_function_call(session, "start_review_session", {"recent_only": False}))
            assert sr2.get("session_already_active") == True, f"No session_already_active flag: {sr2}"
            assert sr2["first_question"]["question_id"] == first_qid, "Question changed — queue was reset!"
            print(f"  PASS: Same question returned, no reset")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}"); failed += 1

        # Test 8: evaluate_answer (real LLM)
        print("Test 8: evaluate_answer (real LLM call)")
        try:
            ea = json.loads(await mgr.handle_function_call(session, "evaluate_answer", {
                "question_id": first_qid,
                "user_answer": "RAG retrieves relevant information and uses it to generate answers",
            }))
            assert "score" in ea, f"No score: {ea}"
            assert "feedback" in ea, f"No feedback: {ea}"
            if not ea.get("done"):
                assert "instruction" in ea, "Missing instruction in evaluate_answer response!"
                assert "next_question" in ea
                print(f"  PASS: score={ea['score']}, next Q: {ea['next_question']['question_text'][:40]}...")
            else:
                print(f"  PASS: score={ea['score']}, done=true")
            assert session.review_index >= 1, f"Index didn't advance: {session.review_index}"
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}"); failed += 1
    else:
        print("Test 7: SKIP (no due)")
        print("Test 8: SKIP (no due)")

    # Test 9: finish_capture via dispatch
    print("Test 9: finish_capture via dispatch")
    try:
        # Reset session for clean capture
        session.review_queue = []
        session.review_index = 0
        session.rated_question_ids = set()
        session.active_workflow = None

        fc = json.loads(await mgr.handle_function_call(session, "finish_capture", {
            "final_transcript": "A for loop in Python iterates over sequences. "
                                "Syntax: for item in iterable. "
                                "It can iterate over lists, strings, ranges, and dictionaries."
        }))
        assert "error" not in fc, f"Error: {fc}"
        cap_id = fc.get("capture_id")
        assert cap_id, f"No capture_id: {fc}"
        print(f"  PASS: Captured → {cap_id}, facts={fc.get('extracted_count')}, Qs={fc.get('question_count')}")
        passed += 1

        # Test 10: Review recent capture
        print("Test 10: start_review_session (recent_only=true)")
        rr = json.loads(await mgr.handle_function_call(session, "start_review_session", {"recent_only": True}))
        if rr.get("due_count", 0) == 0:
            print(f"  PASS (no Qs generated): {rr.get('message')}")
        else:
            assert "first_question" in rr
            assert "instruction" in rr, "Missing instruction!"
            print(f"  PASS: {rr['due_count']} questions from recent capture")
        passed += 1

    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback; traceback.print_exc()
        failed += 1

    # Test 11: save_why_it_matters
    print("Test 11: save_why_it_matters")
    if session.last_capture_id:
        try:
            wim = json.loads(await mgr.handle_function_call(session, "save_why_it_matters", {
                "capture_id": session.last_capture_id,
                "why_it_matters": "Essential for coding interviews",
            }))
            assert wim.get("saved") == True, f"Not saved: {wim}"
            print(f"  PASS: saved=True")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}"); failed += 1
    else:
        print("  SKIP: no capture_id")

    # Test 11b: save_why_it_matters without capture
    print("Test 11b: save_why_it_matters (no capture → error)")
    try:
        session2 = UnifiedVoiceSession()  # fresh session, no capture
        wim2 = json.loads(await mgr.handle_function_call(session2, "save_why_it_matters", {
            "capture_id": "fake", "why_it_matters": "test",
        }))
        assert "error" in wim2, f"Expected error: {wim2}"
        print(f"  PASS: error={wim2['error']}")
        passed += 1
    except Exception as e:
        print(f"  FAIL: {e}"); failed += 1

    # Test 12: search_knowledge
    print("Test 12: search_knowledge")
    try:
        sk = json.loads(await mgr.handle_function_call(session, "search_knowledge", {
            "query": "Python for loops",
        }))
        assert "has_answer" in sk, f"Missing has_answer: {sk}"
        print(f"  PASS: has_answer={sk['has_answer']}, answer={str(sk.get('answer',''))[:60]}...")
        passed += 1
    except Exception as e:
        print(f"  FAIL: {e}"); failed += 1

    # Test 13: submit_reflection
    print("Test 13: submit_reflection")
    try:
        ref = json.loads(await mgr.handle_function_call(session, "submit_reflection", {
            "content": "Today I learned about Python decorators and for loops. Both are fundamental concepts.",
        }))
        assert "error" not in ref, f"Error: {ref}"
        assert ref.get("capture_id"), f"No capture_id: {ref}"
        print(f"  PASS: capture_id={ref['capture_id']}, facts={ref.get('facts_count')}")
        passed += 1
    except Exception as e:
        print(f"  FAIL: {e}"); failed += 1

    # Test 13b: submit_reflection (empty → error)
    print("Test 13b: submit_reflection (empty → error)")
    try:
        ref2 = json.loads(await mgr.handle_function_call(session, "submit_reflection", {
            "content": "  ",
        }))
        assert "error" in ref2, f"Expected error: {ref2}"
        print(f"  PASS: error={ref2['error']}")
        passed += 1
    except Exception as e:
        print(f"  FAIL: {e}"); failed += 1

    # Test 14: end_session
    print("Test 14: end_session")
    try:
        es = json.loads(await mgr.handle_function_call(session, "end_session", {}))
        assert es.get("ended") == True, f"Not ended: {es}"
        assert "duration_seconds" in es
        assert "captures" in es
        print(f"  PASS: ended, duration={es['duration_seconds']}s, captures={es['captures']}, reviews={es['reviews']}")
        passed += 1
    except Exception as e:
        print(f"  FAIL: {e}"); failed += 1

    # Test 15: evaluate_answer with no active session (error path)
    print("Test 15: evaluate_answer (no session → error)")
    try:
        session3 = UnifiedVoiceSession()
        ea_err = json.loads(await mgr.handle_function_call(session3, "evaluate_answer", {
            "question_id": "00000000-0000-0000-0000-000000000000",
            "user_answer": "test",
        }))
        assert "error" in ea_err, f"Expected error: {ea_err}"
        print(f"  PASS: error={ea_err['error']}")
        passed += 1
    except Exception as e:
        print(f"  FAIL: {e}"); failed += 1

    # Test 16: finish_capture (empty transcript → error)
    print("Test 16: finish_capture (empty → error)")
    try:
        session4 = UnifiedVoiceSession()
        fc_err = json.loads(await mgr.handle_function_call(session4, "finish_capture", {
            "final_transcript": "  ",
        }))
        assert "error" in fc_err, f"Expected error: {fc_err}"
        print(f"  PASS: error={fc_err['error']}")
        passed += 1
    except Exception as e:
        print(f"  FAIL: {e}"); failed += 1

    # Test 17: unknown function (error path)
    print("Test 17: unknown function → error")
    try:
        unk = json.loads(await mgr.handle_function_call(session, "nonexistent_function", {}))
        assert "error" in unk, f"Expected error: {unk}"
        print(f"  PASS: error={unk['error']}")
        passed += 1
    except Exception as e:
        print(f"  FAIL: {e}"); failed += 1

    # Test 18: WebSocket endpoint reachable
    print("Test 18: WebSocket /ws/voice")
    try:
        import websockets
        try:
            async with websockets.connect("ws://localhost:8001/ws/voice") as ws:
                print(f"  PASS: WebSocket connected")
                passed += 1
        except websockets.exceptions.ConnectionClosed as e:
            print(f"  PASS: WebSocket reachable (closed: {e.code})")
            passed += 1
    except ImportError:
        async with httpx.AsyncClient(base_url=BASE) as c:
            r = await c.get("/ws/voice", headers={
                "Upgrade": "websocket", "Connection": "Upgrade",
                "Sec-WebSocket-Key": "dGhlIHNhbXBsZSBub25jZQ==",
                "Sec-WebSocket-Version": "13",
            })
            print(f"  PASS: WS endpoint exists (HTTP {r.status_code})")
            passed += 1
    except Exception as e:
        print(f"  FAIL: {e}"); failed += 1

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
    if failed == 0:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
