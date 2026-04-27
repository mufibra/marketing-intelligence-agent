"""
Pipeline — Orchestrates the full Marketing Intelligence Agent flow.
Part of the AI Marketing Intelligence Agent (Project 1).

This chains everything together:
  1. data_fetcher.py pulls from BigQuery (THE HANDS)
  2. anomaly_detector.py flags issues (THE HANDS)
  3. ai_analyzer.py generates the briefing (THE BRAIN)
  4. Output as structured dict for the Streamlit dashboard (THE OUTPUT)

Following James Pasmantier's architecture: separate strategic reasoning
(Gemini) from execution (BigQuery + Python).
"""

import json
from datetime import datetime

from data_fetcher import fetch_daily_metrics, fetch_aggregated_daily
from anomaly_detector import (
    detect_anomalies,
    detect_channel_anomalies,
    summarize_anomalies,
)
from ai_analyzer import analyze_marketing_data, create_metrics_summary


def run_pipeline(
    start_date: str = "20210101",
    end_date: str = "20210131",
) -> dict:
    """
    Run the full marketing intelligence pipeline.

    Args:
        start_date: Start date in YYYYMMDD format
        end_date: End date in YYYYMMDD format

    Returns:
        Dict with all analysis results, ready for the Streamlit dashboard:
        {
            "generated_at": timestamp,
            "period": {"start": ..., "end": ...},
            "metrics_summary": {...},
            "daily_data": DataFrame,
            "channel_data": DataFrame,
            "site_anomalies": DataFrame,
            "channel_anomalies": DataFrame,
            "anomaly_report": str,
            "ai_briefing": str,
        }
    """
    print("=" * 60)
    print("AI Marketing Intelligence Agent — Full Pipeline")
    print(f"Period: {start_date} to {end_date}")
    print("=" * 60)

    # Step 1: Fetch data from BigQuery
    print("\n[1/5] Fetching channel-level data from BigQuery...")
    channel_data = fetch_daily_metrics(start_date, end_date)

    print("\n[2/5] Aggregating daily totals...")
    daily_data = fetch_aggregated_daily(start_date, end_date)

    # Step 2: Detect anomalies
    print("\n[3/5] Running anomaly detection...")
    site_anomalies = detect_anomalies(daily_data)
    channel_anomalies = detect_channel_anomalies(channel_data)

    site_report = summarize_anomalies(site_anomalies)
    channel_report = summarize_anomalies(channel_anomalies)

    # Combine anomaly reports
    full_anomaly_report = (
        "SITE-WIDE ANOMALIES:\n"
        + site_report
        + "\n\nCHANNEL-LEVEL ANOMALIES:\n"
        + channel_report
    )

    # Step 3: Build metrics summary
    print("\n[4/5] Building metrics summary...")
    metrics_summary = create_metrics_summary(daily_data)

    # Step 4: Generate AI briefing
    print("\n[5/5] Generating AI briefing via Gemini...")
    daily_trends = daily_data.tail(10).to_string(index=False)
    ai_briefing = analyze_marketing_data(
        metrics_summary, full_anomaly_report, daily_trends
    )

    # Package everything
    result = {
        "generated_at": datetime.now().isoformat(),
        "period": {"start": start_date, "end": end_date},
        "metrics_summary": metrics_summary,
        "daily_data": daily_data,
        "channel_data": channel_data,
        "site_anomalies": site_anomalies,
        "channel_anomalies": channel_anomalies,
        "anomaly_report": full_anomaly_report,
        "ai_briefing": ai_briefing,
    }

    print("\n✅ Pipeline complete!")
    return result


if __name__ == "__main__":
    result = run_pipeline()

    print("\n" + "=" * 60)
    print("METRICS SUMMARY")
    print("=" * 60)
    print(json.dumps(result["metrics_summary"], indent=2, default=str))

    print("\n" + "=" * 60)
    print("ANOMALY REPORT")
    print("=" * 60)
    print(result["anomaly_report"])

    print("\n" + "=" * 60)
    print("AI MARKETING INTELLIGENCE BRIEFING")
    print("=" * 60)
    print(result["ai_briefing"])
