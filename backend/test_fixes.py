"""Re-test script for security fixes verification."""
import httpx
import time

BASE = "http://localhost:8000"
results = []

def test(name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    results.append((name, passed, detail))
    print(f"[{status}] {name}: {detail}")

# ============================================================
# FIX 1: why_it_matters max_length=1000
# ============================================================
r = httpx.post(f"{BASE}/api/captures/", json={"raw_text": "test", "why_it_matters": "A" * 1001}, timeout=30)
test("Fix 1: why_it_matters 1001 chars rejected", r.status_code == 422,
     f"Status={r.status_code} (expected 422)")

r = httpx.post(f"{BASE}/api/captures/", json={"raw_text": "test", "why_it_matters": "A" * 1000}, timeout=30)
test("Fix 1: why_it_matters 1000 chars accepted", r.status_code == 200,
     f"Status={r.status_code} (expected 200)")

# ============================================================
# FIX 3: question_id UUID validation
# ============================================================
r = httpx.post(f"{BASE}/api/reviews/evaluate", json={"question_id": "not-a-uuid", "user_answer": "test"}, timeout=10)
test("Fix 3: Invalid UUID evaluate rejected with 422", r.status_code == 422,
     f"Status={r.status_code}, Body={r.text[:100]}")

r = httpx.post(f"{BASE}/api/reviews/rate", json={"question_id": "not-a-uuid", "rating": 3}, timeout=10)
test("Fix 3: Invalid UUID rate rejected with 422", r.status_code == 422,
     f"Status={r.status_code}, Body={r.text[:100]}")

# ============================================================
# FIX 5: Rate limiting (check headers on captures POST)
# ============================================================
# Send a request and check for rate limit headers
r = httpx.post(f"{BASE}/api/captures/", json={"raw_text": "rate limit test"}, timeout=30)
has_ratelimit = any("ratelimit" in k.lower() or "x-ratelimit" in k.lower() or "retry-after" in k.lower()
                     for k in r.headers)
rl_headers = {k: v for k, v in r.headers.items() if "rate" in k.lower() or "limit" in k.lower() or "retry" in k.lower()}
test("Fix 5: Rate limit headers present on captures POST", has_ratelimit,
     f"Headers={rl_headers}")

# Try to trigger rate limit (send rapid requests to evaluate, which has 30/min limit)
# But we'll use a cheaper endpoint check
r = httpx.post(f"{BASE}/api/reviews/evaluate", json={"question_id": "00000000-0000-0000-0000-000000000001", "user_answer": "x"}, timeout=10)
has_ratelimit2 = any("ratelimit" in k.lower() for k in r.headers)
rl_headers2 = {k: v for k, v in r.headers.items() if "rate" in k.lower() or "limit" in k.lower()}
test("Fix 5: Rate limit headers on evaluate POST", has_ratelimit2,
     f"Headers={rl_headers2}")

# ============================================================
# FIX 7: Invalid capture_id returns 422
# ============================================================
r = httpx.get(f"{BASE}/api/captures/not-a-uuid", timeout=10)
test("Fix 7: Invalid capture_id returns 422", r.status_code == 422,
     f"Status={r.status_code}, Body={r.text[:100]}")

r = httpx.get(f"{BASE}/api/captures/00000000-0000-0000-0000-000000000099", timeout=10)
test("Fix 7: Valid UUID not found returns 404", r.status_code == 404,
     f"Status={r.status_code}")

# ============================================================
# FIX 8: RateRequest fields max_length
# ============================================================
r = httpx.post(f"{BASE}/api/reviews/rate", json={
    "question_id": "00000000-0000-0000-0000-000000000001",
    "rating": 3,
    "user_answer": "A" * 10001
}, timeout=10)
test("Fix 8: RateRequest user_answer 10001 chars rejected", r.status_code == 422,
     f"Status={r.status_code}, Body={r.text[:100]}")

r = httpx.post(f"{BASE}/api/reviews/rate", json={
    "question_id": "00000000-0000-0000-0000-000000000001",
    "rating": 3,
    "ai_feedback": "A" * 5001
}, timeout=10)
test("Fix 8: RateRequest ai_feedback 5001 chars rejected", r.status_code == 422,
     f"Status={r.status_code}, Body={r.text[:100]}")

# ============================================================
# HAPPY PATH: Dashboard still works
# ============================================================
r = httpx.get(f"{BASE}/api/stats/dashboard", timeout=10)
test("Happy path: Dashboard works", r.status_code == 200,
     f"Status={r.status_code}")

# ============================================================
# HAPPY PATH: List captures works
# ============================================================
r = httpx.get(f"{BASE}/api/captures/", timeout=10)
test("Happy path: List captures works", r.status_code == 200,
     f"Status={r.status_code}")

# ============================================================
# HAPPY PATH: Due questions works
# ============================================================
r = httpx.get(f"{BASE}/api/reviews/due", timeout=10)
test("Happy path: Due questions works", r.status_code == 200,
     f"Status={r.status_code}")

# ============================================================
# SUMMARY
# ============================================================
print("\n" + "=" * 60)
passed = sum(1 for _, p, _ in results if p)
total = len(results)
print(f"RESULTS: {passed}/{total} tests passed")
print("=" * 60)
for name, p, detail in results:
    if not p:
        print(f"  FAILED: {name}")
        print(f"          {detail}")
