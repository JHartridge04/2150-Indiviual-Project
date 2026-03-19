# 👗 AI-Powered Personal Style Assistant

A full-stack web app that uses AI (Claude) to analyse your outfit photos and provide personalised style recommendations.

## Tech Stack

| Layer     | Technology                              |
|-----------|----------------------------------------|
| Frontend  | React (Create React App)               |
| Backend   | Python + Flask                         |
| Auth/DB   | Supabase (Auth + Storage)              |
| AI        | Anthropic Claude (vision analysis)     |

---

## Project Structure

```
.
├── .env.example         # Copy to .env and fill in your keys
├── frontend/            # React app
│   ├── src/
│   │   ├── components/  # Reusable UI components
│   │   ├── context/     # AuthContext (Supabase session state)
│   │   ├── pages/       # Route-level page components
│   │   └── services/    # API & Supabase client helpers
│   └── package.json
└── backend/             # Flask API
    ├── app.py           # Main application & endpoints
    ├── requirements.txt
    └── tests/           # Pytest unit tests
```

---

## Prerequisites

- Node.js ≥ 18
- Python ≥ 3.11
- A [Supabase](https://supabase.com) project with:
  - Auth enabled
  - A storage bucket named `outfit-photos` (set to public or use RLS)
- An [Anthropic](https://console.anthropic.com) API key

---

## Setup

### 1. Clone & configure environment variables

```bash
cp .env.example .env
# Edit .env and fill in SUPABASE_URL, SUPABASE_ANON_KEY, ANTHROPIC_API_KEY
```

### 2. Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
flask run                        # Starts on http://localhost:5000
```

### 3. Frontend

```bash
cd frontend
npm install
npm start                        # Starts on http://localhost:3000
```

---

## API Endpoints

| Method | Path                   | Description                              | Auth |
|--------|------------------------|------------------------------------------|------|
| POST   | `/api/auth/signup`     | Register a new user                      | ✗    |
| POST   | `/api/auth/login`      | Sign in and get a JWT session            | ✗    |
| POST   | `/api/auth/logout`     | Sign out                                 | ✓    |
| POST   | `/api/upload`          | Upload an outfit photo to Supabase       | ✓    |
| POST   | `/api/analyze`         | AI style analysis via Claude             | ✓    |
| GET/POST | `/api/recommendations` | Get clothing recommendations           | ✓    |
| GET    | `/api/health`          | Health check                             | ✗    |

Authenticated endpoints require `Authorization: Bearer <access_token>`.

---

## Running Tests

### Backend (pytest)

```bash
cd backend
source venv/bin/activate
pytest tests/ -v
```

### Frontend (Jest)

```bash
cd frontend
npm test
```
