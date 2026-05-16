"""
Job Market Intelligence Engine — Analytics Engine
==================================================
Weekly trend calculations, skill velocity, salary intelligence,
and market snapshot generator for the AI chatbot context.

Run standalone to refresh all trend tables:
    python analytics.py
"""

import json
import sqlite3
from datetime import datetime, timedelta
from database import get_conn


# ── Trend Aggregation ─────────────────────────────────────────────────────────

def compute_weekly_skill_trends():
    """
    Aggregate skill mentions by ISO week into skill_trends table.
    Calculates velocity: is this skill rising or falling?
    """
    conn = get_conn()

    # Get all weeks present in jobs table
    weeks = conn.execute("""
        SELECT DISTINCT strftime('%Y-W%W', posted_date) AS week
        FROM jobs WHERE posted_date IS NOT NULL
        ORDER BY week
    """).fetchall()

    total_jobs = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]

    for (week,) in weeks:
        # Jobs posted in this week
        week_jobs = conn.execute("""
            SELECT COUNT(*) FROM jobs
            WHERE strftime('%Y-W%W', posted_date) = ?
        """, (week,)).fetchone()[0]

        if week_jobs == 0:
            continue

        # Skills in this week
        skill_rows = conn.execute("""
            SELECT js.skill, COUNT(*) as cnt,
                   AVG((j.salary_min + j.salary_max) / 2) as avg_sal
            FROM job_skills js
            JOIN jobs j ON j.job_id = js.job_id
            WHERE strftime('%Y-W%W', j.posted_date) = ?
            GROUP BY js.skill
        """, (week,)).fetchall()

        for row in skill_rows:
            skill, cnt, avg_sal = row
            pct = round(cnt * 100.0 / week_jobs, 1)
            conn.execute("""
                INSERT OR REPLACE INTO skill_trends
                    (skill, week, count, pct_of_jobs, avg_salary)
                VALUES (?, ?, ?, ?, ?)
            """, (skill, week, cnt, pct, round(avg_sal, 0) if avg_sal else None))

    conn.commit()
    conn.close()
    print(f"✓ Skill trends computed for {len(weeks)} weeks")


def compute_weekly_company_stats():
    """Aggregate company hiring stats by week."""
    conn = get_conn()

    weeks = conn.execute("""
        SELECT DISTINCT strftime('%Y-W%W', posted_date) AS week
        FROM jobs WHERE posted_date IS NOT NULL
        ORDER BY week
    """).fetchall()

    for (week,) in weeks:
        company_rows = conn.execute("""
            SELECT company,
                   COUNT(*) as job_count,
                   AVG((salary_min + salary_max) / 2) as avg_sal
            FROM jobs
            WHERE strftime('%Y-W%W', posted_date) = ?
              AND company IS NOT NULL AND company != ''
            GROUP BY company
        """, (week,)).fetchall()

        for row in company_rows:
            company, job_count, avg_sal = row

            # Top 5 skills for this company in this week
            top_skills = conn.execute("""
                SELECT js.skill, COUNT(*) as cnt
                FROM job_skills js
                JOIN jobs j ON j.job_id = js.job_id
                WHERE strftime('%Y-W%W', j.posted_date) = ?
                  AND j.company = ?
                GROUP BY js.skill ORDER BY cnt DESC LIMIT 5
            """, (week, company)).fetchall()
            skills_json = json.dumps([r[0] for r in top_skills])

            conn.execute("""
                INSERT OR REPLACE INTO company_stats
                    (company, week, job_count, avg_salary, top_skills)
                VALUES (?, ?, ?, ?, ?)
            """, (company, week, job_count,
                  round(avg_sal, 0) if avg_sal else None, skills_json))

    conn.commit()
    conn.close()
    print(f"✓ Company stats computed for {len(weeks)} weeks")


def compute_weekly_city_stats():
    """Aggregate city demand stats by week."""
    conn = get_conn()

    weeks = conn.execute("""
        SELECT DISTINCT strftime('%Y-W%W', posted_date) AS week
        FROM jobs WHERE posted_date IS NOT NULL
        ORDER BY week
    """).fetchall()

    for (week,) in weeks:
        city_rows = conn.execute("""
            SELECT city,
                   COUNT(*) as job_count,
                   AVG((salary_min + salary_max) / 2) as avg_sal
            FROM jobs
            WHERE strftime('%Y-W%W', posted_date) = ?
              AND city IS NOT NULL AND city != ''
            GROUP BY city
        """, (week,)).fetchall()

        for row in city_rows:
            city, job_count, avg_sal = row

            top_roles = conn.execute("""
                SELECT title, COUNT(*) as cnt
                FROM jobs
                WHERE strftime('%Y-W%W', posted_date) = ?
                  AND city = ?
                GROUP BY title ORDER BY cnt DESC LIMIT 5
            """, (week, city)).fetchall()
            roles_json = json.dumps([r[0] for r in top_roles])

            conn.execute("""
                INSERT OR REPLACE INTO city_stats
                    (city, week, job_count, avg_salary, top_roles)
                VALUES (?, ?, ?, ?, ?)
            """, (city, week, job_count,
                  round(avg_sal, 0) if avg_sal else None, roles_json))

    conn.commit()
    conn.close()
    print(f"✓ City stats computed for {len(weeks)} weeks")


# ── Skill Velocity ────────────────────────────────────────────────────────────

def get_skill_velocity(top_n: int = 20):
    """
    Compares last 4 weeks vs previous 4 weeks for each skill.
    Returns velocity: positive = rising, negative = falling.
    """
    conn = get_conn()

    current_window = conn.execute("""
        SELECT js.skill, COUNT(*) as cnt
        FROM job_skills js
        JOIN jobs j ON j.job_id = js.job_id
        WHERE j.posted_date >= date('now', '-28 days')
        GROUP BY js.skill
    """).fetchall()

    previous_window = conn.execute("""
        SELECT js.skill, COUNT(*) as cnt
        FROM job_skills js
        JOIN jobs j ON j.job_id = js.job_id
        WHERE j.posted_date >= date('now', '-56 days')
          AND j.posted_date < date('now', '-28 days')
        GROUP BY js.skill
    """).fetchall()

    conn.close()

    current = {r[0]: r[1] for r in current_window}
    previous = {r[0]: r[1] for r in previous_window}

    results = []
    all_skills = set(current.keys()) | set(previous.keys())

    for skill in all_skills:
        cur = current.get(skill, 0)
        prev = previous.get(skill, 0)
        if prev == 0:
            velocity = 100.0 if cur > 0 else 0.0
        else:
            velocity = round((cur - prev) / prev * 100, 1)
        results.append({
            "skill": skill,
            "current_count": cur,
            "previous_count": prev,
            "velocity_pct": velocity,
            "trend": "rising" if velocity > 10 else "falling" if velocity < -10 else "stable"
        })

    results.sort(key=lambda x: x["velocity_pct"], reverse=True)
    return results[:top_n]


# ── Rich Market Context for Chatbot ──────────────────────────────────────────

def build_market_context() -> str:
    """
    Builds a rich, structured market intelligence brief for the Groq chatbot.
    Called fresh on each chat request so the AI always has current data.
    """
    conn = get_conn()

    total_jobs = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    companies  = conn.execute("SELECT COUNT(DISTINCT company) FROM jobs").fetchone()[0]
    avg_salary = conn.execute(
        "SELECT ROUND(AVG((salary_min+salary_max)/2),1) FROM jobs WHERE salary_min IS NOT NULL"
    ).fetchone()[0]

    # Top 20 skills
    top_skills = conn.execute("""
        SELECT skill, job_count, pct_of_all_jobs, avg_salary
        FROM v_top_skills LIMIT 20
    """).fetchall()

    # Top cities
    top_cities = conn.execute("""
        SELECT city, job_count, avg_salary FROM v_city_demand LIMIT 10
    """).fetchall()

    # Top companies hiring
    top_companies = conn.execute("""
        SELECT company, open_roles, avg_salary FROM v_company_hiring LIMIT 10
    """).fetchall()

    # Salary by title
    salary_by_title = conn.execute("""
        SELECT title, ROUND(AVG((salary_min+salary_max)/2),1) as avg_sal, COUNT(*) as jobs
        FROM jobs WHERE salary_min IS NOT NULL
        GROUP BY title HAVING jobs >= 3
        ORDER BY avg_sal DESC LIMIT 10
    """).fetchall()

    # Salary by skill (top 10)
    salary_by_skill = conn.execute("""
        SELECT skill, avg_salary, jobs FROM v_salary_by_skill LIMIT 10
    """).fetchall()

    # Freshest jobs (last 7 days)
    recent = conn.execute("""
        SELECT COUNT(*) FROM jobs WHERE posted_date >= date('now','-7 days')
    """).fetchone()[0]

    conn.close()

    # Format skills section
    skills_lines = []
    for r in top_skills:
        sal = f", avg ₹{r[3]}L" if r[3] else ""
        skills_lines.append(f"  • {r[0]}: {r[1]} jobs ({r[2]}%{sal})")

    cities_lines = [
        f"  • {r[0]}: {r[1]} jobs" + (f", avg ₹{r[2]}L" if r[2] else "")
        for r in top_cities
    ]

    companies_lines = [
        f"  • {r[0]}: {r[1]} open roles" + (f", avg ₹{r[2]}L" if r[2] else "")
        for r in top_companies
    ]

    salary_title_lines = [
        f"  • {r[0]}: ₹{r[1]}L avg ({r[2]} jobs)" for r in salary_by_title
    ]

    salary_skill_lines = [
        f"  • {r[0]}: ₹{r[1]}L avg ({r[2]} jobs)" for r in salary_by_skill
    ]

    context = f"""=== LIVE INDIA JOB MARKET DATA (Data Analytics Roles) ===
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

OVERVIEW
• Total job postings analysed: {total_jobs:,}
• Companies actively hiring: {companies}
• Average salary (all roles): ₹{avg_salary}L per annum
• Jobs posted in last 7 days: {recent}

TOP 20 IN-DEMAND SKILLS
{chr(10).join(skills_lines)}

TOP CITIES BY DEMAND
{chr(10).join(cities_lines)}

TOP COMPANIES HIRING
{chr(10).join(companies_lines)}

SALARY BY JOB TITLE
{chr(10).join(salary_title_lines)}

HIGHEST-PAYING SKILLS
{chr(10).join(salary_skill_lines)}
"""
    return context


# ── Salary Intelligence ───────────────────────────────────────────────────────

def get_salary_percentiles():
    """Returns P25, P50, P75, P90 salary percentiles."""
    conn = get_conn()
    salaries = conn.execute("""
        SELECT (salary_min + salary_max) / 2 as mid
        FROM jobs WHERE salary_min IS NOT NULL
        ORDER BY mid
    """).fetchall()
    conn.close()

    if not salaries:
        return {}

    vals = [r[0] for r in salaries]
    n = len(vals)

    def percentile(p):
        idx = int(n * p / 100)
        return round(vals[min(idx, n - 1)], 1)

    return {
        "p25": percentile(25),
        "p50": percentile(50),
        "p75": percentile(75),
        "p90": percentile(90),
        "min": round(vals[0], 1),
        "max": round(vals[-1], 1),
        "count": n,
    }


def get_skill_combinations():
    """
    Find the most common skill pairs — which skills appear together most.
    Useful for: 'If you know SQL, also learn...'
    """
    conn = get_conn()

    # Get skill pairs per job
    rows = conn.execute("""
        SELECT a.skill as skill1, b.skill as skill2, COUNT(*) as co_count
        FROM job_skills a
        JOIN job_skills b ON a.job_id = b.job_id AND a.skill < b.skill
        GROUP BY a.skill, b.skill
        HAVING co_count >= 5
        ORDER BY co_count DESC
        LIMIT 30
    """).fetchall()
    conn.close()

    return [{"skill1": r[0], "skill2": r[1], "co_occurrences": r[2]} for r in rows]


# ── Run all aggregations ──────────────────────────────────────────────────────

def run_all_analytics():
    print("Running full analytics refresh...")
    compute_weekly_skill_trends()
    compute_weekly_company_stats()
    compute_weekly_city_stats()
    print("✓ All analytics complete")


if __name__ == "__main__":
    run_all_analytics()

    # Preview velocity
    velocity = get_skill_velocity(10)
    print("\n--- Skill Velocity (top risers) ---")
    for v in velocity[:5]:
        print(f"  {v['skill']}: {v['velocity_pct']:+.1f}%  [{v['trend']}]")

    # Preview salary percentiles
    pct = get_salary_percentiles()
    print(f"\n--- Salary Percentiles ---")
    print(f"  P25: ₹{pct.get('p25')}L  |  P50: ₹{pct.get('p50')}L  |  P75: ₹{pct.get('p75')}L  |  P90: ₹{pct.get('p90')}L")
