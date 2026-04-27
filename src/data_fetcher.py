"""
Data Fetcher — Pulls GA4 marketing data from BigQuery.
Part of the AI Marketing Intelligence Agent (Project 1).

Supports two authentication modes:
  1. Local: uses gcloud application-default credentials
  2. Streamlit Cloud: uses service account from st.secrets

Usage:
    python src/data_fetcher.py
"""

import os
from pathlib import Path
from google.cloud import bigquery
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# Google Cloud project ID
PROJECT_ID = "galvanic-smoke-489914-u7"

# Path to SQL queries
QUERIES_DIR = Path(__file__).parent.parent / "queries"


def get_client() -> bigquery.Client:
    """
    Create a BigQuery client.
    Uses Streamlit secrets if available (for cloud deployment),
    otherwise falls back to local gcloud credentials.
    """
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "gcp_service_account" in st.secrets:
            from google.oauth2 import service_account
            credentials = service_account.Credentials.from_service_account_info(
                st.secrets["gcp_service_account"]
            )
            return bigquery.Client(credentials=credentials, project=PROJECT_ID)
    except Exception:
        pass

    # Fallback: local gcloud auth
    return bigquery.Client(project=PROJECT_ID)


def load_query(filename: str) -> str:
    """Load a SQL query from the queries/ directory."""
    query_path = QUERIES_DIR / filename
    with open(query_path, "r") as f:
        return f.read()


def fetch_daily_metrics(
    start_date: str = "20210101",
    end_date: str = "20210131",
) -> pd.DataFrame:
    """
    Fetch daily marketing metrics by traffic source from BigQuery.

    Args:
        start_date: Start date in YYYYMMDD format (default: Jan 1, 2021)
        end_date: End date in YYYYMMDD format (default: Jan 31, 2021)

    Returns:
        DataFrame with columns: date, source, medium, users, sessions,
        page_views, purchases, revenue
    """
    client = get_client()

    # Load and parameterize the query
    query_template = load_query("daily_metrics.sql")
    query = query_template.format(start_date=start_date, end_date=end_date)

    print(f"Fetching metrics from {start_date} to {end_date}...")

    # Run query and convert to DataFrame
    df = client.query(query).to_dataframe()

    # Clean up data types
    df["date"] = pd.to_datetime(df["date"])
    df["revenue"] = df["revenue"].fillna(0).astype(float)
    df["purchases"] = df["purchases"].fillna(0).astype(int)

    print(f"Fetched {len(df)} rows across {df['date'].nunique()} days")
    print(f"Traffic sources found: {df['source'].nunique()}")
    print(f"Total sessions: {df['sessions'].sum():,}")
    print(f"Total revenue: ${df['revenue'].sum():,.2f}")

    return df


def fetch_aggregated_daily(
    start_date: str = "20210101",
    end_date: str = "20210131",
) -> pd.DataFrame:
    """
    Fetch daily totals (all sources combined) for trend analysis.
    Useful for anomaly detection across the whole site.
    """
    df = fetch_daily_metrics(start_date, end_date)

    daily = df.groupby("date").agg({
        "users": "sum",
        "sessions": "sum",
        "page_views": "sum",
        "purchases": "sum",
        "revenue": "sum",
    }).reset_index()

    # Add derived metrics
    daily["conversion_rate"] = (daily["purchases"] / daily["sessions"] * 100).round(2)
    daily["revenue_per_session"] = (daily["revenue"] / daily["sessions"]).round(2)

    return daily


if __name__ == "__main__":
    print("=" * 60)
    print("AI Marketing Intelligence Agent — Data Fetcher")
    print("=" * 60)
    print()

    # Test: Fetch January 2021 data
    df = fetch_daily_metrics()

    print()
    print("Sample data (first 10 rows):")
    print(df.head(10).to_string(index=False))

    print()
    print("=" * 60)
    print("Daily aggregated totals:")
    print("=" * 60)
    daily = fetch_aggregated_daily()
    print(daily.head(10).to_string(index=False))
