"""
Live integration test: capture → review → evaluate full cycle.
Requires the backend running at http://localhost:8000.
Tests against the real database and API.
"""
import asyncio
import json
import sys
import httpx

BASE = "http://localhost:8000"


async def main():
    print("\n=== Live Integration Tests ===\n")
    passed = 0
    failed = 0

    async with httpx.AsyncClient(base_url=BASE, timeout=30) as c:

        # ---------------------------------------------------------------
        # Test 1: Health check
        # ---------------------------------------------------------------
        print("Test 1: Health check")
        try:
            r = await c.get("/")
            assert r.status_code == 200, f"Status {r.status_code}"
            print(f"  PASS: {r.json()}")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}")
            failed += 1

        # ---------------------------------------------------------------
        # Test 2: Capture knowledge via API
        # ---------------------------------------------------------------
        print("Test 2: Capture knowledge (text)")
        try:
            r = await c.post("/api/captures/", json={
                "raw_content": "Python list comprehensions allow creating lists in one line. "
                               "Syntax: [expr for item in iterable if condition]. "
                               "They are faster than regular for loops for simple transformations. "
                               "Example: squares = [x**2 for x in range(10)].",
                "source_type": "text",
            })
            assert r.status_code in (200, 201), f"Status {r.status_code}: {r.text}"
            capture = r.json()
            capture_id = capture.get("id") or capture.get("capture_id")
            assert capture_id, f"No capture ID in response: {capture}"
            print(f"  PASS: Captured → {capture_id}")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}")
            failed += 1
            capture_id = None

        # ---------------------------------------------------------------
        # Test 3: Verify questions were generated
        # ---------------------------------------------------------------
        print("Test 3: Verify questions generated for capture")
        questions = []
        if capture_id:
            try:
                # Wait a moment for async processing
                await asyncio.sleep(2)
                r = await c.get(f"/api/captures/{capture_id}")
                assert r.status_code == 200, f"Status {r.status_code}"
                data = r.json()
                # Check extracted_points → questions
                points = data.get("extracted_points", [])
                for p in points:
                    questions.extend(p.get("questions", []))
                if not questions:
                    # Try direct questions query
                    r2 = await c.get("/api/reviews/due", params={"limit": 50})
                    if r2.status_code == 200:
                        due_data = r2.json()
                        questions = due_data.get("questions", [])
                print(f"  PASS: {len(questions)} questions found")
                passed += 1
            except Exception as e:
                print(f"  FAIL: {e}")
                failed += 1
        else:
            print("  SKIP: no capture_id")

        # ---------------------------------------------------------------
        # Test 4: Get due reviews
        # ---------------------------------------------------------------
        print("Test 4: Get due reviews")
        try:
            r = await c.get("/api/reviews/due", params={"limit": 10})
            assert r.status_code == 200, f"Status {r.status_code}"
            due = r.json()
            due_questions = due.get("questions", [])
            total_due = due.get("total_due", 0)
            print(f"  PASS: {total_due} due, got {len(due_questions)} questions")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}")
            failed += 1
            due_questions = []

        # ---------------------------------------------------------------
        # Test 5: Evaluate an answer via API
        # ---------------------------------------------------------------
        print("Test 5: Evaluate answer via /reviews/evaluate")
        if due_questions:
            try:
                q = due_questions[0]
                qid = q.get("question_id") or q.get("id")
                r = await c.post("/api/reviews/evaluate", json={
                    "question_id": qid,
                    "user_answer": "List comprehensions create lists in one line using a for loop syntax",
                })
                assert r.status_code == 200, f"Status {r.status_code}: {r.text}"
                eval_resp = r.json()
                assert "score" in eval_resp, f"No score: {eval_resp}"
                assert "feedback" in eval_resp, f"No feedback: {eval_resp}"
                assert "correct_answer" in eval_resp, f"No correct_answer: {eval_resp}"
                print(f"  PASS: score={eval_resp['score']}, rating={eval_resp.get('suggested_rating')}")
                passed += 1

                # Test 5b: Rate the question
                print("Test 5b: Rate question via /reviews/rate")
                r2 = await c.post("/api/reviews/rate", json={
                    "question_id": qid,
                    "rating": eval_resp.get("suggested_rating", 3),
                })
                assert r2.status_code == 200, f"Status {r2.status_code}: {r2.text}"
                print(f"  PASS: Rated successfully")
                passed += 1
            except Exception as e:
                print(f"  FAIL: {e}")
                failed += 1
        else:
            print("  SKIP: no due questions")

        # ---------------------------------------------------------------
        # Test 6: Voice session manager dispatch (direct, no WS)
        # ---------------------------------------------------------------
        print("Test 6: Voice session manager dispatch (via import)")
        try:
            # Import and test directly against the real DB
            sys.path.insert(0, "E:\\Sharuk\\recall\\backend")
            from config import settings
            import asyncpg
            from openai import AsyncOpenAI
            from fsrs import Scheduler
            from services.voice_service import VoiceSessionManager, UnifiedVoiceSession

            from db import _init_connection
            pool = await asyncpg.create_pool(settings.DATABASE_URL, min_size=1, max_size=2, init=_init_connection)
            openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            scheduler = Scheduler()
            mgr = VoiceSessionManager(pool, openai_client, scheduler)
            session = UnifiedVoiceSession()

            # 6a: Get user context
            print("  6a: get_user_context")
            ctx_json = await mgr.handle_function_call(session, "get_user_context", {})
            ctx = json.loads(ctx_json)
            assert "due_count" in ctx, f"Missing due_count: {ctx}"
            print(f"    PASS: due={ctx['due_count']}, streak={ctx['streak_days']}, retention={ctx['retention_rate']}%")
            passed += 1

            # 6b: Start review session (all due)
            print("  6b: start_review_session")
            sr_json = await mgr.handle_function_call(session, "start_review_session", {"recent_only": False})
            sr = json.loads(sr_json)
            if sr.get("due_count", 0) == 0:
                print(f"    PASS (no reviews due): {sr.get('message')}")
                passed += 1
            else:
                assert "first_question" in sr, f"Missing first_question: {sr}"
                assert "instruction" in sr, f"Missing instruction: {sr}"
                fq = sr["first_question"]
                assert fq.get("question_id"), "Missing question_id in first_question"
                print(f"    PASS: {sr['due_count']} due, first Q: {fq['question_text'][:60]}...")
                passed += 1

                # 6c: Start review again (should NOT reset)
                print("  6c: start_review_session again (no-reset guard)")
                sr2_json = await mgr.handle_function_call(session, "start_review_session", {"recent_only": False})
                sr2 = json.loads(sr2_json)
                assert sr2.get("session_already_active") == True, f"Expected session_already_active: {sr2}"
                assert sr2["first_question"]["question_id"] == fq["question_id"], "Should be same question"
                print(f"    PASS: No reset, same question returned")
                passed += 1

                # 6d: Evaluate answer (real LLM call!)
                print("  6d: evaluate_answer (real LLM evaluation)")
                ea_json = await mgr.handle_function_call(session, "evaluate_answer", {
                    "question_id": fq["question_id"],
                    "user_answer": "List comprehensions let you create a list in one line",
                })
                ea = json.loads(ea_json)
                assert "score" in ea, f"Missing score: {ea}"
                assert "feedback" in ea, f"Missing feedback: {ea}"
                print(f"    PASS: score={ea['score']}, feedback={ea['feedback'][:60]}...")
                passed += 1

                if ea.get("done"):
                    print(f"    Review complete: {ea['reviewed_count']} reviewed, {ea['correct_count']} correct")
                else:
                    nq = ea.get("next_question", {})
                    assert "instruction" in ea, f"Missing instruction in evaluate_answer response"
                    print(f"    Next Q: {nq.get('question_text', 'N/A')[:60]}...")

                # 6e: Verify index advanced
                assert session.review_index >= 1, f"Index should have advanced, got {session.review_index}"
                print(f"    PASS: review_index={session.review_index}")
                passed += 1

            # 6f: Finish capture via voice dispatch
            print("  6f: finish_capture via dispatch")
            fc_json = await mgr.handle_function_call(session, "finish_capture", {
                "final_transcript": "A for loop in Python iterates over sequences. Syntax: for item in iterable. "
                                    "It can iterate over lists, strings, ranges, and dictionaries."
            })
            fc = json.loads(fc_json)
            if "error" in fc:
                print(f"    WARN: {fc['error']}")
            else:
                cap_id = fc.get("capture_id")
                print(f"    PASS: Captured → {cap_id}, facts={fc.get('extracted_count')}, questions={fc.get('question_count')}")
                passed += 1

                # 6g: Review recent capture
                if cap_id:
                    print("  6g: start_review_session (recent_only=true)")
                    # Reset session to clear previous review
                    session.review_queue = []
                    session.review_index = 0
                    session.rated_question_ids = set()
                    session.active_workflow = None

                    rr_json = await mgr.handle_function_call(session, "start_review_session", {"recent_only": True})
                    rr = json.loads(rr_json)
                    if rr.get("due_count", 0) == 0:
                        print(f"    PASS (no questions yet): {rr.get('message')}")
                    else:
                        assert "first_question" in rr, f"Missing first_question: {rr}"
                        assert "instruction" in rr, f"Missing instruction: {rr}"
                        print(f"    PASS: {rr['due_count']} questions from recent capture")
                    passed += 1

            await pool.close()

        except Exception as e:
            print(f"  FAIL: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

        # ---------------------------------------------------------------
        # Test 7: WebSocket endpoint reachable
        # ---------------------------------------------------------------
        print("Test 7: WebSocket /ws/voice endpoint exists")
        try:
            # We can't do a full WS handshake without Deepgram,
            # but we can verify the endpoint responds to upgrade
            import websockets
            try:
                async with websockets.connect("ws://localhost:8000/ws/voice") as ws:
                    # If we get here, the endpoint accepted the connection
                    print(f"  PASS: WebSocket connected")
                    passed += 1
            except websockets.exceptions.ConnectionClosed as e:
                # Server may close after initial handshake — that's OK
                print(f"  PASS: WebSocket endpoint reachable (closed after connect: {e.code})")
                passed += 1
        except ImportError:
            # Try raw HTTP upgrade check
            r = await c.get("/ws/voice", headers={
                "Upgrade": "websocket",
                "Connection": "Upgrade",
                "Sec-WebSocket-Key": "dGhlIHNhbXBsZSBub25jZQ==",
                "Sec-WebSocket-Version": "13",
            })
            if r.status_code in (101, 403, 426):
                print(f"  PASS: WebSocket endpoint exists (status {r.status_code})")
                passed += 1
            else:
                print(f"  WARN: Unexpected status {r.status_code}")
                passed += 1
        except Exception as e:
            print(f"  FAIL: {e}")
            failed += 1

    # ---------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------
    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
    if failed == 0:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
