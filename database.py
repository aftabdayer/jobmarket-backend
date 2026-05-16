"""
Production database setup — works both locally and on Railway.
On Railway: uses /tmp/jobmarket.db (ephemeral but fine for demo)
Locally: uses ../data/jobmarket.db
"""
import os, sqlite3

def get_db_path() -> str:
    # Railway / production: use /tmp
    if os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RENDER"):
        return "/tmp/jobmarket.db"
    # Local dev: use data/ folder next to backend/
    base = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base, "..", "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "jobmarket.db")

DB_PATH = get_db_path()

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn

def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
            job_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            company     TEXT,
            location    TEXT,
            city        TEXT,
            salary_min  REAL,
            salary_max  REAL,
            salary_text TEXT,
            experience  TEXT,
            job_type    TEXT DEFAULT 'Full-time',
            source      TEXT,
            url         TEXT,
            posted_date TEXT,
            description TEXT,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(title, company, posted_date)
        );

        CREATE TABLE IF NOT EXISTS job_skills (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id   INTEGER REFERENCES jobs(job_id) ON DELETE CASCADE,
            skill    TEXT NOT NULL,
            category TEXT DEFAULT 'technical',
            UNIQUE(job_id, skill)
        );

        CREATE TABLE IF NOT EXISTS skill_trends (
            skill       TEXT,
            week        TEXT,
            count       INTEGER,
            pct_of_jobs REAL,
            avg_salary  REAL,
            PRIMARY KEY (skill, week)
        );

        CREATE TABLE IF NOT EXISTS company_stats (
            company    TEXT,
            week       TEXT,
            job_count  INTEGER,
            avg_salary REAL,
            top_skills TEXT,
            PRIMARY KEY (company, week)
        );

        CREATE TABLE IF NOT EXISTS city_stats (
            city       TEXT,
            week       TEXT,
            job_count  INTEGER,
            avg_salary REAL,
            top_roles  TEXT,
            PRIMARY KEY (city, week)
        );

        CREATE TABLE IF NOT EXISTS chat_sessions (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role       TEXT NOT NULL,
            message    TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_jobs_city   ON jobs(city);
        CREATE INDEX IF NOT EXISTS idx_jobs_title  ON jobs(title);
        CREATE INDEX IF NOT EXISTS idx_jobs_date   ON jobs(posted_date);
        CREATE INDEX IF NOT EXISTS idx_skills_job  ON job_skills(job_id);
        CREATE INDEX IF NOT EXISTS idx_skills_name ON job_skills(skill);
    """)
    conn.commit()
    conn.close()
    print(f"Database initialised at: {DB_PATH}")
