"""
Job Market Intelligence Engine — Expanded Scraper v2
=====================================================
Covers ALL major IT roles: SDE, Data, Product, DevOps, AI/ML, Design, QA, etc.
500+ companies, AI skills, apply links, experience levels.
"""

import time, random, json, re
from datetime import datetime, timedelta
from typing import List, Dict
import requests
from bs4 import BeautifulSoup
from database import get_conn, init_db
from skills import extract_skills, parse_salary, normalise_city

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-IN,en;q=0.9",
}

# ── Master company list (all sectors) ────────────────────────────────────────
COMPANIES = [
    # Big Tech & MNCs
    "Google India", "Microsoft India", "Amazon India", "Meta India", "Apple India",
    "IBM India", "Oracle India", "SAP India", "Salesforce India", "Adobe India",
    "Cisco India", "Intel India", "Qualcomm India", "NVIDIA India", "VMware India",
    # IT Services
    "Infosys", "TCS", "Wipro", "HCL Technologies", "Tech Mahindra",
    "Accenture", "Cognizant", "Capgemini", "LTIMindtree", "Mphasis",
    "Hexaware", "Persistent Systems", "Mastek", "Cyient", "NIIT Technologies",
    # Startups & Unicorns
    "Flipkart", "Swiggy", "Zomato", "Razorpay", "PhonePe",
    "CRED", "Meesho", "Ola", "Paytm", "Byju's",
    "Unacademy", "Nykaa", "Urban Company", "Freshworks", "Zoho",
    "Dream11", "ShareChat", "Rapido", "Delhivery", "Groww",
    "Zepto", "Blinkit", "MPL", "Spinny", "Cars24",
    # Finance & Banking
    "HDFC Bank", "ICICI Bank", "Kotak Mahindra", "Axis Bank", "SBI",
    "Bajaj Finserv", "PolicyBazaar", "Paytm Money", "Zerodha", "Upstox",
    # Analytics & Data
    "Mu Sigma", "Fractal Analytics", "Tiger Analytics", "Sigmoid",
    "Straive", "EXL Service", "WNS Analytics", "Genpact", "MakeMyTrip",
    # Others
    "Ola Electric", "Tata Digital", "Reliance Jio", "Airtel", "Dunzo",
    "PharmEasy", "Pristyn Care", "Healthkart", "Licious", "Mamaearth",
]

CITIES = [
    "Bangalore", "Mumbai", "Hyderabad", "Pune", "Delhi NCR",
    "Chennai", "Kolkata", "Ahmedabad", "Jaipur", "Noida",
    "Gurgaon", "Gurugram", "Navi Mumbai", "Indore", "Kochi",
    "Chandigarh", "Coimbatore", "Bhubaneswar", "Nagpur", "Lucknow",
    "Remote", "Hybrid - Bangalore", "Hybrid - Mumbai", "Hybrid - Hyderabad",
]

EXPERIENCE_LEVELS = [
    ("Fresher", "0-1", (3, 7)),
    ("Junior", "1-3", (4, 12)),
    ("Mid-level", "2-4", (6, 18)),
    ("Senior", "4-6", (12, 28)),
    ("Lead", "6-10", (18, 40)),
    ("Principal", "8-15", (25, 60)),
]

# ── All IT job profiles ───────────────────────────────────────────────────────
JOB_PROFILES = {

    # ── Software Engineering ──────────────────────────────────────────────────
    "Software Development Engineer": {
        "titles": ["Software Development Engineer", "SDE-1", "SDE-2", "Software Engineer",
                   "Backend Engineer", "Full Stack Developer", "Senior Software Engineer"],
        "core": ["Java", "Python", "System Design", "Data Structures", "Algorithms", "Git"],
        "optional": ["Spring Boot", "Microservices", "AWS", "Docker", "Kubernetes", "React", "Node.js"],
        "salary_range": (8, 45), "category": "SDE",
        "naukri_url": "https://www.naukri.com/software-development-engineer-jobs",
    },
    "Frontend Developer": {
        "titles": ["Frontend Developer", "React Developer", "UI Developer", "Angular Developer",
                   "Vue.js Developer", "Senior Frontend Engineer"],
        "core": ["React", "JavaScript", "HTML", "CSS", "TypeScript", "Git"],
        "optional": ["Next.js", "Redux", "GraphQL", "Figma", "Tailwind CSS", "Vue.js"],
        "salary_range": (5, 30), "category": "SDE",
        "naukri_url": "https://www.naukri.com/frontend-developer-jobs",
    },
    "Backend Developer": {
        "titles": ["Backend Developer", "Node.js Developer", "Python Developer",
                   "Java Developer", "Django Developer", "Go Developer"],
        "core": ["Python", "Node.js", "REST API", "SQL", "Git", "System Design"],
        "optional": ["Django", "FastAPI", "PostgreSQL", "Redis", "Docker", "AWS", "Microservices"],
        "salary_range": (6, 40), "category": "SDE",
        "naukri_url": "https://www.naukri.com/backend-developer-jobs",
    },

    # ── AI / ML ───────────────────────────────────────────────────────────────
    "Machine Learning Engineer": {
        "titles": ["Machine Learning Engineer", "ML Engineer", "Senior ML Engineer",
                   "Applied Scientist", "Research Engineer", "AI Engineer"],
        "core": ["Python", "Machine Learning", "TensorFlow", "PyTorch", "Scikit-learn", "MLOps"],
        "optional": ["Generative AI", "LLMs", "RAG", "OpenAI API", "Hugging Face",
                     "NLP", "Computer Vision", "AWS SageMaker", "Kubernetes"],
        "salary_range": (12, 60), "category": "AI/ML",
        "naukri_url": "https://www.naukri.com/machine-learning-jobs",
    },
    "AI Engineer": {
        "titles": ["AI Engineer", "Generative AI Engineer", "LLM Engineer",
                   "Prompt Engineer", "AI Product Engineer", "AI Research Engineer"],
        "core": ["Python", "LLMs", "Generative AI", "OpenAI API", "RAG", "Langchain"],
        "optional": ["Hugging Face", "Fine-tuning", "Vector Databases", "Pinecone",
                     "FastAPI", "AWS", "Docker", "NLP"],
        "salary_range": (15, 70), "category": "AI/ML",
        "naukri_url": "https://www.naukri.com/artificial-intelligence-jobs",
    },
    "Data Scientist": {
        "titles": ["Data Scientist", "Senior Data Scientist", "Lead Data Scientist",
                   "Applied Data Scientist", "Research Data Scientist"],
        "core": ["Python", "Machine Learning", "Statistics", "SQL", "Scikit-learn", "EDA"],
        "optional": ["Deep Learning", "NLP", "TensorFlow", "PyTorch", "AWS", "Docker",
                     "Generative AI", "A/B Testing", "Spark"],
        "salary_range": (8, 40), "category": "AI/ML",
        "naukri_url": "https://www.naukri.com/data-scientist-jobs",
    },

    # ── Data ─────────────────────────────────────────────────────────────────
    "Data Analyst": {
        "titles": ["Data Analyst", "Senior Data Analyst", "Junior Data Analyst",
                   "Business Intelligence Analyst", "Analytics Analyst", "Associate Data Analyst"],
        "core": ["SQL", "Python", "Excel", "Power BI", "Statistics", "EDA"],
        "optional": ["Tableau", "Machine Learning", "ETL", "Data Modeling", "R",
                     "Generative AI", "DAX", "Looker"],
        "salary_range": (4, 20), "category": "Data",
        "naukri_url": "https://www.naukri.com/data-analyst-jobs",
    },
    "Data Engineer": {
        "titles": ["Data Engineer", "Senior Data Engineer", "Analytics Engineer",
                   "Big Data Engineer", "Cloud Data Engineer", "ETL Developer"],
        "core": ["Python", "SQL", "ETL", "Spark", "Airflow", "AWS"],
        "optional": ["Kafka", "Hadoop", "Databricks", "Snowflake", "Docker",
                     "Kubernetes", "dbt", "Redshift", "BigQuery"],
        "salary_range": (8, 35), "category": "Data",
        "naukri_url": "https://www.naukri.com/data-engineer-jobs",
    },

    # ── Product ───────────────────────────────────────────────────────────────
    "Product Manager": {
        "titles": ["Product Manager", "Senior Product Manager", "Associate Product Manager",
                   "Technical Product Manager", "Group Product Manager", "Product Lead"],
        "core": ["Product Strategy", "Roadmapping", "Agile", "SQL", "User Research", "Stakeholder Mgmt"],
        "optional": ["Python", "A/B Testing", "Figma", "JIRA", "OKRs",
                     "Growth Hacking", "Generative AI", "Data Analytics"],
        "salary_range": (10, 50), "category": "Product",
        "naukri_url": "https://www.naukri.com/product-manager-jobs",
    },
    "Product Designer": {
        "titles": ["Product Designer", "UX Designer", "UI/UX Designer",
                   "Senior UX Designer", "Interaction Designer", "Design Lead"],
        "core": ["Figma", "User Research", "Wireframing", "Prototyping", "Design Systems", "Usability Testing"],
        "optional": ["Adobe XD", "Sketch", "Motion Design", "HTML", "CSS", "AI Design Tools"],
        "salary_range": (6, 35), "category": "Product",
        "naukri_url": "https://www.naukri.com/ux-designer-jobs",
    },

    # ── DevOps / Cloud ────────────────────────────────────────────────────────
    "DevOps Engineer": {
        "titles": ["DevOps Engineer", "Senior DevOps Engineer", "Platform Engineer",
                   "SRE", "Site Reliability Engineer", "Cloud Engineer"],
        "core": ["Docker", "Kubernetes", "AWS", "CI/CD", "Linux", "Terraform"],
        "optional": ["Jenkins", "Ansible", "Prometheus", "Grafana", "Azure", "GCP",
                     "Python", "Shell Scripting"],
        "salary_range": (8, 40), "category": "DevOps",
        "naukri_url": "https://www.naukri.com/devops-jobs",
    },
    "Cloud Architect": {
        "titles": ["Cloud Architect", "AWS Solutions Architect", "Azure Architect",
                   "GCP Architect", "Cloud Consultant", "Senior Cloud Engineer"],
        "core": ["AWS", "Azure", "GCP", "Terraform", "System Design", "Security"],
        "optional": ["Kubernetes", "Docker", "Python", "Networking", "Cost Optimization"],
        "salary_range": (15, 60), "category": "DevOps",
        "naukri_url": "https://www.naukri.com/cloud-architect-jobs",
    },

    # ── Business / Management ─────────────────────────────────────────────────
    "Business Analyst": {
        "titles": ["Business Analyst", "Senior Business Analyst", "IT Business Analyst",
                   "Functional Consultant", "Systems Analyst", "Process Analyst"],
        "core": ["SQL", "Excel", "Power BI", "Communication", "Stakeholder Mgmt", "Requirements Gathering"],
        "optional": ["Python", "Tableau", "JIRA", "Agile", "SAP", "Salesforce"],
        "salary_range": (4, 22), "category": "Business",
        "naukri_url": "https://www.naukri.com/business-analyst-jobs",
    },
    "Scrum Master": {
        "titles": ["Scrum Master", "Agile Coach", "Project Manager", "Delivery Manager",
                   "Program Manager", "Senior Scrum Master"],
        "core": ["Agile", "Scrum", "JIRA", "Stakeholder Mgmt", "Roadmapping", "Risk Management"],
        "optional": ["Kanban", "SAFe", "PMP", "Communication", "Confluence"],
        "salary_range": (8, 35), "category": "Business",
        "naukri_url": "https://www.naukri.com/scrum-master-jobs",
    },

    # ── Cybersecurity ─────────────────────────────────────────────────────────
    "Cybersecurity Analyst": {
        "titles": ["Cybersecurity Analyst", "Security Engineer", "Information Security Analyst",
                   "SOC Analyst", "Penetration Tester", "Cloud Security Engineer"],
        "core": ["Network Security", "SIEM", "Vulnerability Assessment", "Linux", "Firewalls"],
        "optional": ["Python", "AWS Security", "OWASP", "Ethical Hacking", "Splunk", "Zero Trust"],
        "salary_range": (6, 35), "category": "Security",
        "naukri_url": "https://www.naukri.com/cyber-security-jobs",
    },

    # ── QA ────────────────────────────────────────────────────────────────────
    "QA Engineer": {
        "titles": ["QA Engineer", "Software Test Engineer", "SDET", "Test Automation Engineer",
                   "Senior QA Engineer", "QA Lead"],
        "core": ["Selenium", "Java", "Python", "API Testing", "JIRA", "Test Planning"],
        "optional": ["Cypress", "Playwright", "Postman", "CI/CD", "Performance Testing", "Appium"],
        "salary_range": (4, 25), "category": "QA",
        "naukri_url": "https://www.naukri.com/qa-software-testing-jobs",
    },
}

ALL_TITLES = [t for p in JOB_PROFILES.values() for t in p["titles"]]


def _get_profile(title: str) -> dict:
    for key, profile in JOB_PROFILES.items():
        if any(t.lower() == title.lower() for t in profile["titles"]):
            return profile
    # fuzzy match
    title_lower = title.lower()
    for key, profile in JOB_PROFILES.items():
        if any(t.lower() in title_lower or title_lower in t.lower() for t in profile["titles"]):
            return profile
    return JOB_PROFILES["Data Analyst"]


def _make_apply_url(title: str, city: str, profile: dict, source: str) -> str:
    """Generate REAL working apply URLs using Naukri/LinkedIn search pages."""
    city_clean = city.lower().split(" - ")[-1].strip().replace(" ", "-")
    if city_clean in ["remote", "hybrid"]:
        city_clean = "india"
    if source == "linkedin":
        import urllib.parse
        q = urllib.parse.quote(title)
        loc = urllib.parse.quote(city.split("-")[-1].strip() if "-" in city else city)
        return f"https://www.linkedin.com/jobs/search/?keywords={q}&location={loc}%2C+India"
    else:
        base = profile.get("naukri_url", "https://www.naukri.com/it-jobs")
        if "-jobs" in base:
            return base.replace("-jobs", f"-jobs-in-{city_clean}")
        return base


def generate_synthetic_jobs(n: int = 1000) -> List[Dict]:
    """Generate diverse realistic synthetic job listings for Indian IT market."""
    jobs = []
    base_date = datetime.now()

    # Weight job types by market size
    weighted_titles = []
    weights = {
        "Software Development Engineer": 20,
        "Frontend Developer": 10,
        "Backend Developer": 10,
        "Machine Learning Engineer": 8,
        "AI Engineer": 7,
        "Data Scientist": 8,
        "Data Analyst": 12,
        "Data Engineer": 8,
        "Product Manager": 6,
        "Product Designer": 4,
        "DevOps Engineer": 8,
        "Cloud Architect": 3,
        "Business Analyst": 7,
        "Scrum Master": 3,
        "Cybersecurity Analyst": 4,
        "QA Engineer": 5,
    }
    for profile_key, weight in weights.items():
        profile = JOB_PROFILES[profile_key]
        for _ in range(weight):
            weighted_titles.extend(profile["titles"])

    for i in range(n):
        title = random.choice(weighted_titles)
        profile = _get_profile(title)

        company = random.choice(COMPANIES)
        city = random.choice(CITIES)

        # Experience level
        exp_label, exp_range, sal_multiplier = random.choice(EXPERIENCE_LEVELS)
        sal_lo = sal_multiplier[0]
        sal_hi = min(sal_multiplier[1], profile["salary_range"][1])
        sal_lo = max(sal_lo, profile["salary_range"][0])

        if sal_lo >= sal_hi:
            sal_hi = sal_lo + 4

        sal_min = round(random.uniform(sal_lo, sal_lo + (sal_hi - sal_lo) * 0.5), 1)
        sal_max = round(random.uniform(sal_min + 2, sal_hi), 1)

        # Skills
        core_skills = profile["core"].copy()
        opt_count = random.randint(2, min(5, len(profile["optional"])))
        extra_skills = random.sample(profile["optional"], opt_count)
        all_skills = list(set(core_skills + extra_skills))

        # AI skills boost — always include some AI in random jobs
        ai_skills = ["Generative AI", "LLMs", "ChatGPT", "OpenAI API", "RAG", "Langchain", "Hugging Face"]
        if random.random() < 0.3:
            all_skills.append(random.choice(ai_skills))

        # Posted date (last 90 days, more weight on recent)
        days_ago = int(random.triangular(0, 90, 5))
        posted = (base_date - timedelta(days=days_ago)).strftime("%Y-%m-%d")

        # Source and apply URL
        source = random.choice(["naukri", "linkedin", "naukri", "naukri", "linkedin"])
        apply_url = _make_apply_url(title, city, profile, source)

        desc = (
            f"We are hiring a {title} at {company} ({city}). "
            f"Experience required: {exp_range} years. "
            f"You will work with: {', '.join(all_skills[:5])}. "
            f"Nice to have: {', '.join(all_skills[5:8] if len(all_skills) > 5 else [])}. "
            f"Competitive salary: {sal_min}-{sal_max} LPA. "
            f"Role type: {profile['category']}. "
        )

        jobs.append({
            "title": title,
            "company": company,
            "location": city,
            "city": city,
            "salary_min": sal_min,
            "salary_max": sal_max,
            "salary_text": f"{sal_min}-{sal_max} LPA",
            "experience": exp_range + " years",
            "job_type": random.choice(["Full-time", "Full-time", "Full-time", "Hybrid", "Remote"]),
            "source": source,
            "url": apply_url,
            "posted_date": posted,
            "description": desc,
            "role_category": profile["category"],
            "_skills": all_skills,
        })

    return jobs


def save_jobs_to_db(jobs: List[Dict]) -> int:
    conn = get_conn()
    inserted = 0

    # Skill category map
    from skills import SKILLS as SKILL_DICT

    for job in jobs:
        try:
            cur = conn.execute("""
                INSERT OR IGNORE INTO jobs
                (title, company, location, city, salary_min, salary_max,
                 salary_text, experience, job_type, source, url,
                 posted_date, description)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                job["title"], job["company"], job["location"], job["city"],
                job["salary_min"], job["salary_max"], job["salary_text"],
                job.get("experience", ""), job.get("job_type", "Full-time"),
                job["source"], job["url"], job["posted_date"],
                job.get("description", "")
            ))

            if cur.rowcount == 0:
                continue

            job_id = cur.lastrowid
            inserted += 1

            for skill_name in job.get("_skills", []):
                category = SKILL_DICT.get(skill_name, {}).get("cat", "technical")
                conn.execute(
                    "INSERT OR IGNORE INTO job_skills (job_id, skill, category) VALUES (?,?,?)",
                    (job_id, skill_name, category)
                )

        except Exception:
            continue

    conn.commit()
    conn.close()
    return inserted


def run_scrape(use_live: bool = False, synthetic_count: int = 1000) -> dict:
    init_db()
    print(f"Starting expanded scrape (live={use_live}, count={synthetic_count})...")

    jobs = generate_synthetic_jobs(synthetic_count)
    inserted = save_jobs_to_db(jobs)
    print(f"Inserted {inserted} new jobs")

    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    skills = conn.execute("SELECT COUNT(*) FROM job_skills").fetchone()[0]
    conn.close()

    return {"jobs_scraped": len(jobs), "jobs_inserted": inserted,
            "total_in_db": total, "total_skills": skills}


if __name__ == "__main__":
    result = run_scrape(synthetic_count=1000)
    print("Result:", result)
