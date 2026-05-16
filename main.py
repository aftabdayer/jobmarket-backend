"""
Job Market Intelligence Engine — FastAPI Backend
=================================================
All API endpoints. Run with:
    uvicorn main:app --reload --port 8000
"""

import os, sys, json, threading, time
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(__file__))
from database import get_conn, init_db
from scraper import run_scrape

try:
    from analytics import run_all_analytics, build_market_context, get_skill_velocity
    HAS_ANALYTICS = True
except Exception:
    HAS_ANALYTICS = False
    def run_all_analytics(): pass
    def build_market_context(): return "No analytics available"
    def get_skill_velocity(n=10): return []

app = FastAPI(
    title="JobMarket AI — India IT Intelligence",
    description="Real-time India job market analytics — all IT roles",
    version="3.0",
)

# ── Auto-refresh scheduler (runs every 24h) ───────────────────────────────────
_last_refresh = {"ts": None}

def _background_refresh():
    while True:
        time.sleep(86400)   # 24 hours
        try:
            print("Auto-refresh: adding new synthetic jobs...")
            run_scrape(use_live=False, synthetic_count=200)
            run_all_analytics()
            _last_refresh["ts"] = datetime.now().isoformat()
            print("Auto-refresh complete")
        except Exception as e:
            print(f"Auto-refresh error: {e}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()
    conn = get_conn()
    count = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    conn.close()
    if count == 0:
        print("No data found — seeding with 1000 jobs...")
        run_scrape(use_live=False, synthetic_count=1000)
    if HAS_ANALYTICS:
        run_all_analytics()
        _last_refresh["ts"] = datetime.now().isoformat()
    # Start background auto-refresh thread
    t = threading.Thread(target=_background_refresh, daemon=True)
    t.start()
    print("Auto-refresh scheduler started (runs every 24h)")


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    conn = get_conn()
    jobs   = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    skills = conn.execute("SELECT COUNT(*) FROM job_skills").fetchone()[0]
    recent = conn.execute("SELECT COUNT(*) FROM jobs WHERE posted_date >= date('now','-7 days')").fetchone()[0]
    conn.close()
    return {
        "status": "ok", "jobs_in_db": jobs, "skills_in_db": skills,
        "posted_this_week": recent, "version": "3.0",
        "last_refresh": _last_refresh["ts"],
        "next_refresh": "Runs every 24 hours automatically",
        "ts": datetime.now().isoformat()
    }


# ── Summary KPIs ──────────────────────────────────────────────────────────────
@app.get("/api/summary")
def get_summary():
    conn = get_conn()
    total      = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    companies  = conn.execute("SELECT COUNT(DISTINCT company) FROM jobs").fetchone()[0]
    cities     = conn.execute("SELECT COUNT(DISTINCT city) FROM jobs WHERE city!=''").fetchone()[0]
    skills_cnt = conn.execute("SELECT COUNT(DISTINCT skill) FROM job_skills").fetchone()[0]
    avg_sal    = conn.execute("""
        SELECT ROUND(AVG((salary_min+salary_max)/2),1)
        FROM jobs WHERE salary_min IS NOT NULL
    """).fetchone()[0]
    this_week  = conn.execute("""
        SELECT COUNT(*) FROM jobs
        WHERE posted_date >= date('now','-7 days')
    """).fetchone()[0]
    conn.close()
    return {
        "total_jobs": total,
        "companies_hiring": companies,
        "cities": cities,
        "unique_skills": skills_cnt,
        "avg_salary_lpa": avg_sal,
        "posted_this_week": this_week,
    }


# ── Top skills (supports role_title filter for dropdown) ──────────────────────
@app.get("/api/skills/top")
def top_skills(limit: int = 20, category: Optional[str] = None, role_title: Optional[str] = None):
    conn = get_conn()
    if role_title and role_title != "All":
        rows = conn.execute("""
            SELECT js.skill, COUNT(DISTINCT js.job_id) as job_count,
                   ROUND(COUNT(DISTINCT js.job_id)*100.0/(SELECT COUNT(*) FROM jobs WHERE title LIKE ?),1) as pct,
                   ROUND(AVG((j.salary_min+j.salary_max)/2),0) as avg_salary
            FROM job_skills js
            JOIN jobs j ON j.job_id = js.job_id
            WHERE j.title LIKE ?
            GROUP BY js.skill ORDER BY job_count DESC LIMIT ?
        """, (f"%{role_title}%", f"%{role_title}%", limit)).fetchall()
    else:
        rows = conn.execute("""
            SELECT js.skill, COUNT(DISTINCT js.job_id) as job_count,
                   ROUND(COUNT(DISTINCT js.job_id)*100.0/(SELECT COUNT(*) FROM jobs),1) as pct,
                   ROUND(AVG((j.salary_min+j.salary_max)/2),0) as avg_salary
            FROM job_skills js
            JOIN jobs j ON j.job_id = js.job_id
            GROUP BY js.skill ORDER BY job_count DESC LIMIT ?
        """, (limit,)).fetchall()
    conn.close()
    return [{"skill": r[0], "job_count": r[1], "pct": r[2], "avg_salary": r[3]} for r in rows]


@app.get("/api/skills/salary")
def skills_by_salary(limit: int = 15, role_title: Optional[str] = None):
    conn = get_conn()
    if role_title and role_title != "All":
        rows = conn.execute("""
            SELECT js.skill,
                   COUNT(DISTINCT js.job_id) as jobs,
                   ROUND(MIN((j.salary_min+j.salary_max)/2),0) as min_salary,
                   ROUND(AVG((j.salary_min+j.salary_max)/2),0) as avg_salary,
                   ROUND(MAX((j.salary_min+j.salary_max)/2),0) as max_salary
            FROM job_skills js
            JOIN jobs j ON j.job_id = js.job_id
            WHERE j.title LIKE ? AND j.salary_min IS NOT NULL
            GROUP BY js.skill HAVING jobs >= 2
            ORDER BY avg_salary DESC LIMIT ?
        """, (f"%{role_title}%", limit)).fetchall()
    else:
        rows = conn.execute("""
            SELECT js.skill,
                   COUNT(DISTINCT js.job_id) as jobs,
                   ROUND(MIN((j.salary_min+j.salary_max)/2),0) as min_salary,
                   ROUND(AVG((j.salary_min+j.salary_max)/2),0) as avg_salary,
                   ROUND(MAX((j.salary_min+j.salary_max)/2),0) as max_salary
            FROM job_skills js
            JOIN jobs j ON j.job_id = js.job_id
            WHERE j.salary_min IS NOT NULL
            GROUP BY js.skill HAVING jobs >= 3
            ORDER BY avg_salary DESC LIMIT ?
        """, (limit,)).fetchall()
    conn.close()
    return [{"skill": r[0], "jobs": r[1], "min": r[2], "avg": r[3], "max": r[4]} for r in rows]


@app.get("/api/job-titles")
def get_job_titles():
    conn = get_conn()
    rows = conn.execute("SELECT title, COUNT(*) as cnt FROM jobs GROUP BY title ORDER BY cnt DESC LIMIT 40").fetchall()
    conn.close()
    return ["All"] + [r[0] for r in rows]


@app.get("/api/skills/categories")
def skills_by_category():
    conn = get_conn()
    rows = conn.execute("""
        SELECT js.category, COUNT(DISTINCT js.skill) as skills, COUNT(*) as mentions
        FROM job_skills js
        GROUP BY js.category ORDER BY mentions DESC
    """).fetchall()
    conn.close()
    return [{"category": r[0], "unique_skills": r[1], "total_mentions": r[2]} for r in rows]


# ── City analytics ────────────────────────────────────────────────────────────
@app.get("/api/cities")
def city_demand(limit: int = 15):
    conn = get_conn()
    rows = conn.execute("""
        SELECT city, job_count, avg_salary, pct_of_jobs
        FROM v_city_demand LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [{"city": r[0], "jobs": r[1], "avg_salary": r[2], "pct": r[3]} for r in rows]


@app.get("/api/cities/{city}/skills")
def city_top_skills(city: str, limit: int = 10):
    conn = get_conn()
    rows = conn.execute("""
        SELECT js.skill, COUNT(*) as cnt
        FROM job_skills js
        JOIN jobs j ON j.job_id = js.job_id
        WHERE j.city = ?
        GROUP BY js.skill ORDER BY cnt DESC LIMIT ?
    """, (city, limit)).fetchall()
    conn.close()
    return {"city": city, "top_skills": [{"skill": r[0], "count": r[1]} for r in rows]}


# ── Company analytics ─────────────────────────────────────────────────────────
@app.get("/api/companies")
def company_hiring(limit: int = 20):
    conn = get_conn()
    rows = conn.execute("""
        SELECT company, open_roles, avg_salary, latest_posting
        FROM v_company_hiring LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [{"company": r[0], "open_roles": r[1], "avg_salary": r[2], "latest": r[3]} for r in rows]


# ── Salary analytics ──────────────────────────────────────────────────────────
@app.get("/api/salary/distribution")
def salary_distribution():
    conn = get_conn()
    rows = conn.execute("""
        SELECT
            CASE
                WHEN (salary_min+salary_max)/2 < 6  THEN '0-6 LPA'
                WHEN (salary_min+salary_max)/2 < 10 THEN '6-10 LPA'
                WHEN (salary_min+salary_max)/2 < 15 THEN '10-15 LPA'
                WHEN (salary_min+salary_max)/2 < 20 THEN '15-20 LPA'
                ELSE '20+ LPA'
            END AS bracket,
            COUNT(*) AS jobs
        FROM jobs
        WHERE salary_min IS NOT NULL
        GROUP BY bracket ORDER BY MIN(salary_min)
    """).fetchall()
    conn.close()
    return [{"bracket": r[0], "count": r[1]} for r in rows]


@app.get("/api/salary/percentiles")
def salary_percentiles(role_title: Optional[str] = None):
    conn = get_conn()
    if role_title and role_title != "All":
        rows = conn.execute("SELECT (salary_min+salary_max)/2 as mid FROM jobs WHERE salary_min IS NOT NULL AND title LIKE ? ORDER BY mid", (f"%{role_title}%",)).fetchall()
    else:
        rows = conn.execute("SELECT (salary_min+salary_max)/2 as mid FROM jobs WHERE salary_min IS NOT NULL ORDER BY mid").fetchall()
    conn.close()
    if not rows:
        return {"p25": None, "p50": None, "p75": None, "p90": None}
    vals = [r[0] for r in rows]
    n = len(vals)
    def pct(p): return round(vals[min(int(n*p/100), n-1)], 1)
    return {"p25": pct(25), "p50": pct(50), "p75": pct(75), "p90": pct(90), "min": round(vals[0],1), "max": round(vals[-1],1)}


@app.get("/api/salary/by-title")
def salary_by_title(role_title: Optional[str] = None):
    conn = get_conn()
    if role_title and role_title != "All":
        rows = conn.execute("""SELECT title, COUNT(*) as jobs, ROUND(AVG((salary_min+salary_max)/2),1) as avg_salary, ROUND(MIN(salary_min),1) as min_sal, ROUND(MAX(salary_max),1) as max_sal FROM jobs WHERE salary_min IS NOT NULL AND title LIKE ? GROUP BY title HAVING jobs >= 1 ORDER BY avg_salary DESC LIMIT 15""", (f"%{role_title}%",)).fetchall()
    else:
        rows = conn.execute("""SELECT title, COUNT(*) as jobs, ROUND(AVG((salary_min+salary_max)/2),1) as avg_salary, ROUND(MIN(salary_min),1) as min_sal, ROUND(MAX(salary_max),1) as max_sal FROM jobs WHERE salary_min IS NOT NULL GROUP BY title HAVING jobs >= 3 ORDER BY avg_salary DESC LIMIT 15""").fetchall()
    conn.close()
    return [{"title": r[0], "jobs": r[1], "avg": r[2], "min": r[3], "max": r[4]} for r in rows]


# ── Trends ────────────────────────────────────────────────────────────────────
@app.get("/api/trends/weekly")
def weekly_posting_trend(weeks: int = 12):
    conn = get_conn()
    rows = conn.execute("""
        SELECT strftime('%Y-W%W', posted_date) AS week,
               COUNT(*) AS jobs
        FROM jobs
        WHERE posted_date >= date('now', ?)
        GROUP BY week ORDER BY week
    """, (f"-{weeks*7} days",)).fetchall()
    conn.close()
    return [{"week": r[0], "jobs": r[1]} for r in rows]


@app.get("/api/trends/skills-over-time")
def skill_trend(skill: str = "Python", weeks: int = 12):
    conn = get_conn()
    rows = conn.execute("""
        SELECT strftime('%Y-W%W', j.posted_date) AS week,
               COUNT(*) AS mentions
        FROM job_skills js
        JOIN jobs j ON j.job_id = js.job_id
        WHERE js.skill = ? AND j.posted_date >= date('now', ?)
        GROUP BY week ORDER BY week
    """, (skill, f"-{weeks*7} days")).fetchall()
    conn.close()
    return {"skill": skill, "trend": [{"week": r[0], "mentions": r[1]} for r in rows]}


# ── Job search (expanded — all IT roles) ──────────────────────────────────────
@app.get("/api/jobs")
def search_jobs(
    q: Optional[str] = None,
    city: Optional[str] = None,
    company: Optional[str] = None,
    skill: Optional[str] = None,
    experience: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    conn = get_conn()
    base = """
        SELECT DISTINCT j.job_id, j.title, j.company, j.city,
               j.salary_text, j.experience, j.job_type,
               j.source, j.posted_date, j.url, j.salary_min, j.salary_max
        FROM jobs j
    """
    conditions, params = [], []

    if skill:
        base += " JOIN job_skills js ON js.job_id = j.job_id"
        conditions.append("js.skill = ?")
        params.append(skill)
    if q:
        conditions.append("(j.title LIKE ? OR j.company LIKE ? OR j.description LIKE ?)")
        params += [f"%{q}%", f"%{q}%", f"%{q}%"]
    if city:
        conditions.append("j.city LIKE ?")
        params.append(f"%{city}%")
    if company:
        conditions.append("j.company LIKE ?")
        params.append(f"%{company}%")
    if experience:
        try:
            exp_num = int(experience.split("-")[0].replace("+", ""))
            conditions.append(
                "(CAST(SUBSTR(j.experience, 1, 1) AS INTEGER) >= ? AND "
                " CAST(SUBSTR(j.experience, 1, 1) AS INTEGER) <= ? + 3)"
            )
            params += [max(0, exp_num - 1), exp_num + 2]
        except Exception:
            pass

    if conditions:
        base += " WHERE " + " AND ".join(conditions)

    base += " ORDER BY j.posted_date DESC LIMIT ? OFFSET ?"
    params += [limit, offset]

    rows = conn.execute(base, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/api/reseed")
def reseed_database(background_tasks: BackgroundTasks, count: int = 1000):
    """Wipe and reseed with expanded job types (SDE, AI, Product, DevOps etc)."""
    def _reseed():
        conn = get_conn()
        conn.execute("DELETE FROM job_skills")
        conn.execute("DELETE FROM jobs")
        conn.commit()
        conn.close()
        run_scrape(use_live=False, synthetic_count=count)
        run_all_analytics()
        print(f"✓ Reseed complete with {count} expanded jobs")
    background_tasks.add_task(_reseed)
    return {"message": f"Reseeding {count} jobs in background. Check /health in ~30 seconds."}


# ── AI Chatbot ────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

# ⚠️ GET YOUR FREE KEY: https://console.groq.com → API Keys → Create Key
# Paste it below replacing PASTE_YOUR_GROQ_KEY_HERE
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
@app.post("/api/chat")
def chat(req: ChatRequest):
    if GROQ_API_KEY == "PASTE_YOUR_GROQ_KEY_HERE" or not GROQ_API_KEY:
        return {"reply": "⚠️ Groq API key not set. Get a free key at https://console.groq.com → paste it in main.py line with GROQ_API_KEY."}
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
    except Exception as e:
        return {"reply": f"Groq import error: {e}"}

    # Build rich context from DB
    conn = get_conn()
    total_jobs = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    companies  = conn.execute("SELECT COUNT(DISTINCT company) FROM jobs").fetchone()[0]
    avg_sal    = conn.execute("SELECT ROUND(AVG((salary_min+salary_max)/2),1) FROM jobs WHERE salary_min IS NOT NULL").fetchone()[0]
    top_skills = conn.execute("""
        SELECT js.skill, COUNT(DISTINCT js.job_id) as cnt,
               ROUND(AVG((j.salary_min+j.salary_max)/2),0) as avg_sal
        FROM job_skills js JOIN jobs j ON j.job_id=js.job_id
        GROUP BY js.skill ORDER BY cnt DESC LIMIT 20
    """).fetchall()
    top_cities = conn.execute("""
        SELECT city, COUNT(*) as cnt, ROUND(AVG((salary_min+salary_max)/2),0) as avg_sal
        FROM jobs WHERE city IS NOT NULL GROUP BY city ORDER BY cnt DESC LIMIT 10
    """).fetchall()
    top_companies = conn.execute("""
        SELECT company, COUNT(*) as cnt FROM jobs GROUP BY company ORDER BY cnt DESC LIMIT 10
    """).fetchall()
    salary_by_title = conn.execute("""
        SELECT title, ROUND(AVG((salary_min+salary_max)/2),0) as avg_sal, COUNT(*) as cnt
        FROM jobs WHERE salary_min IS NOT NULL
        GROUP BY title HAVING cnt >= 3 ORDER BY avg_sal DESC LIMIT 12
    """).fetchall()
    conn.close()

    skills_str   = ", ".join([f"{r[0]}({r[1]} jobs, avg ₹{r[2]}L)" for r in top_skills])
    cities_str   = ", ".join([f"{r[0]}({r[1]} jobs, avg ₹{r[2]}L)" for r in top_cities])
    company_str  = ", ".join([f"{r[0]}({r[1]} openings)" for r in top_companies])
    salary_str   = ", ".join([f"{r[0]}: ₹{r[1]}L avg" for r in salary_by_title])

    system_prompt = f"""You are JobMarket AI — a sharp, data-driven career intelligence analyst for India's IT job market.

== LIVE DATABASE SNAPSHOT ({datetime.now().strftime('%B %Y')}) ==
Total job postings: {total_jobs:,} | Companies hiring: {companies} | Market avg salary: ₹{avg_sal}L

TOP SKILLS IN DEMAND:
{skills_str}

TOP CITIES:
{cities_str}

TOP HIRING COMPANIES:
{company_str}

SALARY BY ROLE:
{salary_str}

== YOUR JOB ==
Answer career questions using ONLY this real data. Always:
- Quote specific numbers (job counts, salaries, %)
- Give actionable advice ("learn X because Y companies need it")  
- Compare options when asked ("Python vs SQL: Python has X jobs at ₹Yl avg")
- Mention AI/ML skills when relevant (Generative AI, LLMs, RAG are emerging)
- Keep answers under 150 words, use bullet points for lists
- Be encouraging but realistic about the Indian job market

You cover ALL IT roles: SDE, Data, AI/ML, Product, DevOps, QA, Design, Business Analyst."""

    # Get chat history
    conn = get_conn()
    history = conn.execute("""
        SELECT role, message FROM chat_sessions
        WHERE session_id = ? ORDER BY created_at DESC LIMIT 10
    """, (req.session_id,)).fetchall()
    history = list(reversed(history))

    # Save user message
    conn.execute(
        "INSERT INTO chat_sessions (session_id, role, message) VALUES (?,?,?)",
        (req.session_id, "user", req.message)
    )
    conn.commit()
    conn.close()

    messages = [{"role": "system", "content": system_prompt}]
    for h in history:
        messages.append({"role": h[0], "content": h[1]})
    messages.append({"role": "user", "content": req.message})

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=250,
            temperature=0.4,
        )
        reply = response.choices[0].message.content

        # Save assistant reply
        conn = get_conn()
        conn.execute(
            "INSERT INTO chat_sessions (session_id, role, message) VALUES (?,?,?)",
            (req.session_id, "assistant", reply)
        )
        conn.commit()
        conn.close()

        return {"reply": reply}
    except Exception as e:
        return {"reply": f"Error: {str(e)}"}


# ── Scrape trigger ────────────────────────────────────────────────────────────
@app.post("/api/scrape")
def trigger_scrape(background_tasks: BackgroundTasks, live: bool = False, count: int = 200):
    background_tasks.add_task(run_scrape, use_live=live, synthetic_count=count)
    return {"message": "Scrape started in background", "live": live, "count": count}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
