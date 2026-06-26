import os

import folium
import httpx
import streamlit as st
from streamlit_folium import st_folium

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(
    page_title="HeatVision AI — Urban Heat",
    page_icon="🌡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Premium CSS ──────────────────────────────────────────────────────────────
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800;900&family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="collapsedControl"] { display: none; }

/* Base typography */
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
h1, h2, h3 { font-family: 'Poppins', sans-serif !important; }
.main .block-container { padding: 1rem 2rem 2rem; max-width: 1500px; }

/* ── Hero Banner ───────────────────────────────────────────── */
.hero {
  background: linear-gradient(135deg, rgba(124,58,237,.28) 0%, rgba(0,229,255,.10) 50%, rgba(236,72,153,.12) 100%);
  border: 1px solid rgba(0,229,255,.25);
  border-radius: 20px;
  padding: 28px 32px;
  margin-bottom: 20px;
  backdrop-filter: blur(12px);
  position: relative;
  overflow: hidden;
}
.hero::before {
  content: '';
  position: absolute;
  top: -50%; right: -20%;
  width: 400px; height: 400px;
  background: radial-gradient(circle, rgba(0,229,255,.08) 0%, transparent 70%);
  pointer-events: none;
}
.hero-tag {
  font-size: .72rem; font-weight: 700; letter-spacing: .18em;
  color: #A78BFA; text-transform: uppercase; margin-bottom: 8px;
  display: inline-block;
  background: rgba(167,139,250,.12);
  padding: 4px 12px;
  border-radius: 20px;
  border: 1px solid rgba(167,139,250,.25);
}
.hero h1 {
  font-size: 1.8rem; font-weight: 900; margin: 8px 0 0;
  background: linear-gradient(135deg, #fff 0%, #00E5FF 60%, #A78BFA 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  line-height: 1.2;
}
.hero p {
  color: rgba(255,255,255,.55); font-size: .9rem; margin: 8px 0 0;
  line-height: 1.5;
}

/* ── Metric Cards ──────────────────────────────────────────── */
.metric-card {
  background: rgba(255,255,255,.04);
  border: 1px solid rgba(0,229,255,.15);
  border-radius: 16px;
  padding: 18px 20px;
  transition: all .3s cubic-bezier(.4,0,.2,1);
  backdrop-filter: blur(8px);
  position: relative;
  overflow: hidden;
}
.metric-card::after {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
  background: linear-gradient(90deg, #00E5FF, #A78BFA);
  opacity: 0;
  transition: opacity .3s ease;
}
.metric-card:hover {
  border-color: rgba(0,229,255,.35);
  transform: translateY(-2px);
  box-shadow: 0 8px 32px rgba(0,229,255,.12);
}
.metric-card:hover::after { opacity: 1; }
.metric-label {
  font-size: .7rem; font-weight: 600; color: rgba(255,255,255,.45);
  text-transform: uppercase; letter-spacing: .1em; margin-bottom: 6px;
}
.metric-value {
  font-family: 'Poppins', sans-serif; font-size: 1.5rem;
  font-weight: 800; color: #00E5FF;
  line-height: 1.1;
}
.metric-value.hot { color: #ef4444; }
.metric-value.warn { color: #f97316; }
.metric-value.cool { color: #22c55e; }
.metric-value.purple { color: #A78BFA; }

/* ── Source Badge ───────────────────────────────────────────── */
.source-badge {
  display: inline-flex; align-items: center; gap: 6px;
  background: rgba(34,197,94,.12);
  border: 1px solid rgba(34,197,94,.3);
  border-radius: 20px;
  padding: 4px 14px;
  font-size: .75rem; font-weight: 600;
  color: #22c55e;
  margin-top: 8px;
}
.source-badge.synthetic {
  background: rgba(249,115,22,.12);
  border-color: rgba(249,115,22,.3);
  color: #f97316;
}

/* ── Priority Ranking Cards ────────────────────────────────── */
.priority-card {
  background: linear-gradient(135deg, rgba(255,255,255,.03) 0%, rgba(0,229,255,.04) 100%);
  border: 1px solid rgba(0,229,255,.12);
  border-radius: 14px;
  padding: 16px 20px;
  margin-bottom: 10px;
  transition: all .3s ease;
  display: flex;
  align-items: center;
  gap: 16px;
}
.priority-card:hover {
  border-color: rgba(0,229,255,.3);
  transform: translateX(4px);
  box-shadow: 0 4px 20px rgba(0,229,255,.08);
}
.priority-rank {
  font-family: 'Poppins', sans-serif;
  font-size: 1.6rem; font-weight: 900;
  color: #00E5FF;
  min-width: 44px; text-align: center;
}
.priority-info { flex: 1; }
.priority-cell {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 600; font-size: .95rem; color: #fff;
}
.priority-action {
  font-size: .82rem; color: rgba(255,255,255,.55);
  margin-top: 2px;
}
.priority-stats {
  text-align: right;
}
.priority-cooling {
  font-family: 'Poppins', sans-serif;
  font-size: 1.1rem; font-weight: 700; color: #22c55e;
}
.priority-roi {
  font-size: .75rem; color: rgba(255,255,255,.4);
  margin-top: 2px;
}

/* ── Analysis Cards ────────────────────────────────────────── */
.analysis-card {
  background: rgba(255,255,255,.04);
  border: 1px solid rgba(167,139,250,.2);
  border-radius: 14px;
  padding: 18px 22px;
  margin-bottom: 12px;
}
.analysis-title {
  font-family: 'Poppins', sans-serif;
  font-size: 1rem; font-weight: 700; color: #A78BFA;
  margin-bottom: 10px;
}
.rec-item {
  background: rgba(0,229,255,.06);
  border: 1px solid rgba(0,229,255,.15);
  border-radius: 10px;
  padding: 12px 16px;
  margin-bottom: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.rec-action {
  font-weight: 600; font-size: .9rem; color: #fff;
  text-transform: capitalize;
}
.rec-cooling {
  font-family: 'Poppins', sans-serif;
  font-weight: 700; color: #22c55e;
  font-size: .95rem;
}

/* ── Sim Result Cards ──────────────────────────────────────── */
.sim-result {
  background: linear-gradient(135deg, rgba(34,197,94,.08), rgba(0,229,255,.06));
  border: 1px solid rgba(34,197,94,.2);
  border-radius: 14px;
  padding: 16px 20px;
  margin-bottom: 10px;
}
.sim-label { font-size: .82rem; color: rgba(255,255,255,.5); }
.sim-value {
  font-family: 'Poppins', sans-serif;
  font-size: 1.3rem; font-weight: 800; color: #22c55e;
}
.sim-combined {
  background: linear-gradient(135deg, rgba(0,229,255,.12), rgba(167,139,250,.12));
  border: 1px solid rgba(0,229,255,.3);
  border-radius: 16px;
  padding: 20px 24px;
  text-align: center;
  margin-top: 12px;
}
.sim-combined-label {
  font-size: .8rem; font-weight: 600; color: #A78BFA;
  text-transform: uppercase; letter-spacing: .12em;
}
.sim-combined-value {
  font-family: 'Poppins', sans-serif;
  font-size: 2rem; font-weight: 900; color: #00E5FF;
}

/* ── Tabs ──────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
  gap: 8px;
  background: rgba(255,255,255,.02);
  border-radius: 12px;
  padding: 4px;
}
.stTabs [data-baseweb="tab"] {
  border-radius: 8px;
  font-weight: 600;
  padding: 8px 20px;
}

/* ── Footer ────────────────────────────────────────────────── */
.app-footer {
  text-align: center;
  padding: 24px 0 8px;
  color: rgba(255,255,255,.25);
  font-size: .72rem;
  border-top: 1px solid rgba(255,255,255,.06);
  margin-top: 32px;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ── Hero Banner ──────────────────────────────────────────────────────────────
st.markdown(
    """
<div class="hero">
  <div class="hero-tag">🏆 ISRO HACKATHON 2026 · BHARATIYA ANTARIKSH HACKATHON</div>
  <h1>🌡️ HeatVision AI — Urban Heat Hotspot Platform</h1>
  <p>Real-time OpenWeather temperatures · Isolation Forest anomaly detection · K-Means spatial clustering · Gemini AI cooling recommendations</p>
</div>
""",
    unsafe_allow_html=True,
)


# ── API helpers ──────────────────────────────────────────────────────────────
def fetch_dashboard(city=None):
    with httpx.Client(timeout=60) as client:
        params = {"city": city} if city else {}
        r = client.get(f"{API_BASE}/api/v1/locations/dashboard", params=params)
        r.raise_for_status()
        return r.json()


def fetch_analysis(cell_id: str):
    with httpx.Client(timeout=30) as client:
        r = client.get(f"{API_BASE}/api/v1/analysis/{cell_id}")
        r.raise_for_status()
        return r.json()


def fetch_recommendations(cell_id: str, budget: str):
    with httpx.Client(timeout=30) as client:
        r = client.post(
            f"{API_BASE}/api/v1/recommendations",
            json={"cell_id": cell_id, "budget_tier": budget},
        )
        r.raise_for_status()
        return r.json()


def fetch_simulate(cell_id: str, tree_delta: float, roof_pct: float):
    with httpx.Client(timeout=30) as client:
        r = client.post(
            f"{API_BASE}/api/v1/simulate",
            json={
                "cell_id": cell_id,
                "scenarios": [
                    {"intervention": "increase_tree_cover", "delta_pct": tree_delta},
                    {"intervention": "cool_roofs", "coverage_pct": roof_pct},
                ],
            },
        )
        r.raise_for_status()
        return r.json()


def severity_color(severity: str) -> str:
    return {"high": "#ef4444", "medium": "#f97316", "low": "#22c55e"}.get(severity, "#3b82f6")


def temp_color(temp: float, min_t: float, max_t: float) -> str:
    ratio = (temp - min_t) / max(max_t - min_t, 0.1)
    r = int(255 * min(1, max(0, ratio)))
    g = int(255 * min(1, max(0, 1 - ratio)))
    return f"#{r:02x}{g:02x}33"


st.sidebar.markdown("### Location Settings")
selected_city = st.sidebar.text_input("Target City", "Raipur")

# ── Refresh Button with Status ───────────────────────────────────────────────
if st.button("🔄 Refresh Live Data", type="primary"):
    with st.status(f"🛰️ Fetching live data for {selected_city}...", expanded=True) as status:
        try:
            st.write("📡 Connecting to OpenWeather API...")
            with httpx.Client(timeout=60) as client:
                client.post(f"{API_BASE}/api/v1/locations/refresh", params={"city": selected_city})
            st.write("🧠 Running Isolation Forest anomaly detection...")
            st.write("✅ Data loaded successfully!")
            status.update(label=f"✅ {selected_city} grid refreshed!", state="complete", expanded=False)
            st.cache_data.clear()
            st.rerun()
        except Exception as exc:
            status.update(label="❌ Refresh failed", state="error")
            st.error(f"Error: {exc}")

# ── Load Dashboard Data ──────────────────────────────────────────────────────
with st.status("Loading dashboard...", expanded=False) as load_status:
    try:
        dash = fetch_dashboard(selected_city)
        load_status.update(label="✅ Dashboard ready", state="complete")
    except Exception as exc:
        load_status.update(label="❌ Failed to load", state="error")
        st.error(f"Cannot load dashboard for {selected_city}: {exc}")
        st.info("💡 Click **Refresh Live Data** above to fetch data for the first time, or check that your OPENWEATHER_API_KEY is set in `.env`.")
        st.stop()

data = dash["hotspots"]
stats = data["stats"]
ml_count = dash["ml_hotspot_count"]

# ── Metric Cards ─────────────────────────────────────────────────────────────
metrics = [
    ("🌡️ Mean Temp", f"{stats['mean_temp_c']}°C", "warn"),
    ("🔥 Peak Temp", f"{stats['max_temp_c']}°C", "hot"),
    ("⚠️ Hotspots", str(stats["hotspot_count"]), "warn"),
    ("🧠 ML Anomalies", str(ml_count), "purple"),
    ("🏙️ City", dash["city"], ""),
    ("📡 Source", dash["data_source"].upper(), "cool" if dash["data_source"] == "live" else "warn"),
]

cols = st.columns(6)
for col, (label, val, color_cls) in zip(cols, metrics):
    with col:
        st.markdown(
            f'<div class="metric-card"><div class="metric-label">{label}</div>'
            f'<div class="metric-value {color_cls}">{val}</div></div>',
            unsafe_allow_html=True,
        )

# Source badge
badge_cls = "" if dash["data_source"] == "live" else " synthetic"
badge_icon = "🟢" if dash["data_source"] == "live" else "🟠"
st.markdown(
    f'<div class="source-badge{badge_cls}">{badge_icon} {dash["formatted_address"]} · '
    f'Base avg {dash["base_temperature_c"]}°C · {dash["ml_model"]}</div>',
    unsafe_allow_html=True,
)

st.markdown("")  # spacer

# ── Tabs ─────────────────────────────────────────────────────────────────────
tab_map, tab_analysis, tab_sim, tab_priority = st.tabs([
    "🗺️ Heat Map",
    "🔍 Root Cause & AI Recommendations",
    "🔬 What-If Simulator",
    "📊 Priority Zones",
])

# ── Tab 1: Heat Map ─────────────────────────────────────────────────────────
with tab_map:
    if not data["cells"]:
        st.warning("No heat data available. Click **Refresh Live Data** above.")
        st.stop()

    bbox = data["bbox"]
    center = [(bbox[1] + bbox[3]) / 2, (bbox[0] + bbox[2]) / 2]
    m = folium.Map(location=center, zoom_start=13, tiles="CartoDB dark_matter")

    temps = [c["temperature_c"] for c in data["cells"]]
    min_t, max_t = min(temps), max(temps)

    for cell in data["cells"]:
        border = severity_color(cell["severity"])
        if cell.get("ml_is_hotspot"):
            border = "#a855f7"
        folium.GeoJson(
            cell["geometry"],
            style_function=lambda _f, c=cell, mn=min_t, mx=max_t, bc=border: {
                "fillColor": temp_color(c["temperature_c"], mn, mx),
                "color": bc,
                "weight": 3 if c.get("ml_is_hotspot") else 2,
                "fillOpacity": 0.68,
            },
            tooltip=folium.Tooltip(
                f"<b>{cell['cell_id']}</b><br>"
                f"🌡️ {cell['temperature_c']}°C<br>"
                f"Severity: {cell['severity'].upper()}<br>"
                f"ML Hotspot: {'Yes 🔴' if cell.get('ml_is_hotspot') else 'No'}"
            ),
        ).add_to(m)

    st_folium(m, use_container_width=True, height=550, returned_objects=[])

    # Legend
    legend_cols = st.columns(4)
    with legend_cols[0]:
        st.markdown("🟢 **Low severity** — Normal zone")
    with legend_cols[1]:
        st.markdown("🟠 **Medium severity** — Warm zone")
    with legend_cols[2]:
        st.markdown("🔴 **High severity** — Heat island")
    with legend_cols[3]:
        st.markdown("🟣 **ML Anomaly** — Isolation Forest flagged")


# ── Tab 2: Root Cause Analysis + AI Recommendations ─────────────────────────
with tab_analysis:
    st.markdown("### 🔍 Analyze a Hotspot Zone")
    st.markdown("Select a grid cell to understand **why** it's hot and get **AI-powered cooling recommendations**.")

    ac1, ac2 = st.columns([2, 1])
    with ac1:
        cell_ids = [c["cell_id"] for c in data["cells"]]
        hottest = max(data["cells"], key=lambda c: c["temperature_c"])["cell_id"]
        selected = st.selectbox("Select hotspot cell", cell_ids, index=cell_ids.index(hottest), key="analysis_cell")
    with ac2:
        budget = st.select_slider("Budget tier", options=["low", "medium", "high"], value="medium", key="analysis_budget")

    if st.button("🧠 Analyze & Get AI Recommendations", type="primary", key="btn_analyze"):
        with st.status("🔬 Analyzing root causes...", expanded=True) as analysis_status:
            try:
                st.write(f"📊 Scoring contributors for **{selected}**...")
                analysis = fetch_analysis(selected)

                st.write("🤖 Generating AI cooling recommendations...")
                recs = fetch_recommendations(selected, budget)

                analysis_status.update(label="✅ Analysis complete!", state="complete", expanded=False)
            except Exception as exc:
                analysis_status.update(label="❌ Analysis failed", state="error")
                st.error(f"Error: {exc}")
                st.stop()

        # Root cause results
        st.markdown(
            f'<div class="analysis-card"><div class="analysis-title">📊 Root Cause Analysis — {selected}</div>'
            f'<p style="color:rgba(255,255,255,.7);font-size:.9rem">{analysis["summary"]}</p></div>',
            unsafe_allow_html=True,
        )

        st.markdown("**Contributing Factors:**")
        for contrib in analysis["contributors"]:
            factor_label = contrib["factor"].replace("_", " ").title()
            st.progress(contrib["score"], text=f"**{factor_label}** — {contrib['detail']}")

        # AI Recommendations
        st.markdown("---")
        st.markdown("### 🤖 AI Cooling Recommendations")
        if recs.get("narrative"):
            st.info(f"💡 {recs['narrative']}")

        for rec in recs["recommendations"]:
            action_label = rec["action"].replace("_", " ").title()
            qty = rec.get("quantity")
            qty_html = f" · {qty}" if qty else ""
            st.markdown(
                f'<div class="rec-item">'
                f'<div><span class="rec-action">{action_label}</span>'
                f'{qty_html}'
                f'</div>'
                f'<span class="rec-cooling">−{rec["estimated_cooling_c"]}°C</span>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ── Tab 3: What-If Simulator ────────────────────────────────────────────────
with tab_sim:
    st.markdown("### 🔬 What-If Simulator")
    st.markdown("Estimate temperature reduction from green interventions. Adjust the sliders and run a simulation.")

    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        sim_cell = st.selectbox("Grid cell", [c["cell_id"] for c in data["cells"]], key="sim_cell")
    with sc2:
        tree_delta = st.slider("🌳 Increase tree cover by", 0, 40, 20, format="%d%%")
    with sc3:
        roof_pct = st.slider("🏠 Cool roof coverage", 0, 80, 30, format="%d%%")

    if st.button("▶️ Run Simulation", type="primary", key="btn_sim"):
        with st.status("🔬 Simulating interventions...", expanded=True) as sim_status:
            try:
                result = fetch_simulate(sim_cell, tree_delta, roof_pct)
                sim_status.update(label="✅ Simulation complete!", state="complete", expanded=False)
            except Exception as exc:
                sim_status.update(label="❌ Simulation failed", state="error")
                st.error(f"Error: {exc}")
                st.stop()

        # Baseline
        st.markdown(
            f'<div class="metric-card" style="margin-bottom:16px">'
            f'<div class="metric-label">📍 Baseline Temperature — {sim_cell}</div>'
            f'<div class="metric-value hot">{result["baseline_temp_c"]}°C</div></div>',
            unsafe_allow_html=True,
        )

        # Individual results
        r_cols = st.columns(len(result["results"]))
        for col, row in zip(r_cols, result["results"]):
            with col:
                intervention_label = row["intervention"].replace("_", " ").title()
                st.markdown(
                    f'<div class="sim-result">'
                    f'<div class="sim-label">{intervention_label}</div>'
                    f'<div class="sim-value">{row["projected_temp_c"]}°C</div>'
                    f'<div class="sim-label" style="color:#22c55e">−{row["cooling_c"]}°C cooling</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        # Combined
        if result.get("combined_projected_temp_c"):
            st.markdown(
                f'<div class="sim-combined">'
                f'<div class="sim-combined-label">🎯 Combined Projected Temperature</div>'
                f'<div class="sim-combined-value">{result["combined_projected_temp_c"]}°C</div>'
                f'<div style="color:#22c55e;font-weight:600;margin-top:4px">'
                f'Total cooling: −{result.get("combined_cooling_c", "?")}°C</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ── Tab 4: Priority Zones ───────────────────────────────────────────────────
with tab_priority:
    st.markdown("### 📊 Priority Intervention Zones")
    st.markdown("Zones ranked by **heat stress** and **intervention ROI** — where cooling action will have the biggest impact.")

    for item in dash["priority"]["rankings"]:
        action_label = item["recommended_action"].replace("_", " ").title()
        st.markdown(
            f"""
<div class="priority-card">
  <div class="priority-rank">#{item['rank']}</div>
  <div class="priority-info">
    <div class="priority-cell">{item['cell_id']}</div>
    <div class="priority-action">💡 {action_label}</div>
  </div>
  <div class="priority-stats">
    <div class="priority-cooling">−{item['expected_cooling_c']}°C</div>
    <div class="priority-roi">ROI: {item['intervention_roi']}x</div>
  </div>
</div>""",
            unsafe_allow_html=True,
        )


# ── Footer ───────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="app-footer">HeatVision AI · ISRO Bharatiya Antariksh Hackathon 2026 · '
    'Powered by OpenWeather · Isolation Forest · K-Means · Gemini AI</div>',
    unsafe_allow_html=True,
)
