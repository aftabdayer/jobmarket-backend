# ⚙️ JobMarket AI — Backend (FastAPI)

> **FastAPI backend** powering the JobMarket AI platform — synthetic job data engine, NLP skill extraction, percentile salary analytics, and a Groq LLM chatbot over 1,000 India IT job postings.

👉 **[Live App](https://jobmarket-frontend.vercel.app/)** &nbsp;|&nbsp; 🖥️ **[Frontend Repo](https://github.com/aftabdayer/jobmarket-frontend)**

---

## What This Repo Contains

This is the data and API layer for JobMarket AI. It handles job data generation, NLP skill extraction, all analytics calculations, and the AI chatbot — serving a Next.js frontend via REST API.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check — job count, skill count, posts this week |
| `GET` | `/api/summary` | Market KPIs — total jobs, companies, cities, avg salary, weekly posts |
| `GET` | `/api/skills/top` | Top skills by demand; filterable by role title |
| `GET` | `/api/skills/salary` | Skills ranked by average salary; filterable by role |
| `GET` | `/api/skills/categories` | Skills grouped by category (languages, frameworks, tools, etc.) |
| `GET` | `/api/job-titles` | All job titles in the database |
| `GET` | `/api/cities` | Hiring demand and avg salary by city |
| `GET` | `/api/jobs` | Job search — filter by keyword, city, company, skill, experience |
| `POST` | `/api/chat` | LLM chatbot — answers career questions grounded in live DB data |
| `POST` | `/api/scrape` | Trigger background job data refresh |
| `POST` | `/api/reseed` | Wipe and reseed database with fresh synthetic jobs |

---

## Data Pipeline

```
Synthetic job generator (1,000 jobs across 15 IT roles)
        ↓
NLP skill extraction — 125 unique skills, 9,833 skill–role associations
        ↓
SQLite DB — jobs, job_skills, chat_sessions tables
        ↓
Analytics layer — percentiles, city heatmaps, salary bands, trends
        ↓
FastAPI REST endpoints → Next.js frontend
        ↓
Groq + LLaMA3 chatbot (grounded in live DB context)
```

---

## Key Stats

| Metric | Value |
|--------|-------|
| Jobs in database | 1,000 |
| IT roles covered | 15 |
| Unique skills | 125 |
| Skill–role associations | 9,833 |
| Cities tracked | 24 |
| Auto-refresh | Every 24 hours |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API Framework | FastAPI · Python |
| Database | SQLite |
| Data Generation | Custom synthetic engine |
| NLP | Keyword + regex skill extraction |
| LLM | Groq API · LLaMA-3.3-70b |
| Deployment | Render |

---

## Running Locally

```bash
# 1. Clone
git clone https://github.com/aftabdayer/jobmarket-backend.git
cd jobmarket-backend

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set Groq API key
export GROQ_API_KEY=your_key_here

# 4. Start the server
uvicorn main:app --reload
```

API available at `http://localhost:8000`  
Interactive docs at `http://localhost:8000/docs`

Database is auto-seeded with 1,000 jobs on first run. Auto-refreshes every 24 hours.

---

## Author

**Aftab Dayer** · [LinkedIn](https://linkedin.com/in/aftabdayer) · [GitHub](https://github.com/aftabdayer)  
NIT Hamirpur 2025 · IEEE Published · Microsoft Power BI Certified (PL-300)
