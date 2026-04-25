# ReCall Backend — MVP

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 16+
- OpenAI API key

### Setup

1. **Create virtual environment**
```powershell
cd E:\Sharuk\recall\backend
python -m venv venv
.\venv\Scripts\Activate.ps1
```

2. **Install dependencies**
```powershell
pip install -r requirements.txt
```

3. **Set up PostgreSQL**
```powershell
# Create database
psql -U postgres
CREATE DATABASE recall_mvp;
\q

# Run schema
psql -U postgres -d recall_mvp -f schema.sql
```

4. **Configure environment**
```powershell
# Create .env file
Copy-Item .env.example .env
# Edit .env and add your configuration:
# - OPENAI_API_KEY (required)
# - VAPID keys for push notifications (optional)
# - API_KEY for authentication (optional, recommended for production)
```

**Important Security Configuration:**

- **API_KEY**: Set a strong API key for production deployment. Leave empty for development (disables authentication).
- **VAPID Keys**: Required for push notifications. Generate using:
  ```powershell
  pip install py-vapid
  vapid --gen
  ```
  Then add `VAPID_PRIVATE_KEY` and `VAPID_PUBLIC_KEY` to your `.env` file.

5. **Install pytz for timezone support**
```powershell
pip install pytz
```

6. **Run server**
```powershell
uvicorn main:app --reload
```

Server runs at: http://localhost:8000

### API Endpoints

**Core Features:**
- `POST /api/captures` — Capture text (rate: 10/min)
- `GET /api/reviews/due` — Get due questions
- `POST /api/reviews/evaluate` — Evaluate answer
- `POST /api/reviews/rate` — Submit rating
- `GET /api/stats/dashboard` — Get stats

**Phase 5 Features (Authenticated):**
- `POST /api/notifications/subscribe` — Subscribe to push notifications (rate: 5/5min)
- `GET /api/notifications/settings` — Get notification settings
- `PUT /api/notifications/settings` — Update notification settings
- `POST /api/notifications/test` — Send test notification (rate: 5/hour)
- `POST /api/loci/create` — Create memory palace (rate: 10/hour)
- `GET /api/loci/{session_id}` — Get loci session
- `POST /api/loci/{session_id}/recall` — Submit recall (rate: 30/hour)
- `GET /api/knowledge/graph/data` — Get knowledge graph (rate: 1/min)
- `GET /api/analytics` — Get comprehensive analytics
- `GET /api/analytics/retention` — Get retention curve
- `GET /api/analytics/weak-areas` — Get weak areas

**Authentication:**
All Phase 5 endpoints require authentication. Include the API key in the Authorization header:
```
Authorization: Bearer <your_api_key>
```

**Rate Limits:**
- Notification subscribe: 5 requests per 5 minutes
- Test notification: 5 requests per hour
- Loci creation: 10 requests per hour
- Loci recall: 30 requests per hour
- Knowledge graph: 1 request per minute
- Maximum 50 loci sessions per user

### Test

```powershell
curl http://localhost:8000/
```

Should return: `{"message": "ReCall API"}`
