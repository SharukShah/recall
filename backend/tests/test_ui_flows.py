"""
UI Flow Integration Tests — simulates every API call the frontend makes.
Tests every page, every component, every user action.
Run: python tests/test_ui_flows.py
Requires: backend running on localhost:8000
"""
import asyncio
import json
import httpx

BASE = "http://localhost:8000"
passed = 0
failed = 0
results = []


def ok(name, detail=""):
    global passed
    passed += 1
    d = f" ({detail})" if detail else ""
    print(f"  ✓ {name}{d}")


def fail(name, err):
    global failed
    failed += 1
    print(f"  ✗ {name} — {err}")

async def main():
    global passed, failed

    async with httpx.AsyncClient(
        base_url=BASE, follow_redirects=True, timeout=60
    ) as c:

        print("=" * 60)
        print("UI FLOW INTEGRATION TESTS")
        print("=" * 60)

        # ===== PAGE 1: DASHBOARD (/) =====
        print("\n--- PAGE 1: DASHBOARD ---")

        try:
            r = await c.get("/api/stats/dashboard")
            assert r.status_code == 200
            d = r.json()
            assert "due_today" in d
            assert "streak_days" in d
            assert "retention_rate" in d
            assert "total_captures" in d
            assert "total_questions" in d
            ok("Dashboard stats load", f"due={d['due_today']}, streak={d['streak_days']}, retention={d['retention_rate']}%")
        except Exception as e:
            fail("Dashboard stats", e)

        # ===== PAGE 2: CAPTURE (/capture) =====
        print("\n--- PAGE 2: CAPTURE ---")

        try:
            r = await c.get("/api/captures/tags")
            assert r.status_code == 200
            ok("Load tags", f"{len(r.json())} tags")
        except Exception as e:
            fail("Load tags", e)

        capture_id = None
        try:
            r = await c.post("/api/captures/", json={
                "raw_text": "Binary search works by dividing a sorted array in half repeatedly. Time complexity is O(log n). It requires the array to be sorted first.",
                "source_type": "text"
            })
            assert r.status_code == 200
            d = r.json()
            capture_id = d.get("capture_id")
            assert capture_id, "No capture_id returned"
            ok("Text capture", f"id={capture_id[:8]}..., facts={d.get('facts_count')}, qs={d.get('questions_count')}")
        except Exception as e:
            fail("Text capture", e)

        if capture_id:
            try:
                r = await c.get(f"/api/captures/{capture_id}")
                assert r.status_code == 200
                d = r.json()
                assert d.get("raw_text"), "No raw_text"
                ok("Capture detail", f"points={len(d.get('extracted_points', []))}")
            except Exception as e:
                fail("Capture detail", e)

        # ===== PAGE 3: REVIEW (/review) =====
        print("\n--- PAGE 3: REVIEW ---")

        due_questions = []
        try:
            r = await c.get("/api/reviews/due?limit=5")
            assert r.status_code == 200
            d = r.json()
            due_questions = d.get("questions", [])
            ok("Get due questions", f"{d.get('total_due', 0)} due, got {len(due_questions)}")
        except Exception as e:
            fail("Get due questions", e)

        if due_questions:
            q = due_questions[0]
            q_id = q["question_id"]

            # Evaluate answer
            try:
                r = await c.post("/api/reviews/evaluate", json={
                    "question_id": q_id,
                    "user_answer": "Binary search divides the array in half each time"
                })
                assert r.status_code == 200
                d = r.json()
                assert "score" in d
                ok("Evaluate answer", f"score={d['score']}")
            except Exception as e:
                fail("Evaluate answer", e)

            # Rate
            try:
                r = await c.post("/api/reviews/rate", json={
                    "question_id": q_id,
                    "rating": 3
                })
                assert r.status_code == 200
                ok("Rate answer (Good)")
            except Exception as e:
                fail("Rate answer", e)

        # ===== PAGE 4: QUESTIONS (/questions) =====
        print("\n--- PAGE 4: QUESTIONS ---")

        try:
            r = await c.get("/api/questions/?limit=5")
            assert r.status_code == 200
            d = r.json()
            ok("List questions", f"{d.get('total', 0)} total")
        except Exception as e:
            fail("List questions", e)

        try:
            r = await c.get("/api/questions/?search=binary&limit=5")
            assert r.status_code == 200
            ok("Search questions", f"{r.json().get('total', 0)} matches for 'binary'")
        except Exception as e:
            fail("Search questions", e)

        try:
            r = await c.get("/api/questions/?question_type=recall&limit=5")
            assert r.status_code == 200
            ok("Filter by type", f"{r.json().get('total', 0)} recall questions")
        except Exception as e:
            fail("Filter by type", e)

        try:
            r = await c.get("/api/questions/stats/summary")
            assert r.status_code == 200
            d = r.json()
            ok("Question stats", f"{d.get('total_questions', 0)} questions, {len(d.get('by_type', []))} types")
        except Exception as e:
            fail("Question stats", e)

        # Get a question detail
        q_detail_id = None
        try:
            r = await c.get("/api/questions/?limit=1")
            qs = r.json().get("questions", [])
            if qs:
                q_detail_id = qs[0]["id"]
                r2 = await c.get(f"/api/questions/{q_detail_id}")
                assert r2.status_code == 200
                ok("Question detail", f"type={r2.json().get('question_type')}")
        except Exception as e:
            fail("Question detail", e)

        # ===== PAGE 5: HISTORY (/history) =====
        print("\n--- PAGE 5: HISTORY ---")

        try:
            r = await c.get("/api/captures/?limit=5")
            assert r.status_code == 200
            d = r.json()
            assert isinstance(d, list)
            ok("Capture list", f"{len(d)} captures")
        except Exception as e:
            fail("Capture list", e)

        # ===== PAGE 6: SEARCH (/search) =====
        print("\n--- PAGE 6: SEARCH ---")

        try:
            r = await c.post("/api/knowledge/search", json={
                "query": "How does binary search work?"
            })
            assert r.status_code == 200
            d = r.json()
            ok("Knowledge search", f"answer={str(d.get('answer', ''))[:60]}...")
        except Exception as e:
            fail("Knowledge search", e)

        # ===== PAGE 7: TEACH (/teach) =====
        print("\n--- PAGE 7: TEACH ---")

        try:
            r = await c.post("/api/teach/start", json={"topic": "binary search"})
            assert r.status_code == 200
            d = r.json()
            ok("Start teach session", f"session_id={str(d.get('session_id', ''))[:8]}...")
        except Exception as e:
            fail("Start teach", e)

        # ===== PAGE 8: REFLECT (/reflect) =====
        print("\n--- PAGE 8: REFLECT ---")

        try:
            r = await c.get("/api/reflections/status")
            assert r.status_code == 200
            ok("Reflection status", f"can_reflect={r.json().get('can_reflect')}")
        except Exception as e:
            fail("Reflection status", e)

        try:
            r = await c.get("/api/reflections/?limit=5")
            assert r.status_code == 200
            d = r.json()
            assert isinstance(d, list)
            ok("Reflection list", f"{len(d)} reflections")
        except Exception as e:
            fail("Reflection list", e)

        # ===== PAGE 9: ANALYTICS (/analytics) =====
        print("\n--- PAGE 9: ANALYTICS ---")

        try:
            r = await c.get("/api/stats/analytics")
            assert r.status_code == 200
            d = r.json()
            ok("Analytics summary", f"reviews={d.get('summary',{}).get('total_reviews_all_time',0)}")
        except Exception as e:
            fail("Analytics summary", e)

        try:
            r = await c.get("/api/stats/retention-curve?weeks=12")
            assert r.status_code == 200
            ok("Retention curve", f"{len(r.json().get('data_points', []))} weeks")
        except Exception as e:
            fail("Retention curve", e)

        try:
            r = await c.get("/api/stats/weak-areas?limit=10")
            assert r.status_code == 200
            ok("Weak areas", f"{len(r.json().get('weak_areas', []))} areas")
        except Exception as e:
            fail("Weak areas", e)

        try:
            r = await c.get("/api/stats/activity?days=90")
            assert r.status_code == 200
            ok("Activity heatmap", f"{len(r.json().get('days', []))} days")
        except Exception as e:
            fail("Activity heatmap", e)

        # ===== PAGE 10: GRAPH (/graph) =====
        print("\n--- PAGE 10: KNOWLEDGE GRAPH ---")

        try:
            r = await c.get("/api/graph/data")
            assert r.status_code == 200
            d = r.json()
            ok("Graph data", f"{len(d.get('nodes', []))} nodes, {len(d.get('edges', []))} edges")
        except Exception as e:
            fail("Graph data", e)

        # ===== PAGE 11: LOCI (/loci) =====
        print("\n--- PAGE 11: METHOD OF LOCI ---")

        try:
            r = await c.get("/api/loci/?limit=5")
            assert r.status_code == 200
            d = r.json()
            assert isinstance(d, list)
            ok("Loci sessions", f"{len(d)} sessions")
        except Exception as e:
            fail("Loci sessions", e)

        # ===== PAGE 12: SETTINGS (/settings) =====
        print("\n--- PAGE 12: SETTINGS ---")

        try:
            r = await c.get("/api/notifications/settings")
            assert r.status_code == 200
            ok("Notification settings")
        except Exception as e:
            fail("Notification settings", e)

        # Note: Export endpoints not yet implemented — skipped

        # ===== PAGE 13: STATS — TOPIC COVERAGE / WEAK AREAS / STREAK =====
        print("\n--- PAGE 13: STATS (coverage / weak areas / streak) ---")

        try:
            r = await c.get("/api/stats/topic-coverage")
            assert r.status_code == 200
            d = r.json()
            ok("Topic coverage", f"{len(d.get('categories', []))} categories, {d.get('uncategorized_count', 0)} uncategorized")
        except Exception as e:
            fail("Topic coverage", e)

        try:
            r = await c.get("/api/stats/weak-categories")
            assert r.status_code == 200
            ok("Weak categories", f"{len(r.json().get('weak_categories', []))} weak")
        except Exception as e:
            fail("Weak categories", e)

        try:
            r = await c.get("/api/stats/streak-info")
            assert r.status_code == 200
            d = r.json()
            ok("Streak info", f"streak={d['current_streak']}, at_risk={d['streak_at_risk']}, next={d.get('next_milestone')}")
        except Exception as e:
            fail("Streak info", e)

        # ===== PAGE 17: FOCUS SESSION (/review?categories=...) =====
        print("\n--- PAGE 17: FOCUS SESSION ---")

        try:
            r = await c.post("/api/reviews/focus-session", json={
                "categories": ["python_basics", "dsa"],
                "limit": 10
            })
            assert r.status_code == 200
            d = r.json()
            ok("Focus session", f"{d.get('total_due', 0)} questions in python_basics+dsa")
        except Exception as e:
            fail("Focus session", e)

        # ===== VOICE AGENT FUNCTIONS =====
        print("\n--- PAGE 18: VOICE AGENT (function dispatch) ---")

        # Simulate voice agent function calls via the service layer
        try:
            # We test voice functions by importing the service directly
            import sys, os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from services.voice_service import VoiceSessionManager
            import asyncpg
            from openai import AsyncOpenAI
            from fsrs import Scheduler
            from config import settings

            pool = await asyncpg.create_pool(settings.DATABASE_URL, min_size=1, max_size=2)
            openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            scheduler = Scheduler()

            mgr = VoiceSessionManager(pool, openai_client, scheduler)
            from services.voice_service import UnifiedVoiceSession
            session = UnifiedVoiceSession()

            # 1. get_user_context
            ctx = await mgr._dispatch(session, "get_user_context", {})
            ok("Voice: get_user_context", f"due={ctx.get('due_count')}, streak={ctx.get('streak')}")

            # 2. start_review_session
            rev = await mgr._dispatch(session, "start_review_session", {"limit": 5})
            ok("Voice: start_review_session", f"{rev.get('total_questions', 0)} questions loaded")

            # 3. evaluate_answer
            if rev.get("question_id"):
                ev = await mgr._dispatch(session, "evaluate_answer", {
                    "question_id": rev["question_id"],
                    "user_answer": "Binary search divides sorted array in half"
                })
                ok("Voice: evaluate_answer", f"score={ev.get('score')}")

            # 4. next_question
            nq = await mgr._dispatch(session, "next_question", {})
            ok("Voice: next_question", f"done={nq.get('done', False)}")

            # 5. finish_capture
            cap = await mgr._dispatch(session, "finish_capture", {
                "final_transcript": "Linked lists use nodes with pointers. Each node points to the next. Insertion is O(1) at head."
            })
            ok("Voice: finish_capture", f"capture_id={str(cap.get('capture_id', ''))[:8]}...")

            # 6. save_why_it_matters
            wim = await mgr._dispatch(session, "save_why_it_matters", {
                "capture_id": cap.get("capture_id", ""),
                "why_it_matters": "Important for understanding data structures"
            })
            ok("Voice: save_why_it_matters", f"saved={wim.get('saved')}")

            # 7. search_knowledge
            sk = await mgr._dispatch(session, "search_knowledge", {"query": "binary search"})
            ok("Voice: search_knowledge", f"has_answer={sk.get('has_answer')}")

            # 8. submit_reflection
            ref = await mgr._dispatch(session, "submit_reflection", {
                "content": "Today I learned about binary search and linked lists. Both are fundamental data structures."
            })
            ok("Voice: submit_reflection", f"capture_id={str(ref.get('capture_id',''))[:8]}...")

            # 12. start_focus_review
            fr = await mgr._dispatch(session, "start_focus_review", {
                "categories": ["python_basics"],
                "limit": 5
            })
            ok("Voice: start_focus_review", f"{fr.get('total_questions', 0)} focus questions")

            # 16. end_session
            es = await mgr._dispatch(session, "end_session", {})
            ok("Voice: end_session", f"duration={es.get('duration_seconds')}s")

            await pool.close()
        except Exception as e:
            fail(f"Voice agent functions", e)

        # ===== SUMMARY =====
        print("\n" + "=" * 60)
        total = passed + failed
        print(f"Results: {passed} passed, {failed} failed, {total} total")
        if failed == 0:
            print("ALL TESTS PASSED")
        else:
            print("SOME TESTS FAILED")
        print("=" * 60)

    return failed


if __name__ == "__main__":
    import sys
    code = asyncio.run(main())
    sys.exit(1 if code > 0 else 0)
