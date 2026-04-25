# ReCall MVP - Quick Start Guide

**Version:** Phase 5 Complete (All Features)  
**Date:** April 19, 2026

---

## 🚀 Starting the Application

### 1. Start PostgreSQL 16
```powershell
# Ensure PostgreSQL 16 is running (not 18)
Get-Service postgresql-x64-16,postgresql-x64-18

# If needed, stop PG18 and start PG16
Stop-Service postgresql-x64-18
Start-Service postgresql-x64-16
```

### 2. Start Backend Server
```powershell
# Open Terminal 1
cd E:\Sharuk\recall\backend
.\venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8001
```

**Expected Output:**
```
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Starting ReCall API...
INFO:     Database pool created
INFO:     OpenAI client initialized
INFO:     FSRS scheduler initialized
INFO:     Supervised notification task started
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8001
```

### 3. Start Frontend Server
```powershell
# Open Terminal 2
cd E:\Sharuk\recall\frontend
npm run dev -- --port 3000
```

**Expected Output:**
```
▲ Next.js 14.2.35
- Local:        http://localhost:3000
- Ready in 2.1s
```

### 4. Open in Browser
Navigate to: **http://localhost:3000**

---

## 📋 Testing Core Features (Phases 1-4)

### Phase 1: Knowledge Capture & Spaced Repetition

#### Test 1: Capture Text Knowledge
1. Go to **http://localhost:3000/capture**
2. Paste this text:
   ```
   The Feynman Technique is a learning method where you explain concepts 
   in simple terms as if teaching someone else. This reveals gaps in your 
   understanding. The four steps are: choose a concept, teach it to a child, 
   identify gaps, and review and simplify.
   ```
3. Click **"Capture Knowledge"**
4. Wait for processing (~3-5 seconds)
5. **Expected Result:**
   - Shows extracted facts (4-6 facts)
   - Shows generated questions (5-7 questions)
   - Status: "Complete"

#### Test 2: Review Questions (Spaced Repetition)
1. Go to **http://localhost:3000/review**
2. You should see questions generated from your capture
3. Type an answer (try both correct and incorrect)
4. Click **"Submit Answer"**
5. **Expected Result:**
   - AI evaluates your answer
   - Provides feedback
   - Shows next review date (FSRS scheduling)
   - Rate the difficulty (Again/Hard/Good/Easy)

#### Test 3: View Dashboard
1. Go to **http://localhost:3000** (Dashboard)
2. **Expected Result:**
   - Shows total captures
   - Shows total questions
   - Shows due count
   - Shows current streak
   - Shows retention rate

### Phase 2: Knowledge Search

#### Test 4: Search Your Knowledge
1. Go to **http://localhost:3000/search**
2. Type: "Feynman"
3. Click **"Search"**
4. **Expected Result:**
   - Shows relevant facts from your captures
   - Uses vector similarity (pgvector)

### Phase 3: Smart Features

#### Test 5: Teach Me Mode
1. Go to **http://localhost:3000/teach**
2. Enter topic: "How neural networks learn"
3. Click **"Start Learning"**
4. **Expected Result:**
   - GPT-4 generates a teaching plan
   - Breaks into 3-5 chunks
   - Shows first chunk
   - Answer the comprehension question
   - Get instant feedback

#### Test 6: Evening Reflection
1. Go to **http://localhost:3000/reflect**
2. Write what you learned today (100+ words)
3. Click **"Submit Reflection"**
4. **Expected Result:**
   - Creates a capture from your reflection
   - Extracts key facts
   - Generates questions
   - Shows streak (if you reflect daily)

### Phase 4: Voice Agent

#### Test 7: Text-to-Speech
1. Go to **http://localhost:3000/voice**
2. Check if voice is enabled (requires Deepgram API key)
3. If enabled, start a voice capture session
4. **Expected Result:**
   - Speaks questions to you
   - Transcribes your spoken answers
   - Works like regular review but hands-free

---

## 🆕 Testing Phase 5 Features

### Feature 1: Knowledge Graph

#### Test 8: View Knowledge Graph
1. **Capture 3-5 different topics first** (so you have data to visualize)
2. Go to **http://localhost:3000/graph**
3. **Expected Result:**
   - Interactive graph visualization using Sigma.js
   - Nodes = your extracted facts
   - Edges = semantic connections (similarity + connection questions)
   - Color-coded by content type (fact, concept, list, etc.)

**Interactions:**
- **Zoom:** Mouse wheel
- **Pan:** Click and drag background
- **Select Node:** Click on a node to see details
- **Adjust Similarity:** Use the slider to show more/fewer connections

### Feature 2: Analytics Dashboard

#### Test 9: View Analytics
1. **Complete a few reviews first** (so you have history)
2. Go to **http://localhost:3000/analytics**
3. **Expected Result:**
   - **Retention Curve:** Shows how well you're retaining knowledge over time
   - **Mastery Breakdown:** Pie chart of Learning/Review/Relearning states
   - **Weak Areas:** List of captures with lowest retention
   - **Velocity Cards:** Reviews this week vs last week
   - **Streak Stats:** Current streak, longest streak, total study days
   - **Activity Heatmap:** 90-day calendar showing daily activity

### Feature 3: Method of Loci (Memory Palace)

#### Test 10: Create Memory Palace
1. Go to **http://localhost:3000/loci/create**
2. Fill in:
   - **Title:** "Countries in Europe"
   - **Items:** (Add 5-10 items)
     ```
     France
     Germany
     Italy
     Spain
     United Kingdom
     Poland
     Netherlands
     Sweden
     Greece
     Portugal
     ```
   - **Palace Theme:** "museum" (or "library", "garden")
3. Click **"Generate Walkthrough"**
4. Wait 5-10 seconds (GPT-4 generates narrative)
5. **Expected Result:**
   - GPT-4 creates a vivid memory palace walkthrough
   - Each item placed in a memorable location
   - Full narration of the journey
   - Auto-creates FSRS capture for review

#### Test 11: Recall from Memory Palace
1. After creating a session, click **"Test Recall"**
2. Try to remember items in order
3. Type what you remember in each position
4. Click **"Submit Recall"**
5. **Expected Result:**
   - Shows which items you got correct/incorrect
   - Calculates recall score
   - Provides feedback

### Feature 4: Push Notifications

#### Test 12: Configure Notifications
1. Go to **http://localhost:3000/settings**
2. Scroll to **"Review Reminders"** section
3. Toggle **"Enable Notifications"** ON
4. Set reminder time (e.g., "09:00")
5. Set your timezone (e.g., "America/New_York")
6. Click **"Subscribe to Notifications"** (if browser supports)
7. Click **"Save Settings"**
8. **Expected Result:**
   - Settings saved
   - Browser requests notification permission
   - Subscription stored in database

#### Test 13: Test Notification (Manual)
1. In settings, click **"Send Test Notification"**
2. **Expected Result:**
   - Browser notification appears
   - Shows "Test Notification" message
   - Click notification → opens review page

**Note:** VAPID keys must be configured in `.env` for push to work. If not configured, notifications section shows "Push notifications unavailable."

### Feature 5: Browser Extension

#### Test 14: Install Chrome Extension
1. Open Chrome browser
2. Go to `chrome://extensions/`
3. Enable **"Developer mode"** (top right)
4. Click **"Load unpacked"**
5. Select folder: `E:\Sharuk\recall\extension`
6. **Expected Result:**
   - Extension appears in toolbar
   - Icon shows (or placeholder if icons missing)

#### Test 15: Capture from Web Page
1. Navigate to any article (e.g., Wikipedia)
2. Highlight some text (100+ characters)
3. Right-click → **"Save to ReCall"**
4. **Expected Result:**
   - Toast notification: "Saved to ReCall!"
   - Text captured to backend
   - Facts extracted
   - Questions generated

#### Test 16: Extension Settings
1. Click extension icon → **"Options"**
2. Set backend URL: `http://localhost:8001`
3. Set auth token (if using API_KEY in .env)
4. Save settings
5. **Expected Result:**
   - Settings saved to Chrome storage
   - Extension can now communicate with your backend

### Feature 6: PWA (Progressive Web App)

#### Test 17: Install as PWA
1. While on **http://localhost:3000**, look for install prompt in address bar
2. Click **"Install ReCall"** (or Chrome menu → Install ReCall)
3. **Expected Result:**
   - App installs as standalone app
   - Opens in separate window (no browser chrome)
   - Works offline (basic pages cached)
   - App icon appears in Start menu / Desktop

#### Test 18: Offline Support
1. With PWA installed, disconnect from internet
2. Open the PWA
3. **Expected Result:**
   - Shows offline page if backend unreachable
   - Service worker serves cached pages
   - Syncs when connection restored

---

## 🧪 API Testing (Advanced)

### Using PowerShell

```powershell
$baseUrl = "http://localhost:8001"
$headers = @{"Content-Type"="application/json"}

# Test 1: Dashboard stats
Invoke-RestMethod -Uri "$baseUrl/api/stats/dashboard" -Method GET

# Test 2: Create capture
$body = @{
    raw_text = "Machine learning is a subset of AI that enables systems to learn from data."
    source_type = "text"
} | ConvertTo-Json
Invoke-RestMethod -Uri "$baseUrl/api/captures/" -Method POST -Body $body -Headers $headers

# Test 3: Get due reviews
Invoke-RestMethod -Uri "$baseUrl/api/reviews/due?limit=5" -Method GET

# Test 4: Knowledge graph
Invoke-RestMethod -Uri "$baseUrl/api/knowledge/graph/data?min_similarity=0.7&limit=100" -Method GET

# Test 5: Analytics
Invoke-RestMethod -Uri "$baseUrl/api/stats/analytics?weeks=12" -Method GET

# Test 6: Loci sessions
Invoke-RestMethod -Uri "$baseUrl/api/loci?limit=10" -Method GET

# Test 7: Notification settings
Invoke-RestMethod -Uri "$baseUrl/api/notifications/settings" -Method GET
```

### Using curl

```bash
# Get dashboard stats
curl http://localhost:8001/api/stats/dashboard

# Create capture
curl -X POST http://localhost:8001/api/captures/ \
  -H "Content-Type: application/json" \
  -d '{"raw_text":"The solar system has 8 planets.","source_type":"text"}'

# Get due reviews
curl http://localhost:8001/api/reviews/due?limit=5

# Knowledge graph
curl "http://localhost:8001/api/knowledge/graph/data?min_similarity=0.7&limit=100"
```

---

## 🔍 Verifying Database

### Check Tables
```powershell
cd E:\Sharuk\recall\backend
$env:PGPASSWORD = "postgres"
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -d recall_mvp -c "\dt"
```

**Expected Tables:**
- captures
- extracted_points
- questions
- review_logs
- teach_sessions
- connection_questions
- reflections
- voice_sessions
- notification_settings ✨ (Phase 5)
- notification_subscriptions ✨ (Phase 5)
- loci_sessions ✨ (Phase 5)

### Check Data
```powershell
# Count captures
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -d recall_mvp -c "SELECT COUNT(*) FROM captures;"

# Count questions
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -d recall_mvp -c "SELECT COUNT(*) FROM questions;"

# View recent captures
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -d recall_mvp -c "SELECT id, source_type, created_at FROM captures ORDER BY created_at DESC LIMIT 5;"
```

---

## 📊 Monitoring & Logs

### Backend Logs
Watch the backend terminal for:
- API requests: `INFO:     127.0.0.1:xxxxx - "GET /api/stats/dashboard HTTP/1.1" 200 OK`
- Errors: `ERROR:    Exception in ASGI application`
- Background tasks: `INFO:     Starting notification background task`

### Frontend Logs
Watch the frontend terminal for:
- Build status: `✓ Compiled successfully`
- Errors: Shows compilation errors if any
- API calls: Check browser DevTools → Network tab

### Browser Console
Open DevTools (F12) → Console:
- Check for JavaScript errors
- Service worker registration: `Service Worker registered`
- API call results

---

## 🎯 Sample Workflows

### Workflow 1: Daily Learning Routine

1. **Morning:** Go to `/teach`, learn something new (5-10 min)
2. **Midday:** Capture interesting articles via browser extension
3. **Evening:** Go to `/review`, complete due reviews (10-15 min)
4. **Night:** Go to `/reflect`, write daily reflection

### Workflow 2: Exam Preparation

1. Capture all study materials (notes, textbooks, articles)
2. Go to `/loci/create` to create memory palaces for key topics
3. Use `/graph` to visualize connections between concepts
4. Daily reviews to reinforce using FSRS scheduling
5. Check `/analytics` to identify weak areas

### Workflow 3: Research Project

1. Use browser extension to capture relevant papers/articles
2. Use `/search` to find related concepts
3. Use `/teach` to deeply understand complex topics
4. Use `/graph` to map out the knowledge domain
5. Track progress in `/analytics`

---

## ⚙️ Configuration

### Backend Environment Variables
Edit `backend/.env`:

```env
# Required
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/recall_mvp
OPENAI_API_KEY=sk-...

# Optional - Deepgram Voice
DEEPGRAM_API_KEY=...
DEEPGRAM_ENABLED=true

# Optional - Push Notifications
VAPID_PUBLIC_KEY=...
VAPID_PRIVATE_KEY=...

# Optional - Authentication
API_KEY=your_secret_key  # Leave empty for dev mode
```

### Generate VAPID Keys
```powershell
pip install py-vapid
vapid --gen
# Copy output to .env
```

---

## 🐛 Troubleshooting

### Issue: Backend won't start
**Error:** `asyncpg.exceptions.InvalidPasswordError`
- Check PostgreSQL 16 is running: `Get-Service postgresql-x64-16`
- Verify database exists: Check DATABASE_URL in `.env`

### Issue: Frontend build errors
**Error:** `Module not found`
- Run: `npm install` in frontend directory
- Clear cache: `rm -rf .next`

### Issue: "Table does not exist"
**Error:** `UndefinedTableError: relation "loci_sessions" does not exist`
- Apply migration: `psql -U postgres -d recall_mvp -f backend/migration_phase5.sql`

### Issue: Push notifications not working
- Check VAPID keys configured in `.env`
- Check browser supports notifications (Chrome, Firefox, Edge)
- Check HTTPS (localhost works, but production needs HTTPS)

### Issue: Knowledge graph shows no data
- Ensure you have captures with embeddings
- Check: `SELECT COUNT(*) FROM extracted_points WHERE embedding IS NOT NULL;`
- If 0, create some captures first

---

## 📚 Further Reading

- **Architecture:** See `docs/system-design.md`
- **Phase 5 Design:** See `docs/phase5-design.md`
- **E2E Test Report:** See `docs/e2e-test-report.md`
- **Security Fixes:** See `PHASE5_SECURITY_FIXES.md`
- **API Endpoints:** See `backend/README.md`

---

## 🎉 You're Ready!

Your ReCall application is fully functional with:
- ✅ AI-powered knowledge capture
- ✅ Spaced repetition (FSRS)
- ✅ Teach mode
- ✅ Voice agent
- ✅ Knowledge graph visualization
- ✅ Analytics dashboard
- ✅ Method of Loci memory palaces
- ✅ Push notifications
- ✅ Browser extension
- ✅ PWA support

Start capturing and reviewing knowledge! 🚀
