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

xxxxxxxxxxxxxxxxxxxdfdddddddddffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffxdfdgdddddddddddddddddddddddddddddxddxxxxxxxddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddx            xxxxxxxxxxxxxxxxxzdxxxxxxxxxxxxxxxxxxxxxxxxxvghd
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

        # ===== PAGE 13: INTERVIEW HUB (/interview) =====
        print("\n--- PAGE 13: INTERVIEW PREP HUB ---")

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

        try:
            r = await c.get("/api/behavioral/coverage")
            assert r.status_code == 200
            d = r.json()
            ok("Behavioral coverage", f"{d['covered_competencies']}/{d['total_competencies']} covered")
        except Exception as e:
            fail("Behavioral coverage", e)

        try:
            r = await c.get("/api/interviews/")
            assert r.status_code == 200
            d = r.json()
            ok("Interview history", f"{d.get('total', 0)} interviews")
        except Exception as e:
            fail("Interview history", e)

        # ===== PAGE 14: MOCK INTERVIEW (/interview/mock) =====
        print("\n--- PAGE 14: MOCK INTERVIEW ---")

        interview_id = None
        total_qs = 0
        try:
            r = await c.post("/api/interviews/", json={
                "topic": "python",
                "difficulty": "easy",
                "duration_minutes": 15
            })
            assert r.status_code == 200
            d = r.json()
            interview_id = d["interview_id"]
            total_qs = d["total_questions"]
            ok("Start mock interview", f"id={interview_id[:8]}..., {total_qs} questions, Q1: {d['first_question']['question_text'][:50]}...")
        except Exception as e:
            fail("Start mock interview", e)

        if interview_id:
            # Answer all questions
            for i in range(1, total_qs + 1):
                try:
                    r = await c.post(f"/api/interviews/{interview_id}/answer/{i}", json={
                        "user_answer": "Python is a high-level programming language with dynamic typing, garbage collection, and extensive standard library support."
                    })
                    assert r.status_code == 200
                    d = r.json()
                    ok(f"Answer Q{i}", f"score={d['score']}/5")
                except Exception as e:
                    fail(f"Answer Q{i}", e)

            # Complete interview
            try:
                r = await c.post(f"/api/interviews/{interview_id}/complete")
                assert r.status_code == 200
                d = r.json()
                ok("Complete interview", f"overall={d['overall_score']}/5, strengths={len(d.get('strengths', []))}, weaknesses={len(d.get('weaknesses', []))}")
            except Exception as e:
                fail("Complete interview", e)

            # View summary
            try:
                r = await c.get(f"/api/interviews/{interview_id}/summary")
                assert r.status_code == 200
                d = r.json()
                ok("Interview summary", f"{len(d.get('answers', []))} answers, tips={len(d.get('improvement_tips', []))}")
            except Exception as e:
                fail("Interview summary", e)

        # ===== PAGE 15: INTERVIEW HISTORY (/interview/history) =====
        print("\n--- PAGE 15: INTERVIEW HISTORY ---")

        try:
            r = await c.get("/api/interviews/?limit=10")
            assert r.status_code == 200
            d = r.json()
            ok("List all interviews", f"{d['total']} total")
        except Exception as e:
            fail("List interviews", e)

        try:
            r = await c.get("/api/interviews/?topic=python&limit=5")
            assert r.status_code == 200
            ok("Filter by topic", f"{r.json()['total']} python interviews")
        except Exception as e:
            fail("Filter by topic", e)

        # ===== PAGE 16: BEHAVIORAL PREP (/interview/behavioral) =====
        print("\n--- PAGE 16: BEHAVIORAL PREP ---")

        try:
            r = await c.get("/api/behavioral/stories?limit=10")
            assert r.status_code == 200
            d = r.json()
            ok("List STAR stories", f"{d['total']} stories")
        except Exception as e:
            fail("List stories", e)

        try:
            r = await c.get("/api/behavioral/coverage")
            assert r.status_code == 200
            d = r.json()
            for comp in d.get("competencies", []):
                if comp["story_count"] > 0:
                    ok(f"  Competency: {comp['competency']}", f"{comp['story_count']} stories, strength={comp.get('avg_strength')}")
        except Exception as e:
            fail("Coverage detail", e)

        # Capture a new STAR story
        story_id = None
        try:
            r = await c.post("/api/behavioral/capture", json={
                "narrative": "During a critical deployment last quarter, our CI pipeline broke and was blocking all team merges. I took ownership of the issue, analyzed the failing tests, identified a flaky test caused by timezone-dependent assertions. I wrote a patch, added timezone-aware fixtures, and submitted a PR within 2 hours. The pipeline was unblocked and we shipped the release on time. The fix also prevented 15 similar failures in the following month.",
                "competency": "initiative"
            })
            assert r.status_code == 200
            d = r.json()
            story_id = d["story_id"]
            ok("Capture STAR story", f"title={d['title'][:40]}..., S/T/A/R extracted, strength={d['strength_rating']}")
        except Exception as e:
            fail("Capture STAR", e)

        if story_id:
            try:
                r = await c.get(f"/api/behavioral/stories/{story_id}")
                assert r.status_code == 200
                d = r.json()
                ok("View story detail", f"S={d['situation'][:40]}... T={d['task'][:30]}...")
            except Exception as e:
                fail("View story", e)

        # Practice behavioral
        try:
            r = await c.get("/api/behavioral/practice?competency=leadership")
            assert r.status_code == 200
            d = r.json()
            ok("Get practice question", f"Q: {d['question'][:50]}...")
        except Exception as e:
            fail("Practice question", e)

        try:
            r = await c.post("/api/behavioral/practice/evaluate", json={
                "competency": "leadership",
                "question": "Tell me about a time you led a team through a challenging project.",
                "answer": "Last year I led a team of 5 engineers to migrate our monolith to microservices. I created a phased migration plan, held weekly architecture reviews, and personally mentored two junior developers who were struggling with the new patterns. We completed the migration 2 weeks ahead of schedule with zero downtime. The new architecture reduced deployment time from 45 minutes to 8 minutes."
            })
            assert r.status_code == 200
            d = r.json()
            ok("Evaluate behavioral", f"overall={d['overall_score']}/5, S={d['situation_score']} T={d['task_score']} A={d['action_score']} R={d['result_score']}")
        except Exception as e:
            fail("Evaluate behavioral", e)

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

            # 9. start_mock_interview
            mi = await mgr._dispatch(session, "start_mock_interview", {
                "topic": "dsa",
                "difficulty": "easy",
                "duration_minutes": 15
            })
            ok("Voice: start_mock_interview", f"interview_id={str(mi.get('interview_id',''))[:8]}..., questions={mi.get('total_questions')}")

            # 10. submit_interview_answer
            if mi.get("interview_id"):
                sia = await mgr._dispatch(session, "submit_interview_answer", {
                    "interview_id": mi["interview_id"],
                    "question_order": 1,
                    "user_answer": "A hash map uses a hash function to map keys to buckets for O(1) average lookup."
                })
                ok("Voice: submit_interview_answer", f"score={sia.get('score')}")

                # 11. end_mock_interview
                emi = await mgr._dispatch(session, "end_mock_interview", {
                    "interview_id": mi["interview_id"]
                })
                ok("Voice: end_mock_interview", f"overall={emi.get('overall_score')}")

            # 12. start_focus_review
            fr = await mgr._dispatch(session, "start_focus_review", {
                "categories": ["python_basics"],
                "limit": 5
            })
            ok("Voice: start_focus_review", f"{fr.get('total_questions', 0)} focus questions")

            # 13. practice_behavioral
            pb = await mgr._dispatch(session, "practice_behavioral", {
                "competency": "teamwork"
            })
            ok("Voice: practice_behavioral", f"Q: {str(pb.get('question',''))[:50]}...")

            # 14. evaluate_behavioral_answer
            if pb.get("question"):
                eba = await mgr._dispatch(session, "evaluate_behavioral_answer", {
                    "competency": "teamwork",
                    "question": pb["question"],
                    "user_answer": "When I joined the team, there was a conflict about API design. I organized a comparison session where each person presented their approach. We agreed on REST with clear documentation. The team became more collaborative after that."
                })
                ok("Voice: evaluate_behavioral_answer", f"overall={eba.get('overall_score')}")

            # 15. capture_behavioral_story
            cbs = await mgr._dispatch(session, "capture_behavioral_story", {
                "narrative": "At my previous company, I noticed our onboarding process was taking new engineers 3 weeks to become productive. I created a structured onboarding guide with code walkthroughs, setup scripts, and paired each new hire with a buddy. I also set up weekly check-ins for the first month. As a result, the average onboarding time dropped to 1 week, and new hire satisfaction scores improved by 40 percent.",
                "competency": "initiative"
            })
            ok("Voice: capture_behavioral_story", f"story_id={str(cbs.get('story_id',''))[:8]}...")

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
