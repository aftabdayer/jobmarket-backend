"""
Job Market Intelligence Engine — Streamlit Dashboard
=====================================================
Run with:
    streamlit run dashboard.py

Make sure the FastAPI backend is running on port 8000 first:
    uvicorn main:app --reload --port 8000
"""

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time

# ── Config ────────────────────────────────────────────────────────────────────
API = "http://localhost:8000"
st.set_page_config(
    page_title="Job Market Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'Space Grotesk', sans-serif;
    }
    .main { background: #0a0f1e; }
    .stApp { background: #0a0f1e; }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: #0d1528 !important;
        border-right: 1px solid #1e3a5f;
    }

    /* KPI Cards */
    .kpi-card {
        background: linear-gradient(135deg, #0d1f3c 0%, #0a1628 100%);
        border: 1px solid #1e3a5f;
        border-radius: 12px;
        padding: 20px 24px;
        text-align: center;
        transition: border-color 0.2s;
    }
    .kpi-card:hover { border-color: #00d4ff; }
    .kpi-value {
        font-size: 2.2rem;
        font-weight: 700;
        color: #00d4ff;
        line-height: 1;
        font-family: 'JetBrains Mono', monospace;
    }
    .kpi-label {
        font-size: 0.75rem;
        color: #6b8cae;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-top: 8px;
    }

    /* Section headers */
    .section-header {
        font-size: 1.1rem;
        font-weight: 600;
        color: #e2e8f0;
        border-left: 3px solid #00d4ff;
        padding-left: 12px;
        margin-bottom: 16px;
    }

    /* Chat bubbles */
    .chat-user {
        background: #1e3a5f;
        border-radius: 16px 16px 4px 16px;
        padding: 12px 16px;
        margin: 8px 0;
        color: #e2e8f0;
        max-width: 80%;
        margin-left: auto;
        font-size: 0.9rem;
    }
    .chat-bot {
        background: #0d1f3c;
        border: 1px solid #1e3a5f;
        border-radius: 16px 16px 16px 4px;
        padding: 12px 16px;
        margin: 8px 0;
        color: #e2e8f0;
        max-width: 85%;
        font-size: 0.9rem;
    }
    .chat-label-user { color: #00d4ff; font-size: 0.7rem; text-align: right; margin-bottom: 4px; }
    .chat-label-bot  { color: #6b8cae; font-size: 0.7rem; margin-bottom: 4px; }

    /* Rising / Falling badges */
    .badge-rising  { background: #0d3320; color: #4ade80; padding: 2px 10px; border-radius: 99px; font-size: 0.75rem; font-weight: 600; }
    .badge-falling { background: #3b0d0d; color: #f87171; padding: 2px 10px; border-radius: 99px; font-size: 0.75rem; font-weight: 600; }
    .badge-stable  { background: #1a1a2e; color: #94a3b8; padding: 2px 10px; border-radius: 99px; font-size: 0.75rem; }

    /* Plotly chart dark override */
    .js-plotly-plot { border-radius: 12px; }

    /* Hide streamlit extras */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

PLOTLY_THEME = dict(
    paper_bgcolor="rgba(13,21,40,0)",
    plot_bgcolor="rgba(13,21,40,0)",
    font_color="#94a3b8",
    font_family="Space Grotesk",
    colorway=["#00d4ff", "#7c3aed", "#f59e0b", "#10b981", "#f43f5e",
               "#3b82f6", "#a78bfa", "#34d399", "#fb923c", "#e879f9"],
)


# ── API helpers ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def fetch(endpoint, params=None):
    try:
        r = requests.get(f"{API}{endpoint}", params=params, timeout=8)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error ({endpoint}): {e}")
        return None


def post_chat(message, session_id):
    try:
        r = requests.post(f"{API}/api/chat",
                          json={"message": message, "session_id": session_id},
                          timeout=20)
        r.raise_for_status()
        return r.json().get("reply", "No response.")
    except Exception as e:
        return f"Connection error: {e}"


# ── Sidebar navigation ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
        <div style='padding: 16px 0 24px 0;'>
            <div style='font-size: 1.3rem; font-weight: 700; color: #00d4ff;'>📊 JobMarket AI</div>
            <div style='font-size: 0.7rem; color: #4a6fa5; margin-top: 4px;'>India Data Analytics Intelligence</div>
        </div>
    """, unsafe_allow_html=True)

    page = st.radio(
        "Navigate",
        ["🏠 Overview", "📈 Skills", "🏙️ Cities", "🏢 Companies",
         "💰 Salaries", "📉 Trends", "🔍 Job Search", "🤖 AI Analyst"],
        label_visibility="collapsed"
    )

    st.markdown("---")
    st.markdown("<div style='font-size:0.7rem; color:#4a6fa5;'>Data refreshes every 60 seconds</div>",
                unsafe_allow_html=True)

    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # Quick health check
    try:
        h = requests.get(f"{API}/health", timeout=3).json()
        st.markdown(f"""
            <div style='margin-top:16px; padding:10px; background:#0d1f3c;
                        border-radius:8px; border:1px solid #1e3a5f; font-size:0.7rem;'>
                <span style='color:#4ade80;'>● LIVE</span>
                <span style='color:#6b8cae; margin-left:8px;'>{h.get('jobs_in_db',0):,} jobs</span>
            </div>
        """, unsafe_allow_html=True)
    except Exception:
        st.markdown("<div style='margin-top:16px; padding:10px; background:#3b0d0d; border-radius:8px; font-size:0.7rem; color:#f87171;'>● Backend offline — start uvicorn</div>",
                    unsafe_allow_html=True)


# ── Page: Overview ────────────────────────────────────────────────────────────
if page == "🏠 Overview":
    st.markdown("## 🏠 Market Overview")

    summary = fetch("/api/summary")
    if summary:
        cols = st.columns(6)
        kpis = [
            (summary.get("total_jobs", 0), "Total Jobs"),
            (summary.get("companies_hiring", 0), "Companies Hiring"),
            (summary.get("cities", 0), "Active Cities"),
            (summary.get("unique_skills", 0), "Unique Skills"),
            (f"₹{summary.get('avg_salary_lpa', 0)}L", "Avg Salary"),
            (summary.get("posted_this_week", 0), "Posted This Week"),
        ]
        for col, (val, label) in zip(cols, kpis):
            with col:
                st.markdown(f"""
                    <div class="kpi-card">
                        <div class="kpi-value">{val}</div>
                        <div class="kpi-label">{label}</div>
                    </div>
                """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="section-header">Top 15 In-Demand Skills</div>', unsafe_allow_html=True)
        skills = fetch("/api/skills/top", {"limit": 15})
        if skills:
            df = pd.DataFrame(skills)
            fig = px.bar(df, x="job_count", y="skill",
                         orientation="h",
                         color="pct",
                         color_continuous_scale=["#1e3a5f", "#00d4ff"],
                         labels={"job_count": "Jobs", "skill": "", "pct": "% of jobs"})
            fig.update_layout(**PLOTLY_THEME, height=420,
                              margin=dict(l=0, r=0, t=10, b=0),
                              coloraxis_showscale=False,
                              yaxis=dict(categoryorder="total ascending"))
            fig.update_traces(marker_line_width=0)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown('<div class="section-header">Jobs by City</div>', unsafe_allow_html=True)
        cities = fetch("/api/cities", {"limit": 10})
        if cities:
            df = pd.DataFrame(cities)
            fig = px.treemap(df, path=["city"], values="jobs",
                             color="avg_salary",
                             color_continuous_scale=["#0d1f3c", "#7c3aed", "#00d4ff"],
                             labels={"avg_salary": "Avg ₹L"})
            fig.update_layout(**PLOTLY_THEME, height=420,
                              margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig, use_container_width=True)

    # Weekly trend at bottom
    st.markdown('<div class="section-header">Weekly Job Posting Volume</div>', unsafe_allow_html=True)
    trend = fetch("/api/trends/weekly", {"weeks": 12})
    if trend:
        df = pd.DataFrame(trend)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["week"], y=df["jobs"],
            mode="lines+markers",
            fill="tozeroy",
            fillcolor="rgba(0,212,255,0.08)",
            line=dict(color="#00d4ff", width=2.5),
            marker=dict(size=6, color="#00d4ff"),
        ))
        fig.update_layout(**PLOTLY_THEME, height=220,
                          margin=dict(l=0, r=0, t=10, b=0),
                          xaxis=dict(showgrid=False),
                          yaxis=dict(gridcolor="#0d1f3c"))
        st.plotly_chart(fig, use_container_width=True)


# ── Page: Skills ──────────────────────────────────────────────────────────────
elif page == "📈 Skills":
    st.markdown("## 📈 Skills Intelligence")

    tab1, tab2, tab3, tab4 = st.tabs(["Top Skills", "By Salary", "Velocity", "Combinations"])

    with tab1:
        col1, col2 = st.columns([3, 1])
        with col2:
            category = st.selectbox("Filter by category",
                                    ["All", "technical", "tool", "domain", "soft"])
        params = {"limit": 25}
        if category != "All":
            params["category"] = category

        skills = fetch("/api/skills/top", params)
        if skills:
            df = pd.DataFrame(skills)
            fig = px.bar(df, x="skill", y="job_count",
                         color="avg_salary",
                         color_continuous_scale=["#1e3a5f", "#7c3aed", "#00d4ff"],
                         labels={"job_count": "Job Mentions", "avg_salary": "Avg ₹L"})
            fig.update_layout(**PLOTLY_THEME, height=420,
                              margin=dict(l=0, r=0, t=10, b=0),
                              xaxis_tickangle=-35)
            st.plotly_chart(fig, use_container_width=True)

            # Skill categories donut
            cats = fetch("/api/skills/categories")
            if cats:
                df_c = pd.DataFrame(cats)
                fig2 = px.pie(df_c, names="category", values="total_mentions",
                              hole=0.6,
                              color_discrete_sequence=["#00d4ff", "#7c3aed", "#f59e0b", "#10b981"])
                fig2.update_layout(**PLOTLY_THEME, height=300,
                                   margin=dict(l=0, r=0, t=10, b=0))
                st.plotly_chart(fig2, use_container_width=True)

    with tab2:
        salary_skills = fetch("/api/skills/salary", {"limit": 20})
        if salary_skills:
            df = pd.DataFrame(salary_skills)
            fig = go.Figure()
            fig.add_trace(go.Bar(name="Min", x=df["skill"], y=df["min"],
                                 marker_color="#1e3a5f"))
            fig.add_trace(go.Bar(name="Avg", x=df["skill"], y=df["avg"],
                                 marker_color="#00d4ff"))
            fig.add_trace(go.Bar(name="Max", x=df["skill"], y=df["max"],
                                 marker_color="#7c3aed"))
            fig.update_layout(**PLOTLY_THEME, barmode="group", height=420,
                              margin=dict(l=0, r=0, t=10, b=0),
                              xaxis_tickangle=-35,
                              yaxis_title="Salary (LPA)")
            st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.markdown("**Skill velocity: rising vs falling demand over last 4 weeks**")
        velocity = fetch("/api/skills/velocity", {"top_n": 25})
        if velocity:
            df = pd.DataFrame(velocity)
            df_sorted = df.sort_values("velocity_pct", ascending=True)
            colors = ["#4ade80" if v > 10 else "#f87171" if v < -10 else "#94a3b8"
                      for v in df_sorted["velocity_pct"]]
            fig = go.Figure(go.Bar(
                x=df_sorted["velocity_pct"],
                y=df_sorted["skill"],
                orientation="h",
                marker_color=colors,
                text=[f"{v:+.1f}%" for v in df_sorted["velocity_pct"]],
                textposition="outside",
            ))
            fig.update_layout(**PLOTLY_THEME, height=520,
                              margin=dict(l=0, r=80, t=10, b=0),
                              xaxis_title="Velocity (%)",
                              xaxis_zeroline=True,
                              xaxis_zerolinecolor="#1e3a5f")
            st.plotly_chart(fig, use_container_width=True)

    with tab4:
        st.markdown("**Skills that appear together most often in job postings**")
        combos = fetch("/api/skills/combinations")
        if combos:
            df = pd.DataFrame(combos)
            df["pair"] = df["skill1"] + " + " + df["skill2"]
            df = df.head(20)
            fig = px.bar(df, x="co_occurrences", y="pair",
                         orientation="h",
                         color="co_occurrences",
                         color_continuous_scale=["#0d1f3c", "#7c3aed"])
            fig.update_layout(**PLOTLY_THEME, height=520,
                              margin=dict(l=0, r=0, t=10, b=0),
                              yaxis=dict(categoryorder="total ascending"),
                              coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)


# ── Page: Cities ──────────────────────────────────────────────────────────────
elif page == "🏙️ Cities":
    st.markdown("## 🏙️ City Intelligence")

    cities = fetch("/api/cities", {"limit": 15})
    if cities:
        df = pd.DataFrame(cities)

        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(df, x="city", y="jobs",
                         color="avg_salary",
                         color_continuous_scale=["#1e3a5f", "#00d4ff"],
                         labels={"avg_salary": "Avg ₹L"})
            fig.update_layout(**PLOTLY_THEME, height=380,
                              margin=dict(l=0, r=0, t=10, b=0),
                              xaxis_tickangle=-30,
                              title_text="Jobs by City")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig2 = px.scatter(df, x="jobs", y="avg_salary",
                              size="jobs", text="city",
                              color="avg_salary",
                              color_continuous_scale=["#7c3aed", "#00d4ff"],
                              labels={"jobs": "Job Count", "avg_salary": "Avg Salary (LPA)"})
            fig2.update_traces(textposition="top center", textfont_size=9)
            fig2.update_layout(**PLOTLY_THEME, height=380,
                               margin=dict(l=0, r=0, t=10, b=30),
                               title_text="Salary vs Demand Bubble Chart",
                               coloraxis_showscale=False)
            st.plotly_chart(fig2, use_container_width=True)

        # City drill-down
        st.markdown("---")
        st.markdown("### 🔍 City Drill-down")
        selected_city = st.selectbox("Select a city", [c["city"] for c in cities])
        city_skills = fetch(f"/api/cities/{selected_city}/skills", {"limit": 12})
        if city_skills and city_skills.get("top_skills"):
            df_cs = pd.DataFrame(city_skills["top_skills"])
            fig3 = px.pie(df_cs, names="skill", values="count",
                          hole=0.5,
                          title=f"Top Skills in {selected_city}")
            fig3.update_layout(**PLOTLY_THEME, height=360,
                               margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig3, use_container_width=True)


# ── Page: Companies ───────────────────────────────────────────────────────────
elif page == "🏢 Companies":
    st.markdown("## 🏢 Company Hiring Intelligence")

    companies = fetch("/api/companies", {"limit": 25})
    if companies:
        df = pd.DataFrame(companies)

        col1, col2 = st.columns(2)
        with col1:
            top15 = df.head(15)
            fig = px.bar(top15, x="open_roles", y="company",
                         orientation="h",
                         color="avg_salary",
                         color_continuous_scale=["#1e3a5f", "#00d4ff"],
                         labels={"avg_salary": "Avg ₹L"})
            fig.update_layout(**PLOTLY_THEME, height=480,
                              margin=dict(l=0, r=0, t=10, b=0),
                              yaxis=dict(categoryorder="total ascending"),
                              coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig2 = px.scatter(df, x="open_roles", y="avg_salary",
                              size="open_roles", text="company",
                              color="avg_salary",
                              color_continuous_scale=["#7c3aed", "#00d4ff"])
            fig2.update_traces(textposition="top center", textfont_size=8)
            fig2.update_layout(**PLOTLY_THEME, height=480,
                               margin=dict(l=0, r=0, t=10, b=0),
                               xaxis_title="Open Roles",
                               yaxis_title="Avg Salary (LPA)",
                               coloraxis_showscale=False)
            st.plotly_chart(fig2, use_container_width=True)

        # Table
        st.markdown("### Company Details")
        display_df = df[["company", "open_roles", "avg_salary", "latest"]].copy()
        display_df.columns = ["Company", "Open Roles", "Avg Salary (LPA)", "Latest Posting"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)


# ── Page: Salaries ────────────────────────────────────────────────────────────
elif page == "💰 Salaries":
    st.markdown("## 💰 Salary Intelligence")

    col1, col2 = st.columns(2)

    with col1:
        # Percentiles
        pct = fetch("/api/salary/percentiles")
        if pct:
            st.markdown('<div class="section-header">Salary Percentiles (All Roles)</div>', unsafe_allow_html=True)
            p_cols = st.columns(4)
            for col, (label, key) in zip(p_cols, [("P25", "p25"), ("P50 Median", "p50"), ("P75", "p75"), ("P90 Top", "p90")]):
                with col:
                    st.markdown(f"""
                        <div class="kpi-card">
                            <div class="kpi-value" style="font-size:1.5rem">₹{pct.get(key,'?')}L</div>
                            <div class="kpi-label">{label}</div>
                        </div>
                    """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Distribution
        dist = fetch("/api/salary/distribution")
        if dist:
            df = pd.DataFrame(dist)
            fig = px.bar(df, x="bracket", y="count",
                         color="count",
                         color_continuous_scale=["#1e3a5f", "#7c3aed", "#00d4ff"],
                         labels={"count": "Jobs", "bracket": "Salary Range"})
            fig.update_layout(**PLOTLY_THEME, height=320,
                              margin=dict(l=0, r=0, t=10, b=0),
                              coloraxis_showscale=False,
                              title_text="Salary Distribution")
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Salary by title
        by_title = fetch("/api/salary/by-title")
        if by_title:
            df = pd.DataFrame(by_title)
            fig = go.Figure()
            fig.add_trace(go.Bar(name="Min", x=df["title"], y=df["min"],
                                 marker_color="#0d1f3c"))
            fig.add_trace(go.Bar(name="Avg", x=df["title"], y=df["avg"],
                                 marker_color="#00d4ff"))
            fig.add_trace(go.Bar(name="Max", x=df["title"], y=df["max"],
                                 marker_color="#7c3aed"))
            fig.update_layout(**PLOTLY_THEME, barmode="group", height=420,
                              margin=dict(l=0, r=0, t=10, b=0),
                              xaxis_tickangle=-30,
                              yaxis_title="LPA",
                              title_text="Salary Range by Job Title")
            st.plotly_chart(fig, use_container_width=True)

    # Salary by skill full-width
    st.markdown("---")
    salary_skills = fetch("/api/skills/salary", {"limit": 20})
    if salary_skills:
        df = pd.DataFrame(salary_skills)
        fig = px.scatter(df, x="jobs", y="avg",
                         size="jobs", text="skill",
                         color="avg",
                         color_continuous_scale=["#7c3aed", "#00d4ff"],
                         labels={"jobs": "Job Demand", "avg": "Avg Salary (LPA)"},
                         title="Skill: Demand vs Salary (Bubble = Volume)")
        fig.update_traces(textposition="top center", textfont_size=9)
        fig.update_layout(**PLOTLY_THEME, height=420,
                          margin=dict(l=0, r=0, t=40, b=0),
                          coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)


# ── Page: Trends ──────────────────────────────────────────────────────────────
elif page == "📉 Trends":
    st.markdown("## 📉 Market Trends")

    col1, col2 = st.columns([2, 1])
    with col2:
        weeks = st.slider("Time window (weeks)", 4, 24, 12)

    # Weekly volume
    trend = fetch("/api/trends/weekly", {"weeks": weeks})
    if trend:
        df = pd.DataFrame(trend)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["week"], y=df["jobs"],
            mode="lines+markers",
            fill="tozeroy",
            fillcolor="rgba(0,212,255,0.07)",
            line=dict(color="#00d4ff", width=2.5),
            marker=dict(size=6),
            name="Jobs Posted"
        ))
        fig.update_layout(**PLOTLY_THEME, height=260,
                          margin=dict(l=0, r=0, t=10, b=0),
                          xaxis=dict(showgrid=False),
                          yaxis=dict(gridcolor="#0d1f3c"),
                          title_text="Weekly Job Posting Volume")
        st.plotly_chart(fig, use_container_width=True)

    # Multi-skill compare
    st.markdown("---")
    st.markdown("### Compare Skills Over Time")
    default_skills = "Python,SQL,Power BI,Tableau,Excel"
    skills_input = st.text_input("Enter skills (comma-separated)", value=default_skills)

    compare_data = fetch("/api/trends/compare", {"skills": skills_input, "weeks": weeks})
    if compare_data:
        fig2 = go.Figure()
        colors = ["#00d4ff", "#7c3aed", "#f59e0b", "#10b981", "#f43f5e",
                  "#3b82f6", "#a78bfa", "#34d399"]
        for i, (skill, data) in enumerate(compare_data.items()):
            if data:
                df_s = pd.DataFrame(data)
                fig2.add_trace(go.Scatter(
                    x=df_s["week"], y=df_s["mentions"],
                    mode="lines+markers",
                    name=skill,
                    line=dict(color=colors[i % len(colors)], width=2),
                    marker=dict(size=5),
                ))
        fig2.update_layout(**PLOTLY_THEME, height=380,
                           margin=dict(l=0, r=0, t=10, b=0),
                           xaxis=dict(showgrid=False),
                           yaxis=dict(gridcolor="#0d1f3c", title="Mentions"),
                           legend=dict(bgcolor="rgba(0,0,0,0)"))
        st.plotly_chart(fig2, use_container_width=True)


# ── Page: Job Search ──────────────────────────────────────────────────────────
elif page == "🔍 Job Search":
    st.markdown("## 🔍 Job Search")

    col1, col2, col3, col4 = st.columns(4)
    with col1: q = st.text_input("Keyword", placeholder="data analyst")
    with col2: city = st.text_input("City", placeholder="Bangalore")
    with col3: company = st.text_input("Company", placeholder="Infosys")
    with col4: skill = st.text_input("Must-have Skill", placeholder="Python")

    params = {}
    if q: params["q"] = q
    if city: params["city"] = city
    if company: params["company"] = company
    if skill: params["skill"] = skill
    params["limit"] = 100

    jobs = fetch("/api/jobs", params)
    if jobs:
        st.markdown(f"**{len(jobs)} jobs found**")
        df = pd.DataFrame(jobs)
        display_cols = ["title", "company", "city", "salary_text", "experience", "posted_date", "source"]
        display_cols = [c for c in display_cols if c in df.columns]
        df_display = df[display_cols].copy()
        df_display.columns = [c.replace("_", " ").title() for c in display_cols]
        st.dataframe(df_display, use_container_width=True, hide_index=True, height=500)
    elif jobs is not None:
        st.info("No jobs found for those filters. Try broader search terms.")


# ── Page: AI Analyst ─────────────────────────────────────────────────────────
elif page == "🤖 AI Analyst":
    st.markdown("## 🤖 AI Job Market Analyst")
    st.markdown("*Powered by Groq + Llama 3 — answers based on your live job database*")

    # Session init
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "session_id" not in st.session_state:
        st.session_state.session_id = f"session_{int(time.time())}"

    # Suggested questions
    st.markdown("**Quick questions:**")
    q_cols = st.columns(3)
    suggestions = [
        "What skills should I learn to get hired?",
        "Which city pays the most for data analysts?",
        "What's a realistic salary for a fresher?",
        "Which companies are hiring the most?",
        "Is Python or SQL more in demand?",
        "What skill combinations appear most in jobs?",
    ]
    for i, suggestion in enumerate(suggestions):
        with q_cols[i % 3]:
            if st.button(suggestion, key=f"sug_{i}", use_container_width=True):
                st.session_state.chat_history.append({"role": "user", "content": suggestion})
                with st.spinner("Analysing market data..."):
                    reply = post_chat(suggestion, st.session_state.session_id)
                st.session_state.chat_history.append({"role": "assistant", "content": reply})

    st.markdown("---")

    # Chat history
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                st.markdown(f"""
                    <div class="chat-label-user">You</div>
                    <div class="chat-user">{msg['content']}</div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                    <div class="chat-label-bot">🤖 AI Analyst</div>
                    <div class="chat-bot">{msg['content']}</div>
                """, unsafe_allow_html=True)

    # Input
    st.markdown("<br>", unsafe_allow_html=True)
    with st.form("chat_form", clear_on_submit=True):
        col_input, col_send = st.columns([5, 1])
        with col_input:
            user_input = st.text_input("Ask anything about the job market...",
                                       label_visibility="collapsed",
                                       placeholder="e.g. What skills should I focus on to get a 15 LPA job?")
        with col_send:
            send = st.form_submit_button("Send →", use_container_width=True)

    if send and user_input.strip():
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.spinner("Analysing..."):
            reply = post_chat(user_input, st.session_state.session_id)
        st.session_state.chat_history.append({"role": "assistant", "content": reply})
        st.rerun()

    if st.button("🗑 Clear Chat", type="secondary"):
        st.session_state.chat_history = []
        st.rerun()
