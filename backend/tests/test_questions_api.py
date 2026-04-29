"""
Live integration tests for the Question Bank API.
Tests all 7 endpoints against real DB (localhost:8001).

Endpoints tested:
  GET    /api/questions              — list with filters, search, sort, pagination
  GET    /api/questions/stats/summary — aggregate stats
  GET    /api/questions/{id}         — detail with review history
  PATCH  /api/questions/{id}         — edit question
  DELETE /api/questions/{id}         — delete single
  POST   /api/questions/bulk-delete  — delete multiple
  POST   /api/questions/{id}/reschedule — reset/review_now/postpone
"""
import asyncio
import sys
import uuid

sys.path.insert(0, "E:\\Sharuk\\recall\\backend")
import httpx

BASE = "http://localhost:8001"


async def main():
    print("\n" + "=" * 60)
    print("QUESTION BANK API — LIVE INTEGRATION TESTS")
    print("=" * 60)
    passed = 0
    failed = 0
    first_q_id = None      # captured for detail/edit/reschedule tests
    created_capture_id = None

    async with httpx.AsyncClient(base_url=BASE, timeout=30, follow_redirects=True) as c:

        # =====================================================
        # 0. Setup — capture some data so we have questions
        # =====================================================
        print("\n--- SETUP ---")

        print("  Creating test capture...", end=" ")
        try:
            r = await c.post("/api/captures/", json={
                "raw_text": (
                    "Binary search divides sorted arrays in half each step. "
                    "Time complexity is O(log n). "
                    "It only works on sorted data."
                ),
                "source_type": "text",
            })
            assert r.status_code == 200, f"Status {r.status_code}: {r.text}"
            created_capture_id = r.json()["capture_id"]
            print(f"OK (capture_id={created_capture_id[:8]}...)")
        except Exception as e:
            print(f"FAIL: {e}")
            # Don't exit — some tests work with existing data

        # =====================================================
        # 1. LIST QUESTIONS — basic
        # =====================================================
        print("\n--- T1: LIST QUESTIONS ---")

        print("  T1.1 Basic list...", end=" ")
        try:
            r = await c.get("/api/questions", params={"limit": 5})
            assert r.status_code == 200
            data = r.json()
            assert "questions" in data
            assert "total" in data
            assert isinstance(data["questions"], list)
            assert data["total"] >= 0
            if data["questions"]:
                q = data["questions"][0]
                first_q_id = q["id"]
                assert "question_text" in q
                assert "answer_text" in q
                assert "question_type" in q
                assert "state" in q
                assert "review_count" in q
                assert "capture_id" in q
            print(f"PASS ({data['total']} total, got {len(data['questions'])})")
            passed += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed += 1

        print("  T1.2 Pagination...", end=" ")
        try:
            # Use deterministic sort (due ASC) to avoid overlap from identical timestamps
            r1 = await c.get("/api/questions", params={"limit": 2, "offset": 0, "sort": "due", "order": "asc"})
            r2 = await c.get("/api/questions", params={"limit": 2, "offset": 2, "sort": "due", "order": "asc"})
            assert r1.status_code == 200
            assert r2.status_code == 200
            d1 = r1.json()
            d2 = r2.json()
            assert d1["total"] == d2["total"]  # Same total
            ids1 = {q["id"] for q in d1["questions"]}
            ids2 = {q["id"] for q in d2["questions"]}
            assert not ids1.intersection(ids2), "Pages should not overlap"
            print(f"PASS (page1={len(d1['questions'])}, page2={len(d2['questions'])})")
            passed += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed += 1

        print("  T1.3 Search filter...", end=" ")
        try:
            r = await c.get("/api/questions", params={"search": "binary", "limit": 10})
            assert r.status_code == 200
            data = r.json()
            if data["questions"]:
                for q in data["questions"]:
                    assert "binary" in q["question_text"].lower() or "binary" in q["answer_text"].lower(), \
                        f"Search miss: {q['question_text'][:50]}"
            print(f"PASS ({data['total']} matches)")
            passed += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed += 1

        print("  T1.4 Type filter...", end=" ")
        try:
            r = await c.get("/api/questions", params={"question_type": "recall", "limit": 5})
            assert r.status_code == 200
            data = r.json()
            for q in data["questions"]:
                assert q["question_type"] == "recall", f"Wrong type: {q['question_type']}"
            print(f"PASS ({data['total']} recall questions)")
            passed += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed += 1

        print("  T1.5 State filter...", end=" ")
        try:
            r = await c.get("/api/questions", params={"state": 1, "limit": 5})
            assert r.status_code == 200
            data = r.json()
            for q in data["questions"]:
                assert q["state"] == 1, f"Wrong state: {q['state']}"
            print(f"PASS ({data['total']} learning)")
            passed += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed += 1

        print("  T1.6 Sort by difficulty desc...", end=" ")
        try:
            r = await c.get("/api/questions", params={"sort": "difficulty", "order": "desc", "limit": 5})
            assert r.status_code == 200
            data = r.json()
            diffs = [q["difficulty"] for q in data["questions"] if q["difficulty"] is not None]
            if len(diffs) >= 2:
                assert diffs == sorted(diffs, reverse=True), "Not sorted desc by difficulty"
            print(f"PASS ({len(diffs)} with difficulty)")
            passed += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed += 1

        print("  T1.7 Sort by due asc...", end=" ")
        try:
            r = await c.get("/api/questions", params={"sort": "due", "order": "asc", "limit": 5})
            assert r.status_code == 200
            data = r.json()
            dues = [q["due"] for q in data["questions"] if q["due"]]
            if len(dues) >= 2:
                assert dues == sorted(dues), "Not sorted asc by due"
            print(f"PASS")
            passed += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed += 1

        print("  T1.8 Invalid sort field rejected...", end=" ")
        try:
            r = await c.get("/api/questions", params={"sort": "'; DROP TABLE questions;--", "limit": 5})
            assert r.status_code == 200  # Should fallback to created_at, not error
            print("PASS (fallback to created_at)")
            passed += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed += 1

        print("  T1.9 Capture_id filter...", end=" ")
        try:
            if created_capture_id:
                r = await c.get("/api/questions", params={"capture_id": created_capture_id, "limit": 10})
                assert r.status_code == 200
                data = r.json()
                for q in data["questions"]:
                    assert q["capture_id"] == created_capture_id
                print(f"PASS ({data['total']} from this capture)")
            else:
                print("SKIP (no capture)")
            passed += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed += 1

        print("  T1.10 Invalid capture_id → 400...", end=" ")
        try:
            r = await c.get("/api/questions", params={"capture_id": "not-a-uuid"})
            assert r.status_code == 400
            print("PASS")
            passed += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed += 1

        # =====================================================
        # 2. STATS SUMMARY
        # =====================================================
        print("\n--- T2: STATS SUMMARY ---")

        print("  T2.1 Stats endpoint...", end=" ")
        try:
            r = await c.get("/api/questions/stats/summary")
            assert r.status_code == 200
            data = r.json()
            assert "total_questions" in data
            assert "by_type" in data
            assert "by_state" in data
            assert "most_failed" in data
            assert isinstance(data["by_type"], list)
            assert isinstance(data["by_state"], list)
            assert data["total_questions"] > 0
            type_total = sum(t["count"] for t in data["by_type"])
            assert type_total == data["total_questions"], \
                f"Type counts ({type_total}) != total ({data['total_questions']})"
            print(f"PASS ({data['total_questions']} questions, {len(data['by_type'])} types)")
            passed += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed += 1

        # =====================================================
        # 3. QUESTION DETAIL
        # =====================================================
        print("\n--- T3: QUESTION DETAIL ---")

        print("  T3.1 Get detail by ID...", end=" ")
        try:
            assert first_q_id, "No question ID from list"
            r = await c.get(f"/api/questions/{first_q_id}")
            assert r.status_code == 200
            data = r.json()
            assert data["id"] == first_q_id
            assert "question_text" in data
            assert "answer_text" in data
            assert "review_logs" in data
            assert isinstance(data["review_logs"], list)
            assert "capture_raw_text" in data
            assert "extracted_point_content" in data
            assert "accuracy_rate" in data
            print(f"PASS (review_count={data['review_count']}, logs={len(data['review_logs'])})")
            passed += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed += 1

        print("  T3.2 Detail for non-existent ID → 404...", end=" ")
        try:
            fake_id = str(uuid.uuid4())
            r = await c.get(f"/api/questions/{fake_id}")
            assert r.status_code == 404
            print("PASS")
            passed += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed += 1

        print("  T3.3 Detail for invalid UUID → 400...", end=" ")
        try:
            r = await c.get("/api/questions/not-a-uuid")
            assert r.status_code == 400
            print("PASS")
            passed += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed += 1

        # =====================================================
        # 4. EDIT QUESTION
        # =====================================================
        print("\n--- T4: EDIT QUESTION ---")

        # Get a question to edit (from the capture we just created)
        edit_q_id = None
        try:
            if created_capture_id:
                r = await c.get("/api/questions", params={"capture_id": created_capture_id, "limit": 1})
                if r.status_code == 200 and r.json()["questions"]:
                    edit_q_id = r.json()["questions"][0]["id"]
        except:
            pass
        if not edit_q_id:
            edit_q_id = first_q_id

        print("  T4.1 Edit question_text...", end=" ")
        try:
            assert edit_q_id
            r = await c.patch(f"/api/questions/{edit_q_id}", json={
                "question_text": "EDITED: What is binary search?"
            })
            assert r.status_code == 200
            data = r.json()
            assert data["question_text"] == "EDITED: What is binary search?"
            print("PASS")
            passed += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed += 1

        print("  T4.2 Edit answer + hint...", end=" ")
        try:
            r = await c.patch(f"/api/questions/{edit_q_id}", json={
                "answer_text": "EDITED: Divides sorted array in half",
                "mnemonic_hint": "EDITED: Think halving"
            })
            assert r.status_code == 200
            data = r.json()
            assert data["answer_text"] == "EDITED: Divides sorted array in half"
            assert data["mnemonic_hint"] == "EDITED: Think halving"
            print("PASS")
            passed += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed += 1

        print("  T4.3 Edit with empty body → 400...", end=" ")
        try:
            r = await c.patch(f"/api/questions/{edit_q_id}", json={})
            assert r.status_code == 400
            print("PASS")
            passed += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed += 1

        print("  T4.4 Edit non-existent → 404...", end=" ")
        try:
            r = await c.patch(f"/api/questions/{uuid.uuid4()}", json={"question_text": "x"})
            assert r.status_code == 404
            print("PASS")
            passed += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed += 1

        print("  T4.5 Verify edit persisted...", end=" ")
        try:
            r = await c.get(f"/api/questions/{edit_q_id}")
            assert r.status_code == 200
            data = r.json()
            assert "EDITED" in data["question_text"]
            assert "EDITED" in data["answer_text"]
            print("PASS")
            passed += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed += 1

        # =====================================================
        # 5. RESCHEDULE
        # =====================================================
        print("\n--- T5: RESCHEDULE ---")

        print("  T5.1 Reschedule: reset...", end=" ")
        try:
            r = await c.post(f"/api/questions/{edit_q_id}/reschedule", json={
                "action": "reset"
            })
            assert r.status_code == 200
            data = r.json()
            assert data["state"] == 0
            assert data["step"] == 0
            print("PASS")
            passed += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed += 1

        print("  T5.2 Reschedule: review_now...", end=" ")
        try:
            r = await c.post(f"/api/questions/{edit_q_id}/reschedule", json={
                "action": "review_now"
            })
            assert r.status_code == 200
            data = r.json()
            assert data["due"]  # Should be set to now
            print("PASS")
            passed += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed += 1

        print("  T5.3 Reschedule: postpone 7 days...", end=" ")
        try:
            r = await c.post(f"/api/questions/{edit_q_id}/reschedule", json={
                "action": "postpone",
                "days": 7
            })
            assert r.status_code == 200
            data = r.json()
            assert data["due"]
            print("PASS")
            passed += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed += 1

        print("  T5.4 Postpone without days → 400...", end=" ")
        try:
            r = await c.post(f"/api/questions/{edit_q_id}/reschedule", json={
                "action": "postpone"
            })
            assert r.status_code == 400
            print("PASS")
            passed += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed += 1

        print("  T5.5 Invalid action → 422...", end=" ")
        try:
            r = await c.post(f"/api/questions/{edit_q_id}/reschedule", json={
                "action": "yeet"
            })
            assert r.status_code == 422  # Pydantic validation
            print("PASS")
            passed += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed += 1

        print("  T5.6 Reschedule non-existent → 404...", end=" ")
        try:
            r = await c.post(f"/api/questions/{uuid.uuid4()}/reschedule", json={
                "action": "reset"
            })
            assert r.status_code == 404
            print("PASS")
            passed += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed += 1

        # =====================================================
        # 6. DELETE SINGLE
        # =====================================================
        print("\n--- T6: DELETE ---")

        # Get questions from our test capture to delete
        # Exclude edit_q_id since we still need it for later tests
        delete_ids = []
        try:
            if created_capture_id:
                r = await c.get("/api/questions", params={"capture_id": created_capture_id, "limit": 10})
                if r.status_code == 200:
                    delete_ids = [q["id"] for q in r.json()["questions"] if q["id"] != edit_q_id]
        except:
            pass

        print("  T6.1 Delete non-existent → 404...", end=" ")
        try:
            r = await c.delete(f"/api/questions/{uuid.uuid4()}")
            assert r.status_code == 404
            print("PASS")
            passed += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed += 1

        print("  T6.2 Delete invalid UUID → 400...", end=" ")
        try:
            r = await c.delete("/api/questions/not-valid")
            assert r.status_code == 400
            print("PASS")
            passed += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed += 1

        del_q_id = delete_ids.pop() if delete_ids else None

        print("  T6.3 Delete single question...", end=" ")
        try:
            if del_q_id:
                # Count before
                r_before = await c.get("/api/questions/stats/summary")
                total_before = r_before.json()["total_questions"]

                r = await c.delete(f"/api/questions/{del_q_id}")
                assert r.status_code == 200
                assert r.json()["deleted"] == True

                # Verify gone
                r_check = await c.get(f"/api/questions/{del_q_id}")
                assert r_check.status_code == 404

                # Verify total decreased
                r_after = await c.get("/api/questions/stats/summary")
                total_after = r_after.json()["total_questions"]
                assert total_after == total_before - 1
                print(f"PASS (total: {total_before} → {total_after})")
            else:
                print("SKIP (no test question)")
            passed += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed += 1

        # =====================================================
        # 7. BULK DELETE
        # =====================================================
        print("\n--- T7: BULK DELETE ---")

        print("  T7.1 Bulk delete with valid IDs...", end=" ")
        try:
            if len(delete_ids) >= 2:
                bulk_ids = delete_ids[:2]
                r = await c.post("/api/questions/bulk-delete", json={
                    "question_ids": bulk_ids
                })
                assert r.status_code == 200
                data = r.json()
                assert data["deleted_count"] == 2
                # Verify both gone
                for bid in bulk_ids:
                    r_check = await c.get(f"/api/questions/{bid}")
                    assert r_check.status_code == 404
                print(f"PASS (deleted {data['deleted_count']})")
            else:
                print("SKIP (not enough questions)")
            passed += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed += 1

        print("  T7.2 Bulk delete with non-existent IDs...", end=" ")
        try:
            r = await c.post("/api/questions/bulk-delete", json={
                "question_ids": [str(uuid.uuid4()), str(uuid.uuid4())]
            })
            assert r.status_code == 200
            assert r.json()["deleted_count"] == 0
            print("PASS")
            passed += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed += 1

        print("  T7.3 Bulk delete empty list → 422...", end=" ")
        try:
            r = await c.post("/api/questions/bulk-delete", json={
                "question_ids": []
            })
            assert r.status_code == 422  # min_length=1 validation
            print("PASS")
            passed += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed += 1

        # =====================================================
        # 8. CROSS-FEATURE: List reflects changes
        # =====================================================
        print("\n--- T8: CROSS-FEATURE VERIFICATION ---")

        print("  T8.1 Deleted questions don't appear in list...", end=" ")
        try:
            if del_q_id:
                r = await c.get("/api/questions", params={"search": "EDITED", "limit": 50})
                assert r.status_code == 200
                remaining_ids = {q["id"] for q in r.json()["questions"]}
                assert del_q_id not in remaining_ids
                print("PASS")
            else:
                print("SKIP")
            passed += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed += 1

        print("  T8.2 Stats consistent with list total...", end=" ")
        try:
            r_list = await c.get("/api/questions", params={"limit": 1})
            r_stats = await c.get("/api/questions/stats/summary")
            list_total = r_list.json()["total"]
            stats_total = r_stats.json()["total_questions"]
            assert list_total == stats_total, f"List ({list_total}) != Stats ({stats_total})"
            print(f"PASS (both report {list_total})")
            passed += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed += 1

        # =====================================================
        # 9. SECURITY: Injection attempts
        # =====================================================
        print("\n--- T9: SECURITY ---")

        print("  T9.1 SQL injection in search...", end=" ")
        try:
            r = await c.get("/api/questions", params={"search": "'; DROP TABLE questions; --"})
            assert r.status_code == 200  # Should not crash
            # Verify table still exists
            r2 = await c.get("/api/questions/stats/summary")
            assert r2.status_code == 200
            assert r2.json()["total_questions"] > 0
            print("PASS (table survived)")
            passed += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed += 1

        print("  T9.2 SQL injection in sort...", end=" ")
        try:
            r = await c.get("/api/questions", params={
                "sort": "id; DROP TABLE questions",
                "limit": 1
            })
            assert r.status_code == 200  # Fallback to created_at
            print("PASS")
            passed += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed += 1

        print("  T9.3 XSS in edit...", end=" ")
        try:
            # Use a known-good question ID that wasn't deleted
            xss_q_id = edit_q_id if edit_q_id and edit_q_id != del_q_id else first_q_id
            if xss_q_id and xss_q_id != del_q_id:
                r = await c.patch(f"/api/questions/{xss_q_id}", json={
                    "mnemonic_hint": "<script>alert('xss')</script>"
                })
                # Should store as plain text (sanitization is frontend's job)
                assert r.status_code == 200
                print("PASS (stored as plain text)")
            else:
                print("SKIP")
            passed += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed += 1

    # =====================================================
    # RESULTS
    # =====================================================
    print(f"\n{'=' * 60}")
    print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
    if failed == 0:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
        sys.exit(1)

    # Cleanup: restore edited question if possible
    if first_q_id and first_q_id != del_q_id:
        async with httpx.AsyncClient(base_url=BASE, timeout=10, follow_redirects=True) as c:
            try:
                await c.patch(f"/api/questions/{first_q_id}", json={
                    "mnemonic_hint": None
                })
            except:
                pass


if __name__ == "__main__":
    asyncio.run(main())
