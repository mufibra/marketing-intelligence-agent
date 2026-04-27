"""
Marketing Intelligence Dashboard — Streamlit App (v2 Polished)
Part of the AI Marketing Intelligence Agent (Project 1).

Architecture: BigQuery (hands) → Anomaly Detection (hands) → Gemini (brain) → Dashboard (output)

Run with: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import sys
import os
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from data_fetcher import fetch_daily_metrics, fetch_aggregated_daily
from anomaly_detector import detect_anomalies, detect_channel_anomalies, summarize_anomalies
from ai_analyzer import analyze_marketing_data, create_metrics_summary

# ============================================================
# Page Config
# ============================================================
st.set_page_config(
    page_title="Marketing Intelligence Agent",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# Professional Theme
# ============================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .top-banner {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #334155 100%);
        padding: 32px 40px;
        border-radius: 16px;
        margin-bottom: 24px;
        position: relative;
        overflow: hidden;
    }
    .top-banner::before {
        content: '';
        position: absolute;
        top: -50%;
        right: -20%;
        width: 400px;
        height: 400px;
        background: radial-gradient(circle, rgba(99,102,241,0.15) 0%, transparent 70%);
        border-radius: 50%;
    }
    .top-banner h1 {
        color: #f8fafc;
        font-size: 1.8rem;
        font-weight: 700;
        margin: 0 0 4px 0;
        letter-spacing: -0.02em;
    }
    .top-banner p {
        color: #94a3b8;
        font-size: 0.9rem;
        margin: 0;
    }
    .top-banner .badge {
        display: inline-block;
        background: rgba(99,102,241,0.2);
        color: #a5b4fc;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 500;
        margin-top: 8px;
        border: 1px solid rgba(99,102,241,0.3);
    }
    
    .metric-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        transition: box-shadow 0.2s;
    }
    .metric-card:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.06);
    }
    .metric-card .label {
        font-size: 0.75rem;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 4px;
    }
    .metric-card .value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #0f172a;
        line-height: 1.2;
    }
    .metric-card .delta {
        font-size: 0.8rem;
        font-weight: 500;
        margin-top: 4px;
    }
    .delta-up { color: #059669; }
    .delta-down { color: #dc2626; }
    
    .section-header {
        font-size: 1.1rem;
        font-weight: 600;
        color: #1e293b;
        margin: 32px 0 16px 0;
        padding-bottom: 8px;
        border-bottom: 2px solid #e2e8f0;
    }
    
    .alert-critical {
        background: linear-gradient(135deg, #fef2f2, #fee2e2);
        border-left: 4px solid #dc2626;
        padding: 12px 16px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 8px;
        font-size: 0.85rem;
        color: #7f1d1d;
    }
    .alert-warning {
        background: linear-gradient(135deg, #fffbeb, #fef3c7);
        border-left: 4px solid #f59e0b;
        padding: 12px 16px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 8px;
        font-size: 0.85rem;
        color: #78350f;
    }
    
    .alert-summary {
        display: flex;
        gap: 12px;
        margin-bottom: 16px;
    }
    .alert-badge {
        padding: 8px 20px;
        border-radius: 10px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-critical { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; }
    .badge-warning { background: #fffbeb; color: #d97706; border: 1px solid #fde68a; }
    .badge-ok { background: #f0fdf4; color: #16a34a; border: 1px solid #bbf7d0; }
    
    .briefing-wrapper {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 28px 32px;
        margin-top: 8px;
        line-height: 1.7;
        font-size: 0.92rem;
        color: #334155;
    }
    
    [data-testid="stSidebar"] {
        background: #0f172a;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdown"] {
        color: #cbd5e1;
    }
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stCheckbox label span,
    [data-testid="stSidebar"] .stCheckbox label,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span {
        color: #cbd5e1 !important;
    }
    
    .footer-text {
        text-align: center;
        color: #94a3b8;
        font-size: 0.78rem;
        padding: 24px 0 8px;
        border-top: 1px solid #e2e8f0;
        margin-top: 40px;
    }
    
    [data-testid="stMetric"] {
        background: transparent;
        padding: 0;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# Color Palette
# ============================================================
COLORS = {
    "sessions": "#6366f1",
    "revenue": "#059669",
    "conversion": "#f59e0b",
    "purchases": "#0ea5e9",
    "danger": "#dc2626",
}


# ============================================================
# Sidebar
# ============================================================
with st.sidebar:
    st.markdown("### 🤖 Marketing Intelligence")
    st.markdown("---")
    st.markdown("##### 📅 Analysis Period")
    st.caption("GA4 Sample Data: Nov 2020 – Jan 2021")
    
    date_options = {
        "January 2021": ("20210101", "20210131"),
        "December 2020": ("20201201", "20201231"),
        "November 2020": ("20201101", "20201130"),
        "Full Period (Nov-Jan)": ("20201101", "20210131"),
    }
    selected_period = st.selectbox("Select period", list(date_options.keys()))
    start_date, end_date = date_options[selected_period]
    
    st.markdown("---")
    st.markdown("##### ⚙️ Display Options")
    show_channel_anomalies = st.checkbox("Channel-level anomalies", value=True)
    generate_ai_briefing = st.checkbox("AI briefing (uses Gemini)", value=True)
    
    st.markdown("---")
    st.markdown("##### 🏗️ Architecture")
    st.caption("**Data:** BigQuery GA4 Public Dataset")
    st.caption("**Detection:** Python + scipy (z-scores)")
    st.caption("**AI Brain:** Google Gemini 3.1 Pro")
    st.caption("**Frontend:** Streamlit + Plotly")
    st.markdown("---")
    st.caption("Built by mufibra23")
    st.caption("Google Cloud AI Agent Project")


# ============================================================
# Data Loading (cached)
# ============================================================
@st.cache_data(ttl=3600, show_spinner="Connecting to BigQuery...")
def load_data(start, end):
    channel_data = fetch_daily_metrics(start, end)
    daily_data = fetch_aggregated_daily(start, end)
    return channel_data, daily_data

@st.cache_data(ttl=3600, show_spinner="Scanning for anomalies...")
def run_anomaly_detection(daily_json, channel_json):
    daily = pd.read_json(daily_json)
    channel = pd.read_json(channel_json)
    return detect_anomalies(daily), detect_channel_anomalies(channel)

@st.cache_data(ttl=3600, show_spinner="Gemini is analyzing your data...")
def generate_briefing(metrics_json, anomaly_report, daily_trends):
    metrics = json.loads(metrics_json)
    return analyze_marketing_data(metrics, anomaly_report, daily_trends)


# ============================================================
# Load Data
# ============================================================
try:
    channel_data, daily_data = load_data(start_date, end_date)
except Exception as e:
    st.error(f"BigQuery connection failed: {str(e)}")
    st.info("Run `gcloud auth application-default login` to authenticate.")
    st.stop()

site_anomalies, channel_anomalies = run_anomaly_detection(
    daily_data.to_json(), channel_data.to_json()
)

# ============================================================
# Top Banner
# ============================================================
st.markdown(f"""
<div class="top-banner">
    <h1>📊 Marketing Intelligence Briefing</h1>
    <p>{selected_period} &nbsp;·&nbsp; Generated {datetime.now().strftime("%b %d, %Y at %I:%M %p")}</p>
    <span class="badge">AI-Powered Analytics · mufibra23</span>
</div>
""", unsafe_allow_html=True)

# ============================================================
# Key Metrics
# ============================================================
total_sessions = int(daily_data["sessions"].sum())
total_users = int(daily_data["users"].sum())
total_revenue = float(daily_data["revenue"].sum())
total_purchases = int(daily_data["purchases"].sum())
avg_conversion = float(daily_data["conversion_rate"].mean())
avg_rps = float((daily_data["revenue"] / daily_data["sessions"]).mean())

if len(daily_data) >= 2:
    last = daily_data.iloc[-1]
    prev = daily_data.iloc[-2]
    s_delta = ((last["sessions"] - prev["sessions"]) / max(prev["sessions"], 1) * 100)
    r_delta = ((last["revenue"] - prev["revenue"]) / max(prev["revenue"], 1) * 100)
    p_delta = ((last["purchases"] - prev["purchases"]) / max(prev["purchases"], 1) * 100)
else:
    s_delta = r_delta = p_delta = 0

def metric_card(label, value, delta=None, prefix="", suffix=""):
    delta_html = ""
    if delta is not None and delta != 0:
        cls = "delta-up" if delta > 0 else "delta-down"
        arrow = "↑" if delta > 0 else "↓"
        delta_html = f'<div class="delta {cls}">{arrow} {abs(delta):.1f}% vs prev day</div>'
    return f"""
    <div class="metric-card">
        <div class="label">{label}</div>
        <div class="value">{prefix}{value}{suffix}</div>
        {delta_html}
    </div>
    """

cols = st.columns(6)
with cols[0]:
    st.markdown(metric_card("Sessions", f"{total_sessions:,}", s_delta), unsafe_allow_html=True)
with cols[1]:
    st.markdown(metric_card("Users", f"{total_users:,}"), unsafe_allow_html=True)
with cols[2]:
    st.markdown(metric_card("Revenue", f"{total_revenue:,.0f}", r_delta, prefix="$"), unsafe_allow_html=True)
with cols[3]:
    st.markdown(metric_card("Purchases", f"{total_purchases:,}", p_delta), unsafe_allow_html=True)
with cols[4]:
    st.markdown(metric_card("Conversion Rate", f"{avg_conversion:.2f}", suffix="%"), unsafe_allow_html=True)
with cols[5]:
    st.markdown(metric_card("Rev / Session", f"{avg_rps:.2f}", prefix="$"), unsafe_allow_html=True)

# ============================================================
# Anomaly Alerts
# ============================================================
st.markdown('<div class="section-header">🚨 Anomaly alerts</div>', unsafe_allow_html=True)

critical_count = len(site_anomalies[site_anomalies["severity"] == "CRITICAL"]) if len(site_anomalies) > 0 else 0
warning_count = len(site_anomalies[site_anomalies["severity"] == "WARNING"]) if len(site_anomalies) > 0 else 0

st.markdown(f"""
<div class="alert-summary">
    <span class="alert-badge badge-critical">🚨 {critical_count} Critical</span>
    <span class="alert-badge badge-warning">⚠️ {warning_count} Warnings</span>
    <span class="alert-badge badge-ok">📊 {len(daily_data)} Days Analyzed</span>
</div>
""", unsafe_allow_html=True)

if len(site_anomalies) > 0:
    criticals = site_anomalies[site_anomalies["severity"] == "CRITICAL"]
    if len(criticals) > 0:
        for _, row in criticals.iterrows():
            st.markdown(f'<div class="alert-critical">🚨 {row["description"]}</div>', unsafe_allow_html=True)
    
    warnings_df = site_anomalies[site_anomalies["severity"] == "WARNING"]
    if len(warnings_df) > 0:
        with st.expander(f"⚠️ {len(warnings_df)} warnings (click to expand)"):
            for _, row in warnings_df.iterrows():
                st.markdown(f'<div class="alert-warning">⚠️ {row["description"]}</div>', unsafe_allow_html=True)
else:
    st.success("No anomalies detected in this period.")

# ============================================================
# Charts — Row 1: Sessions & Revenue
# ============================================================
st.markdown('<div class="section-header">📈 Trends</div>', unsafe_allow_html=True)

chart_layout = dict(
    template="plotly_white",
    font=dict(family="DM Sans, sans-serif", size=12, color="#475569"),
    title_font=dict(size=14, color="#1e293b"),
    margin=dict(l=20, r=20, t=50, b=20),
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    height=320,
)

chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily_data["date"], y=daily_data["sessions"],
        line=dict(color=COLORS["sessions"], width=2.5),
        fill="tozeroy", fillcolor="rgba(99,102,241,0.08)",
    ))
    if len(site_anomalies) > 0:
        sa = site_anomalies[site_anomalies["metric"] == "sessions"]
        if len(sa) > 0:
            fig.add_trace(go.Scatter(
                x=sa["date"], y=sa["value"], mode="markers",
                marker=dict(color=COLORS["danger"], size=9, symbol="diamond"),
            ))
    fig.update_layout(title="Daily sessions", showlegend=False, **chart_layout)
    st.plotly_chart(fig, use_container_width=True)

with chart_col2:
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=daily_data["date"], y=daily_data["revenue"],
        line=dict(color=COLORS["revenue"], width=2.5),
        fill="tozeroy", fillcolor="rgba(5,150,105,0.08)",
    ))
    if len(site_anomalies) > 0:
        ra = site_anomalies[site_anomalies["metric"] == "revenue"]
        if len(ra) > 0:
            fig2.add_trace(go.Scatter(
                x=ra["date"], y=ra["value"], mode="markers",
                marker=dict(color=COLORS["danger"], size=9, symbol="diamond"),
            ))
    fig2.update_layout(title="Daily revenue ($)", showlegend=False, **chart_layout)
    st.plotly_chart(fig2, use_container_width=True)

# ============================================================
# Charts — Row 2: Conversion Rate & Purchases
# ============================================================
chart_col3, chart_col4 = st.columns(2)

with chart_col3:
    fig5 = go.Figure()
    fig5.add_trace(go.Scatter(
        x=daily_data["date"], y=daily_data["conversion_rate"],
        line=dict(color=COLORS["conversion"], width=2.5),
        fill="tozeroy", fillcolor="rgba(245,158,11,0.08)",
    ))
    avg_cr = daily_data["conversion_rate"].mean()
    fig5.add_hline(
        y=avg_cr, line_dash="dash", line_color="#94a3b8", line_width=1,
        annotation_text=f"Avg: {avg_cr:.2f}%", annotation_position="top right",
        annotation_font_size=11, annotation_font_color="#94a3b8",
    )
    fig5.update_layout(title="Daily conversion rate (%)", showlegend=False, **chart_layout)
    st.plotly_chart(fig5, use_container_width=True)

with chart_col4:
    fig6 = go.Figure()
    fig6.add_trace(go.Bar(
        x=daily_data["date"], y=daily_data["purchases"],
        marker_color=COLORS["purchases"], marker_line_width=0, opacity=0.85,
    ))
    if len(site_anomalies) > 0:
        pa = site_anomalies[site_anomalies["metric"] == "purchases"]
        if len(pa) > 0:
            fig6.add_trace(go.Scatter(
                x=pa["date"], y=pa["value"], mode="markers",
                marker=dict(color=COLORS["danger"], size=9, symbol="diamond"),
            ))
    fig6.update_layout(title="Daily purchases", showlegend=False, **chart_layout)
    st.plotly_chart(fig6, use_container_width=True)

# ============================================================
# Channel Performance
# ============================================================
st.markdown('<div class="section-header">📡 Channel performance</div>', unsafe_allow_html=True)

channel_summary = channel_data.groupby(["source", "medium"]).agg({
    "sessions": "sum", "users": "sum", "revenue": "sum", "purchases": "sum",
}).reset_index()
channel_summary["channel"] = channel_summary["source"] + " / " + channel_summary["medium"]
channel_summary = channel_summary.sort_values("sessions", ascending=True)
top_channels = channel_summary.tail(8)

ch_col1, ch_col2 = st.columns(2)

with ch_col1:
    fig3 = go.Figure(go.Bar(
        x=top_channels["sessions"], y=top_channels["channel"],
        orientation="h", marker_color=COLORS["sessions"], opacity=0.85,
    ))
    fig3.update_layout(title="Sessions by channel", showlegend=False, **chart_layout)
    fig3.update_layout(height=360, margin=dict(l=260, r=20, t=50, b=20))
    st.plotly_chart(fig3, use_container_width=True)

with ch_col2:
    fig4 = go.Figure(go.Bar(
        x=top_channels["revenue"], y=top_channels["channel"],
        orientation="h", marker_color=COLORS["revenue"], opacity=0.85,
    ))
    fig4.update_layout(title="Revenue by channel ($)", showlegend=False, **chart_layout)
    fig4.update_layout(height=360, margin=dict(l=260, r=20, t=50, b=20))
    st.plotly_chart(fig4, use_container_width=True)

# ============================================================
# Channel Anomalies
# ============================================================
if show_channel_anomalies and len(channel_anomalies) > 0:
    st.markdown('<div class="section-header">📡 Channel-level anomalies</div>', unsafe_allow_html=True)
    ch_crit = channel_anomalies[channel_anomalies["severity"] == "CRITICAL"]
    ch_warn = channel_anomalies[channel_anomalies["severity"] == "WARNING"]
    if len(ch_crit) > 0:
        with st.expander(f"🚨 {len(ch_crit)} critical channel alerts"):
            for _, row in ch_crit.iterrows():
                st.markdown(f'<div class="alert-critical">🚨 {row["description"]}</div>', unsafe_allow_html=True)
    if len(ch_warn) > 0:
        with st.expander(f"⚠️ {len(ch_warn)} channel warnings"):
            for _, row in ch_warn.iterrows():
                st.markdown(f'<div class="alert-warning">⚠️ {row["description"]}</div>', unsafe_allow_html=True)

# ============================================================
# AI Briefing
# ============================================================
st.markdown('<div class="section-header">🤖 AI marketing intelligence briefing</div>', unsafe_allow_html=True)

if generate_ai_briefing:
    metrics_summary = create_metrics_summary(daily_data)
    full_report = summarize_anomalies(site_anomalies)
    if show_channel_anomalies and len(channel_anomalies) > 0:
        full_report += "\n\nCHANNEL-LEVEL:\n" + summarize_anomalies(channel_anomalies)
    trends = daily_data.tail(10).to_string(index=False)
    
    briefing = generate_briefing(
        json.dumps(metrics_summary, default=str), full_report, trends,
    )
    
    # Escape $ signs to prevent Streamlit LaTeX rendering
    clean_briefing = briefing.replace("$", "\\$")
    
    st.markdown(clean_briefing)
    
    with st.expander("📄 View raw briefing text"):
        st.text(briefing)
else:
    st.info("AI briefing is disabled. Enable it in the sidebar to generate insights via Gemini.")

# ============================================================
# Raw Data Explorer
# ============================================================
st.markdown('<div class="section-header">📋 Data explorer</div>', unsafe_allow_html=True)

with st.expander("Browse raw data tables"):
    tab1, tab2, tab3 = st.tabs(["📊 Daily Totals", "📡 Channel Data", "🚨 Anomalies"])
    with tab1:
        st.dataframe(daily_data, use_container_width=True, height=400)
    with tab2:
        st.dataframe(channel_data, use_container_width=True, height=400)
    with tab3:
        if len(site_anomalies) > 0:
            st.dataframe(site_anomalies, use_container_width=True, height=400)
        else:
            st.info("No anomalies detected.")

# ============================================================
# Footer
# ============================================================
st.markdown(f"""
<div class="footer-text">
    Built with BigQuery · Gemini 3.1 Pro · Streamlit · Python<br>
    Built by mufibra23 · Google Cloud AI Agent Project<br>
    Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
</div>
""", unsafe_allow_html=True)
