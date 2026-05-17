# ⚙️ JobMarket AI — Backend (FastAPI + SQLite)

> **FastAPI backend** powering the JobMarket AI platform — NLP skill extraction, percentile salary engine, and Groq LLM chatbot over 1,000 India IT job postings.

👉 **[Live App](https://jobmarket-frontend.vercel.app/)** &nbsp;|&nbsp; 🖥️ **[Frontend Repo](https://github.com/aftabdayer/jobmarket-frontend)**

---

## What This Repo Contains

This is the API and data layer for JobMarket AI. It handles:

- Job data ingestion and storage (SQLite)
- NLP pipeline for skill extraction from job descriptions
- Percentile salary calculations (P25/P50/P75/P90)
- REST API endpoints consumed by the Next.js frontend
- Groq + LLaMA3 chatbot with live database context

---

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /jobs` | Browse and filter job postings |
| `GET /skills` | Skill demand by role |
| `GET /salaries` | Salary percentiles by role and city |
| `GET /cities` | Hiring activity by city |
| `GET /companies` | Company-level stats |
| `GET /trends` | Weekly posting volume over time |
| `POST /chat` | LLM chatbot — natural language Q&A over job data |

---

## Data Pipeline

```
Raw job postings (1,000)
        ↓
NLP Extraction (skill keywords + regex)
        ↓
SQLite DB — jobs, skills, salary, city tables
        ↓
Aggregation layer — percentiles, trends, counts
        ↓
FastAPI REST endpoints
        ↓
Next.js frontend → Groq chatbot
```

**Output:** 125 unique skills · 9,833 skill–role associations · P25/P50/P75/P90 salary bands across 24 cities

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API Framework | FastAPI · Python |
| Database | SQLite |
| NLP | Custom extraction pipeline (regex + keyword matching) |
| LLM | Groq API · LLaMA3 |
| Deployment | Render |

---

## Running Locally

```bash
# 1. Clone
git clone https://github.com/aftabdayer/jobmarket-backend.git
cd jobmarket-backend

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set your Groq API key
export GROQ_API_KEY=your_key_here

# 4. Start the server
uvicorn main:app --reload
```

API will be available at `http://localhost:8000`  
Docs at `http://localhost:8000/docs`

---

## Author

**Aftab Dayer** · [LinkedIn](https://linkedin.com/in/aftabdayer) · [GitHub](https://github.com/aftabdayer)  
NIT Hamirpur 2025 · IEEE Published · Microsoft Power BI Certified (PL-300)
