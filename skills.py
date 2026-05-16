"""
Job Market Intelligence Engine — Skill Extraction
==================================================
Extracts and categorises skills from job descriptions using
keyword matching + regex. No paid API needed.
"""

import re
from typing import List, Tuple

# ── Master skill dictionary ────────────────────────────────────────────────────
# Format: "canonical_skill_name": ["alias1", "alias2", ...]

SKILLS: dict[str, dict] = {

    # ── Data & Analytics tools ────────────────────────────────────────────────
    "SQL":              {"cat": "technical", "aliases": ["sql", "mysql", "postgresql", "sqlite", "t-sql", "pl/sql", "nosql"]},
    "Python":           {"cat": "technical", "aliases": ["python", "python3", "py"]},
    "R":                {"cat": "technical", "aliases": [r"\br\b", "r language", "r programming"]},
    "Excel":            {"cat": "tool",      "aliases": ["excel", "ms excel", "microsoft excel", "advanced excel"]},
    "Power BI":         {"cat": "tool",      "aliases": ["power bi", "powerbi", "pbi", "power_bi"]},
    "Tableau":          {"cat": "tool",      "aliases": ["tableau"]},
    "Looker":           {"cat": "tool",      "aliases": ["looker", "looker studio", "google data studio"]},
    "Qlik":             {"cat": "tool",      "aliases": ["qlik", "qlikview", "qliksense"]},
    "Metabase":         {"cat": "tool",      "aliases": ["metabase"]},
    "Superset":         {"cat": "tool",      "aliases": ["apache superset", "superset"]},

    # ── Python libraries ──────────────────────────────────────────────────────
    "Pandas":           {"cat": "technical", "aliases": ["pandas"]},
    "NumPy":            {"cat": "technical", "aliases": ["numpy", "np"]},
    "Matplotlib":       {"cat": "technical", "aliases": ["matplotlib", "seaborn", "plotly"]},
    "Scikit-learn":     {"cat": "technical", "aliases": ["scikit-learn", "sklearn", "scikit learn"]},
    "TensorFlow":       {"cat": "technical", "aliases": ["tensorflow", "tf"]},
    "PyTorch":          {"cat": "technical", "aliases": ["pytorch", "torch"]},
    "Keras":            {"cat": "technical", "aliases": ["keras"]},
    "Streamlit":        {"cat": "tool",      "aliases": ["streamlit"]},
    "FastAPI":          {"cat": "technical", "aliases": ["fastapi", "fast api"]},
    "Flask":            {"cat": "technical", "aliases": ["flask"]},
    "Django":           {"cat": "technical", "aliases": ["django"]},

    # ── Machine Learning ──────────────────────────────────────────────────────
    "Machine Learning": {"cat": "technical", "aliases": ["machine learning", "ml", "supervised learning", "unsupervised learning"]},
    "Deep Learning":    {"cat": "technical", "aliases": ["deep learning", "dl", "neural network", "neural networks", "ann", "cnn", "rnn", "lstm"]},
    "NLP":              {"cat": "technical", "aliases": ["nlp", "natural language processing", "text analytics", "text mining"]},
    "Computer Vision":  {"cat": "technical", "aliases": ["computer vision", "image processing", "opencv", "object detection"]},
    "Generative AI":    {"cat": "technical", "aliases": ["generative ai", "gen ai", "genai", "llm", "large language model", "gpt", "chatgpt", "openai", "langchain", "rag", "retrieval augmented"]},
    "MLOps":            {"cat": "technical", "aliases": ["mlops", "ml pipeline", "model deployment", "model monitoring"]},
    "Time Series":      {"cat": "technical", "aliases": ["time series", "time-series", "forecasting", "arima", "prophet"]},

    # ── Cloud & Infrastructure ────────────────────────────────────────────────
    "AWS":              {"cat": "tool",      "aliases": ["aws", "amazon web services", "s3", "ec2", "redshift", "athena", "sagemaker"]},
    "Azure":            {"cat": "tool",      "aliases": ["azure", "microsoft azure", "azure synapse", "azure databricks"]},
    "GCP":              {"cat": "tool",      "aliases": ["gcp", "google cloud", "bigquery", "google bigquery", "dataflow"]},
    "Databricks":       {"cat": "tool",      "aliases": ["databricks"]},
    "Snowflake":        {"cat": "tool",      "aliases": ["snowflake"]},
    "Hadoop":           {"cat": "tool",      "aliases": ["hadoop", "hdfs", "mapreduce", "hive", "pig"]},
    "Spark":            {"cat": "tool",      "aliases": ["spark", "apache spark", "pyspark"]},
    "Kafka":            {"cat": "tool",      "aliases": ["kafka", "apache kafka"]},
    "Airflow":          {"cat": "tool",      "aliases": ["airflow", "apache airflow"]},

    # ── Databases ─────────────────────────────────────────────────────────────
    "MongoDB":          {"cat": "tool",      "aliases": ["mongodb", "mongo"]},
    "Redis":            {"cat": "tool",      "aliases": ["redis"]},
    "Elasticsearch":    {"cat": "tool",      "aliases": ["elasticsearch", "elastic search", "kibana"]},
    "PostgreSQL":       {"cat": "tool",      "aliases": ["postgresql", "postgres"]},
    "MySQL":            {"cat": "tool",      "aliases": ["mysql"]},

    # ── Dev tools ─────────────────────────────────────────────────────────────
    "Git":              {"cat": "tool",      "aliases": ["git", "github", "gitlab", "version control"]},
    "Docker":           {"cat": "tool",      "aliases": ["docker", "dockerfile", "containerisation", "containerization"]},
    "Kubernetes":       {"cat": "tool",      "aliases": ["kubernetes", "k8s"]},
    "Linux":            {"cat": "tool",      "aliases": ["linux", "unix", "bash", "shell scripting"]},
    "REST API":         {"cat": "technical", "aliases": ["rest api", "restful", "api integration", "api development"]},

    # ── Statistics & Analytics concepts ───────────────────────────────────────
    "Statistics":       {"cat": "technical", "aliases": ["statistics", "statistical analysis", "hypothesis testing", "a/b testing", "regression", "clustering", "classification"]},
    "EDA":              {"cat": "technical", "aliases": ["eda", "exploratory data analysis", "data exploration"]},
    "ETL":              {"cat": "technical", "aliases": ["etl", "data pipeline", "data ingestion", "data wrangling", "data transformation"]},
    "Data Modeling":    {"cat": "technical", "aliases": ["data modeling", "data modelling", "star schema", "dimensional modeling", "data warehouse"]},
    "BI & Reporting":   {"cat": "domain",    "aliases": ["business intelligence", "bi", "kpi", "dashboard", "reporting", "data visualisation", "data visualization"]},

    # ── Domain knowledge ──────────────────────────────────────────────────────
    "Finance Analytics":     {"cat": "domain", "aliases": ["financial analytics", "financial analysis", "fintech", "banking analytics", "risk analytics"]},
    "Marketing Analytics":   {"cat": "domain", "aliases": ["marketing analytics", "digital marketing", "growth analytics", "campaign analytics"]},
    "Supply Chain Analytics":{"cat": "domain", "aliases": ["supply chain", "logistics analytics", "inventory analytics", "demand forecasting"]},
    "Healthcare Analytics":  {"cat": "domain", "aliases": ["healthcare analytics", "clinical analytics", "pharma analytics", "health data"]},
    "E-commerce Analytics":  {"cat": "domain", "aliases": ["e-commerce analytics", "ecommerce", "retail analytics", "product analytics"]},

    # ── Soft skills ───────────────────────────────────────────────────────────
    "Communication":    {"cat": "soft", "aliases": ["communication", "presentation skills", "storytelling with data", "data storytelling"]},
    "Problem Solving":  {"cat": "soft", "aliases": ["problem solving", "analytical thinking", "critical thinking"]},
    "Stakeholder Mgmt": {"cat": "soft", "aliases": ["stakeholder management", "client management", "business requirements"]},
}


def extract_skills(text: str) -> List[Tuple[str, str]]:
    """
    Extract skills from text. Returns list of (skill_name, category).
    Case-insensitive matching.
    """
    if not text:
        return []

    text_lower = text.lower()
    found = []
    seen = set()

    for skill_name, info in SKILLS.items():
        if skill_name in seen:
            continue
        for alias in info["aliases"]:
            # Use word boundary for short aliases to avoid false positives
            pattern = r'\b' + re.escape(alias) + r'\b'
            if re.search(pattern, text_lower):
                found.append((skill_name, info["cat"]))
                seen.add(skill_name)
                break

    return found


def parse_salary(salary_text: str) -> Tuple[float | None, float | None]:
    """
    Parse salary text like '6-12 LPA', '₹8,00,000 - ₹15,00,000',
    '10 LPA', '15-20 lakhs' into (min, max) in LPA (lakhs per annum).
    Returns (None, None) if unparseable.
    """
    if not salary_text:
        return None, None

    text = salary_text.lower().replace(",", "").replace("₹", "").replace("rs.", "").strip()

    # Pattern: X-Y LPA or X to Y LPA
    m = re.search(r'(\d+\.?\d*)\s*[-–to]+\s*(\d+\.?\d*)\s*(lpa|lakhs?|l\.p\.a)', text)
    if m:
        return float(m.group(1)), float(m.group(2))

    # Single value: X LPA
    m = re.search(r'(\d+\.?\d*)\s*(lpa|lakhs?|l\.p\.a)', text)
    if m:
        val = float(m.group(1))
        return val, val

    # Annual in full: 600000 - 1200000
    m = re.search(r'(\d{5,8})\s*[-–]\s*(\d{5,8})', text)
    if m:
        lo = float(m.group(1)) / 100000
        hi = float(m.group(2)) / 100000
        return round(lo, 1), round(hi, 1)

    return None, None


def normalise_city(city: str) -> str:
    """Standardise city names."""
    if not city:
        return ""
    city = city.strip().title()
    mapping = {
        "Bengaluru": "Bangalore",
        "Bangalore Urban": "Bangalore",
        "Mumbai Suburban": "Mumbai",
        "New Delhi": "Delhi",
        "Ncr": "Delhi NCR",
        "Delhi/ncr": "Delhi NCR",
        "Delhi Ncr": "Delhi NCR",
        "Gurgaon": "Gurugram",
    }
    return mapping.get(city, city)


if __name__ == "__main__":
    # Quick test
    test = """
    We are looking for a Data Analyst with strong Python and SQL skills.
    Experience with Power BI or Tableau required. Knowledge of machine learning,
    pandas, and scikit-learn is a plus. AWS or Azure exposure preferred.
    Good communication and stakeholder management skills needed.
    Salary: 8-15 LPA
    """
    skills = extract_skills(test)
    print("Skills found:")
    for s, c in skills:
        print(f"  {s} ({c})")

    sal = parse_salary("8-15 LPA")
    print(f"\nSalary parsed: {sal}")
