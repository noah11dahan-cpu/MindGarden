# MindGarden

MindGarden is a lightweight habit and daily check-in web application that helps users build consistency by tracking habits, logging daily mood and reflections, computing streak-based insights, and generating short AI suggestions using recent history (optionally RAG-backed with embeddings and FAISS).

---

## Features

- Email/password authentication (token-based)
- Habit management (create, list, delete)
- Free-tier rule: maximum 3 habits
- Daily check-ins:
  - Mood score
  - Optional reflection note
  - Per-habit completion tracking
  - Enforces one check-in per day
- Insights engine:
  - Habit streaks
  - 7-day mood average
- AI suggestions:
  - 1–2 sentence personalized “tiny challenge”
  - Optional deep-dive endpoint (premium hook)
- Reflection embeddings (RAG):
  - Stores embedded reflections
  - FAISS-based retrieval of relevant past notes
  - Graceful fallback if embeddings are unavailable
- Observability:
  - Metrics endpoint with daily counters and latency stats
- Monetization hooks:
  - subscription_tier on users
  - Upgrade endpoint (no payments yet)
  - Reflection export hook
- Demo seeding:
  - Endpoint creates a deterministic demo user, habits, and 7 days of data for recruiter demos

---

## Tech Stack

- FastAPI
- React + Vite
- PostgreSQL
- SQLAlchemy
- Docker & Docker Compose
- Caddy reverse proxy
- FAISS + sentence-transformers (optional)
- pytest
- Python 3.11

---

## Requirements

- Docker Desktop
- Git
- Optional: Python 3.11+

---

## Getting Started (Windows / PowerShell)

Run the following commands in order:

git clone https://github.com/your-username/mindgarden.git  
cd mindgarden  

Copy-Item .env.example .env  

docker compose up -d --build

---

## Accessing the App

App: http://localhost:8080  
API Docs (Swagger): http://localhost:8080/docs  
OpenAPI JSON: http://localhost:8080/openapi.json  

---

## Demo Flow (Recruiter-Ready)

Seed demo data by calling:

Invoke-RestMethod -Method POST http://localhost:8080/api/dev/seed_demo

Then:
1. Log in with the demo user
2. Create today’s check-in live
3. View insights and AI suggestions
4. Show metrics and analytics endpoints

---

## Running Tests

docker compose exec api pytest -vv

---

## Project Structure

app/  
  main.py  
  models.py  
  db.py  
  auth/  
  habits/  
  checkins/  
  insights/  
  ai/  
  rag/  
  metrics/  

frontend/  
  src/  
  index.html  

worker/  

tests/  

docker-compose.yml  
Dockerfile  
Caddyfile  
.env.example  
README.md  

---

## Next Steps (Optional Enhancements)

- Real payment integration
- Richer analytics visualizations
- PDF / Markdown exports
- Mobile-friendly UI
- Background retraining of embeddings
