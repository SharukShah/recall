# UI Testing & Fix Report

**Date:** April 19, 2026  
**Frontend:** http://localhost:3000  
**Backend:** http://localhost:8001

---

## ✅ Fixes Applied

### Fix #1: FeedbackCard Score Mismatch
**Issue:** Backend returns `"wrong"` but frontend expected `"incorrect"`  
**Files Fixed:**
- `frontend/components/review/FeedbackCard.tsx` - Changed key from `incorrect` to `wrong`
- `frontend/types/api.ts` - Updated type definition to match backend

**Status:** ✅ FIXED

### Fix #2: Better Error Handling in API Client
**Issue:** "Failed to execute 'json' on 'Response'" when backend returns HTML error pages  
**File Fixed:** `frontend/lib/api.ts`  
**Changes:**
- Added content-type checking before parsing JSON
- Better error messages when backend returns non-JSON
- Handles HTML error pages gracefully

**Status:** ✅ FIXED

---

## 🧪 Manual UI Testing Required

The fixes above should resolve the crashes, but you need to test each page manually. Here's a systematic testing checklist:

### Test 1: Dashboard (/) ✅
**URL:** http://localhost:3000

**Expected:**
- Shows capture count (47)
- Shows question count (127)
- Shows due reviews
- Shows current streak

**Test Steps:**
1. Open http://localhost:3000
2. Check if all stats load
3. Check if cards render without errors

---

### Test 2: Capture Page (/capture) ⚠️
**URL:** http://localhost:3000/capture

**Test Steps:**
1. Paste sample text:
   ```
   The Feynman Technique involves explaining concepts in simple terms.
   This reveals gaps in your understanding.
   ```
2. Click "Capture Knowledge"
3. Wait for processing (~3-5 seconds)

**Expected:**
- Loading state shows
- Facts extracted (3-5 facts)
- Questions generated (5-7 questions)
- Status shows "complete"

**Common Issues:**
- If it returns HTML → Backend endpoint error (check terminal)
- If it times out → OpenAI API issue (check .env for OPENAI_API_KEY)

---

### Test 3: Review Page (/review) ⚠️
**URL:** http://localhost:3000/review

**Test Steps:**
1. Page should load questions
2. Type an answer
3. Click "Submit Answer"
4. Check if feedback shows (should not crash with "config undefined" error anymore)
5. Rate the question (1-4)

**Expected:**
- Questions load
- Can type answer
- Feedback shows with green/yellow/red badge
- Rating buttons work
- Moves to next question

**Fixed Issue:**
- ✅ "Cannot read properties of undefined (reading 'className')" - now fixed

---

### Test 4: Knowledge Graph (/graph) ⚠️
**URL:** http://localhost:3000/graph

**Test Steps:**
1. Open page
2. Graph should render with nodes
3. Try zooming with mouse wheel
4. Try clicking on a node
5. Adjust similarity slider

**Expected:**
- Interactive graph with 80+ nodes
- Nodes are draggable
- Clicking a node shows details panel
- Slider adjusts visible connections

**Common Issues:**
- If crashes → Check browser console for WebGL errors
- If shows no data → Check database has embeddings

---

### Test 5: Analytics (/analytics) ⚠️
**URL:** http://localhost:3000/analytics

**Test Steps:**
1. Open page
2. Check all charts load

**Expected:**
- Retention curve chart
- Mastery pie chart
- Weak areas table
- Velocity cards
- Streak stats
- Activity heatmap

**Common Issues:**
- If crashes → Check browser console
- If empty → Normal if no review history

---

### Test 6: Method of Loci (/loci/create) ⚠️
**URL:** http://localhost:3000/loci/create

**Test Steps:**
1. Enter title: "Test Palace"
2. Add 5 items (e.g., Apple, Banana, Cherry, Date, Elderberry)
3. Select palace theme (museum/library/garden)
4. Click "Generate Walkthrough"
5. Wait 5-10 seconds

**Expected:**
- Loading state shows
- GPT-4 generates vivid narrative
- Shows full walkthrough
- "Test Recall" button appears

**Common Issues:**
- If times out → OpenAI API issue
- If 500 error → Check backend terminal for database errors

---

### Test 7: Settings (/settings) ⚠️
**URL:** http://localhost:3000/settings

**Test Steps:**
1. Toggle notifications ON
2. Set reminder time (e.g., 09:00)
3. Set timezone
4. Click "Save Settings"

**Expected:**
- Settings save successfully
- Shows confirmation

**Common Issues:**
- If crashes → Check if notification tables exist in database

---

## 🐛 Known Issues to Check

### Issue: Backend Returns 500 Errors
**Symptom:** Frontend shows "Failed to execute 'json'" or crashes  
**Cause:** Backend endpoint throwing exception  
**Fix:** Check backend terminal for Python tracebacks

### Issue: Database Tables Missing
**Symptom:** Endpoints return "relation does not exist"  
**Fix:** Apply migration: `psql -U postgres -d recall_mvp -f backend/migration_phase5.sql`

### Issue: CORS Errors
**Symptom:** Browser blocks requests from localhost:3000 to localhost:8001  
**Fix:** Already configured in backend/main.py (should work)

---

## 🔧 Debugging Tips

### Check Browser Console (F12)
```
1. Open DevTools (F12)
2. Go to Console tab
3. Look for red errors
4. Copy the full error message
```

### Check Network Tab
```
1. Open DevTools → Network tab
2. Reload the page
3. Look for red (failed) requests
4. Click on them to see response
5. If response is HTML → backend 500 error
6. If response is JSON → read error message
```

### Check Backend Terminal
Look for:
- `ERROR:    Exception in ASGI application` → Backend crash
- `INFO:     127.0.0.1 - "GET /api/... HTTP/1.1" 500` → Endpoint error
- `asyncpg.exceptions...` → Database error

---

## 📋 Full Test Checklist

Test each page and check the box:

- [ ] Dashboard (/) loads without errors
- [ ] Capture (/capture) - can submit text and see results
- [ ] Review (/review) - can answer questions and rate
- [ ] Review - feedback card shows correct/partial/wrong without crashing
- [ ] Search (/search) - can search and see results  
- [ ] Teach (/teach) - can start teaching session
- [ ] Reflect (/reflect) - can submit reflection
- [ ] History (/history) - shows capture list
- [ ] Voice (/voice) - page loads (functionality requires Deepgram)
- [ ] Knowledge Graph (/graph) - renders interactive graph
- [ ] Analytics (/analytics) - all charts load
- [ ] Method of Loci (/loci) - can list sessions
- [ ] Loci Create (/loci/create) - can generate walkthrough
- [ ] Settings (/settings) - can update settings

---

## 🚀 Next Steps

1. **Open http://localhost:3000 in your browser**
2. **Test each page systematically** using the checklist above
3. **Note which pages crash or show errors**
4. **Check browser console (F12) for error messages**
5. **Report back which specific features are broken**

I've fixed the two main issues identified:
- ✅ FeedbackCard crash (score mismatch)
- ✅ Better error handling (JSON parsing)

Now you need to **manually test** and tell me which pages still have issues.
