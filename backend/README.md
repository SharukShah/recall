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
# Edit .env and add your OPENAI_API_KEY
```

5. **Run server**
```powershell
uvicorn main:app --reload
```

Server runs at: http://localhost:8000

### API Endpoints

- `POST /api/captures` — Capture text
- `GET /api/reviews/due` — Get due questions
- `POST /api/reviews/evaluate` — Evaluate answer
- `POST /api/reviews/rate` — Submit rating
- `GET /api/stats/dashboard` — Get stats

### Test

```powershell
curl http://localhost:8000/
```

Should return: `{"message": "ReCall API"}`
