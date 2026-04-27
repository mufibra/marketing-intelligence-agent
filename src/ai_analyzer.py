"""
AI Analyzer — Uses Gemini to generate marketing intelligence briefings.
Part of the AI Marketing Intelligence Agent (Project 1).

Takes structured marketing data + anomaly reports and produces
natural language insights like a senior marketing analyst would.

Following James Pasmantier's "brains vs hands" model from Vybe:
This is THE BRAIN. It receives structured data and generates strategic analysis.
"""

import os
import json
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Use Gemini 3.1
MODEL_NAME = "gemini-3.1-pro-preview"


def build_analysis_prompt(
    metrics_summary: dict,
    anomaly_report: str,
    daily_trends: str,
) -> str:
    """
    Build the prompt that turns raw data into a CMO morning briefing.

    This is where marketing domain knowledge matters most.
    The prompt structure follows James Pasmantier's briefing format:
    what happened, what's important, what needs action.
    """
    prompt = f"""You are a senior marketing analyst preparing a daily intelligence 
briefing for the CMO of an e-commerce company (Google Merchandise Store).

Today's date: {datetime.now().strftime('%B %d, %Y')}
Analysis period: January 2021 (using GA4 sample data)

## METRICS SUMMARY
{json.dumps(metrics_summary, indent=2, default=str)}

## ANOMALY REPORT
{anomaly_report}

## DAILY TRENDS (last 10 days)
{daily_trends}

---

Based on this data, generate a Marketing Intelligence Briefing with these sections:

### 1. EXECUTIVE SUMMARY (3 sentences max)
What's the single most important thing the CMO needs to know today?
Be specific with numbers.

### 2. TOP 3 INSIGHTS (ranked by business impact)
For each insight:
- What happened (specific metric, specific number)
- Why it likely happened (your analysis based on patterns)
- Business impact (revenue, growth, risk)

### 3. ANOMALY ANALYSIS
For each critical anomaly:
- What triggered it
- Most likely cause (consider: promotions, seasonality, technical issues, 
  competitor actions, day-of-week effects)
- Confidence level (high/medium/low)

### 4. RECOMMENDED ACTIONS (prioritized)
For each recommendation:
- Specific action to take
- Expected impact
- Urgency (immediate / this week / this month)

### 5. CHANNEL PERFORMANCE SNAPSHOT
Brief assessment of each traffic channel's health:
- Google Organic
- Direct
- Referral
- Paid (CPC)
Rate each as: Strong / Stable / Needs Attention / Critical

Keep the tone professional but direct. Use specific numbers.
Format with clear headers and bullet points.
"""
    return prompt


def analyze_marketing_data(
    metrics_summary: dict,
    anomaly_report: str,
    daily_trends: str,
) -> str:
    """
    Send marketing data to Gemini and get back an AI-generated briefing.

    Args:
        metrics_summary: Dict with overall metrics (total sessions, revenue, etc.)
        anomaly_report: String from anomaly_detector.summarize_anomalies()
        daily_trends: String representation of recent daily data

    Returns:
        AI-generated marketing intelligence briefing as a string.
    """
    if not GEMINI_API_KEY:
        return (
            "ERROR: GEMINI_API_KEY not found in .env file.\n"
            "Get your key from https://aistudio.google.com\n"
            "Add it to your .env file as: GEMINI_API_KEY=your_key_here"
        )

    prompt = build_analysis_prompt(metrics_summary, anomaly_report, daily_trends)

    print("Sending data to Gemini for analysis...")

    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"ERROR generating analysis: {str(e)}"


def create_metrics_summary(daily_df) -> dict:
    """
    Create a summary dict from the aggregated daily DataFrame.
    This gets passed to Gemini as context.
    """
    return {
        "period": f"{daily_df['date'].min().strftime('%Y-%m-%d')} to {daily_df['date'].max().strftime('%Y-%m-%d')}",
        "total_days": len(daily_df),
        "total_sessions": int(daily_df["sessions"].sum()),
        "total_users": int(daily_df["users"].sum()),
        "total_page_views": int(daily_df["page_views"].sum()),
        "total_purchases": int(daily_df["purchases"].sum()),
        "total_revenue": float(daily_df["revenue"].sum()),
        "avg_daily_sessions": int(daily_df["sessions"].mean()),
        "avg_daily_revenue": round(float(daily_df["revenue"].mean()), 2),
        "avg_conversion_rate": round(float(daily_df["conversion_rate"].mean()), 2),
        "best_day_revenue": {
            "date": daily_df.loc[daily_df["revenue"].idxmax(), "date"].strftime("%Y-%m-%d"),
            "revenue": float(daily_df["revenue"].max()),
        },
        "worst_day_revenue": {
            "date": daily_df.loc[daily_df["revenue"].idxmin(), "date"].strftime("%Y-%m-%d"),
            "revenue": float(daily_df["revenue"].min()),
        },
    }


# ---- Main: test with real data ----
if __name__ == "__main__":
    from data_fetcher import fetch_aggregated_daily
    from anomaly_detector import detect_anomalies, summarize_anomalies

    print("=" * 60)
    print("AI Marketing Intelligence Agent — AI Analyzer")
    print("=" * 60)

    # 1. Fetch data
    print("\n📊 Fetching data...")
    daily = fetch_aggregated_daily()

    # 2. Detect anomalies
    print("\n🔍 Detecting anomalies...")
    anomalies = detect_anomalies(daily)
    anomaly_report = summarize_anomalies(anomalies)

    # 3. Build metrics summary
    metrics_summary = create_metrics_summary(daily)

    # 4. Get daily trends (last 10 days as string)
    daily_trends = daily.tail(10).to_string(index=False)

    # 5. Generate AI briefing
    print("\n🤖 Generating AI briefing...")
    briefing = analyze_marketing_data(metrics_summary, anomaly_report, daily_trends)

    print("\n" + "=" * 60)
    print("MARKETING INTELLIGENCE BRIEFING")
    print("=" * 60)
    print(briefing)
