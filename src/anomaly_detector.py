"""
Anomaly Detector — Flags unusual changes in marketing metrics.
Part of the AI Marketing Intelligence Agent (Project 1).

Uses simple statistical methods (z-scores on rolling averages)
to detect when metrics deviate significantly from recent trends.

Severity levels:
  - WARNING:  > 2 standard deviations from 7-day average
  - CRITICAL: > 3 standard deviations from 7-day average
"""

import pandas as pd
import numpy as np
from scipy import stats


# Thresholds for anomaly detection
WARNING_THRESHOLD = 2.0   # standard deviations
CRITICAL_THRESHOLD = 3.0  # standard deviations
ROLLING_WINDOW = 7        # days for rolling average


def detect_anomalies(df: pd.DataFrame, metrics: list = None) -> pd.DataFrame:
    """
    Detect anomalies in daily aggregated metrics.

    Args:
        df: DataFrame with 'date' column and numeric metric columns.
            Expected from data_fetcher.fetch_aggregated_daily().
        metrics: List of column names to check. Defaults to core metrics.

    Returns:
        DataFrame of detected anomalies with columns:
        date, metric, value, rolling_avg, rolling_std, z_score,
        severity, pct_change_from_avg
    """
    if metrics is None:
        metrics = ["sessions", "users", "page_views", "purchases", "revenue"]

    # Only check metrics that exist in the DataFrame
    metrics = [m for m in metrics if m in df.columns]

    df = df.sort_values("date").copy()
    anomalies = []

    for metric in metrics:
        # Calculate rolling statistics
        rolling_avg = df[metric].rolling(window=ROLLING_WINDOW, min_periods=3).mean()
        rolling_std = df[metric].rolling(window=ROLLING_WINDOW, min_periods=3).std()

        for i in range(ROLLING_WINDOW, len(df)):
            value = df[metric].iloc[i]
            avg = rolling_avg.iloc[i - 1]   # use previous day's rolling avg
            std = rolling_std.iloc[i - 1]

            # Skip if std is 0 or NaN (no variation)
            if pd.isna(std) or std == 0:
                continue

            # Calculate z-score: how many SDs away from rolling average
            z_score = (value - avg) / std

            # Check if it's an anomaly
            if abs(z_score) >= WARNING_THRESHOLD:
                severity = "CRITICAL" if abs(z_score) >= CRITICAL_THRESHOLD else "WARNING"
                pct_change = ((value - avg) / avg * 100)
                direction = "above" if z_score > 0 else "below"

                anomalies.append({
                    "date": df["date"].iloc[i],
                    "metric": metric,
                    "value": round(value, 2),
                    "rolling_avg": round(avg, 2),
                    "rolling_std": round(std, 2),
                    "z_score": round(z_score, 2),
                    "severity": severity,
                    "pct_change": round(pct_change, 1),
                    "direction": direction,
                    "description": (
                        f"{severity}: {metric} was {value:,.0f} on "
                        f"{df['date'].iloc[i].strftime('%b %d')} — "
                        f"{abs(pct_change):.1f}% {direction} the 7-day average "
                        f"({avg:,.0f}). Z-score: {z_score:.1f}"
                    ),
                })

    anomalies_df = pd.DataFrame(anomalies)

    if len(anomalies_df) > 0:
        # Sort by severity (CRITICAL first) then by absolute z-score
        severity_order = {"CRITICAL": 0, "WARNING": 1}
        anomalies_df["severity_rank"] = anomalies_df["severity"].map(severity_order)
        anomalies_df = anomalies_df.sort_values(
            ["severity_rank", "z_score"], ascending=[True, True]
        ).drop(columns=["severity_rank"])

    return anomalies_df


def detect_channel_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect anomalies per traffic source/medium channel.

    Args:
        df: DataFrame from data_fetcher.fetch_daily_metrics()
            with columns: date, source, medium, sessions, users, etc.

    Returns:
        DataFrame of anomalies with channel info included.
    """
    all_anomalies = []

    # Group by channel (source + medium)
    for (source, medium), channel_df in df.groupby(["source", "medium"]):
        # Need enough data points for rolling stats
        if len(channel_df) < ROLLING_WINDOW + 1:
            continue

        # Aggregate daily totals for this channel
        daily = channel_df.groupby("date").agg({
            "users": "sum",
            "sessions": "sum",
            "page_views": "sum",
            "purchases": "sum",
            "revenue": "sum",
        }).reset_index().sort_values("date")

        if len(daily) < ROLLING_WINDOW + 1:
            continue

        channel_anomalies = detect_anomalies(daily, ["sessions", "revenue"])

        if len(channel_anomalies) > 0:
            channel_anomalies["source"] = source
            channel_anomalies["medium"] = medium
            channel_anomalies["channel"] = f"{source} / {medium}"
            # Update descriptions to include channel
            channel_anomalies["description"] = channel_anomalies.apply(
                lambda row: (
                    f"{row['severity']}: [{row['channel']}] {row['metric']} was "
                    f"{row['value']:,.0f} on {row['date'].strftime('%b %d')} — "
                    f"{abs(row['pct_change']):.1f}% {row['direction']} the 7-day "
                    f"average ({row['rolling_avg']:,.0f}). Z-score: {row['z_score']:.1f}"
                ),
                axis=1,
            )
            all_anomalies.append(channel_anomalies)

    if all_anomalies:
        return pd.concat(all_anomalies, ignore_index=True)
    return pd.DataFrame()


def summarize_anomalies(anomalies_df: pd.DataFrame) -> str:
    """
    Create a human-readable summary of detected anomalies.
    This summary will be passed to the AI analyzer (Gemini).
    """
    if len(anomalies_df) == 0:
        return "No anomalies detected in the current period."

    critical = anomalies_df[anomalies_df["severity"] == "CRITICAL"]
    warnings = anomalies_df[anomalies_df["severity"] == "WARNING"]

    lines = []
    lines.append(f"ANOMALY REPORT: {len(anomalies_df)} anomalies detected")
    lines.append(f"  Critical: {len(critical)}  |  Warning: {len(warnings)}")
    lines.append("-" * 60)

    if len(critical) > 0:
        lines.append("\n🚨 CRITICAL ALERTS:")
        for _, row in critical.iterrows():
            lines.append(f"  • {row['description']}")

    if len(warnings) > 0:
        lines.append("\n⚠️ WARNINGS:")
        for _, row in warnings.iterrows():
            lines.append(f"  • {row['description']}")

    return "\n".join(lines)


# ---- Main: test with real data ----
if __name__ == "__main__":
    from data_fetcher import fetch_daily_metrics, fetch_aggregated_daily

    print("=" * 60)
    print("AI Marketing Intelligence Agent — Anomaly Detector")
    print("=" * 60)

    # 1. Site-wide anomaly detection
    print("\n📊 Fetching aggregated daily data...")
    daily = fetch_aggregated_daily()

    print("\n🔍 Running site-wide anomaly detection...")
    site_anomalies = detect_anomalies(daily)
    print(summarize_anomalies(site_anomalies))

    # 2. Channel-level anomaly detection
    print("\n\n📊 Fetching channel-level data...")
    channel_data = fetch_daily_metrics()

    print("\n🔍 Running channel-level anomaly detection...")
    channel_anomalies = detect_channel_anomalies(channel_data)
    print(summarize_anomalies(channel_anomalies))
