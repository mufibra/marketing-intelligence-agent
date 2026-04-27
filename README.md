# 📊 AI Marketing Intelligence Agent

An AI-powered marketing analytics agent that connects to real GA4 e-commerce data via BigQuery, automatically detects statistical anomalies, and generates strategic intelligence briefings using Google Gemini — like having a senior marketing analyst working 24/7.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![Google Cloud](https://img.shields.io/badge/Google%20Cloud-BigQuery-4285F4?style=flat&logo=google-cloud&logoColor=white)
![Gemini](https://img.shields.io/badge/Google-Gemini%202.5-8E75B2?style=flat&logo=google&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B?style=flat&logo=streamlit&logoColor=white)

---

## The Problem

Marketing teams spend **2-3 hours daily** manually checking dashboards, compiling reports, and trying to spot what changed. By the time a human notices a revenue drop or a campaign spike, the window to act on it has often passed.

## The Solution

This agent automates the entire marketing intelligence workflow:

1. **Connects to real marketing data** — pulls GA4 e-commerce metrics from BigQuery (sessions, users, revenue, conversions, by traffic channel)
2. **Detects anomalies automatically** — uses rolling 7-day z-score analysis to flag statistically significant changes, classified as WARNING (>2 SD) or CRITICAL (>3 SD)
3. **Generates strategic briefings** — sends structured data + anomaly reports to Google Gemini, which produces a CMO-level intelligence briefing with executive summary, ranked insights, root cause analysis, and prioritized action items
4. **Displays everything in a live dashboard** — interactive Streamlit app with trend charts, anomaly alerts, channel breakdowns, and the full AI briefing

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    THE HANDS                         │
│                                                     │
│  BigQuery (GA4 Data)  →  Python + scipy             │
│  - Sessions, users       - 7-day rolling averages   │
│  - Revenue, purchases    - Z-score anomaly detection │
│  - Traffic sources       - WARNING / CRITICAL flags  │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│                    THE BRAIN                         │
│                                                     │
│  Google Gemini 2.5 Flash                            │
│  - Receives structured metrics + anomaly report     │
│  - Analyzes trends, identifies root causes          │
│  - Generates strategic recommendations              │
│  - Produces CMO-level intelligence briefing         │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│                   THE OUTPUT                         │
│                                                     │
│  Streamlit Dashboard                                │
│  - Key metric cards with day-over-day deltas        │
│  - Interactive trend charts (Plotly)                 │
│  - Anomaly alert cards (Critical / Warning)         │
│  - Channel performance breakdown                    │
│  - Full AI-generated marketing briefing             │
└─────────────────────────────────────────────────────┘
```

---

## Screenshots

> *Add screenshots of your dashboard here after deployment*

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Data Source | Google BigQuery (GA4 public dataset) |
| AI Model | Google Gemini 2.5 Flash |
| Anomaly Detection | Python, pandas, scipy (z-scores) |
| Dashboard | Streamlit, Plotly |
| Authentication | Google Cloud SDK (gcloud) |

---

## Quick Start

### Prerequisites
- Python 3.10+
- Google Cloud account with BigQuery API enabled
- Gemini API key from [aistudio.google.com](https://aistudio.google.com)

### Setup

```bash
# Clone the repo
git clone https://github.com/mufibra23/marketing-intelligence-agent.git
cd marketing-intelligence-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Authenticate with Google Cloud
gcloud auth application-default login

# Set up environment variables
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### Run

```bash
# Test the data pipeline
cd src
python pipeline.py

# Launch the dashboard
cd ..
streamlit run app.py
```

The dashboard will open at `http://localhost:8501`.

---

## Project Structure

```
marketing-intelligence-agent/
├── app.py                    # Streamlit dashboard (entry point)
├── requirements.txt          # Python dependencies
├── .env.example              # API key template
├── src/
│   ├── data_fetcher.py       # BigQuery data extraction
│   ├── anomaly_detector.py   # Statistical anomaly detection
│   ├── ai_analyzer.py        # Gemini API integration
│   └── pipeline.py           # End-to-end orchestration
└── queries/
    └── daily_metrics.sql     # GA4 metrics SQL query
```

---

## How It Works

### Data Layer (`data_fetcher.py`)
Queries BigQuery's public GA4 e-commerce dataset for daily metrics broken down by traffic source/medium: sessions, users, page views, purchases, and revenue. Returns clean pandas DataFrames with derived metrics like conversion rate and revenue per session.

### Anomaly Detection (`anomaly_detector.py`)
For each metric, calculates a 7-day rolling average and standard deviation. Any day where the metric deviates more than 2 standard deviations is flagged as a WARNING; more than 3 standard deviations is CRITICAL. Runs both site-wide and per-channel analysis.

### AI Analysis (`ai_analyzer.py`)
Constructs a detailed prompt with the metrics summary, anomaly report, and recent trends, then sends it to Gemini 2.5 Flash. The prompt instructs the model to act as a senior marketing analyst and produce a structured briefing with executive summary, top insights, anomaly explanations, recommended actions, and channel health ratings.

### Dashboard (`app.py`)
Streamlit app that chains everything together with caching, interactive date selection, and a professional UI. Charts are built with Plotly for interactivity. Anomaly markers appear directly on the trend charts.

---

## Sample Output

The anomaly detector found patterns like:
- **Jan 20**: Revenue spiked 232% above 7-day average ($6,706 vs $2,018 avg) — CRITICAL
- **Google CPC**: Revenue surged 1,082% above average on Jan 20 — CRITICAL  
- **Jan 30-31**: Purchases dropped 42-63% below average — WARNING

Gemini analyzed these and identified likely causes (promotional campaigns, possible technical issues for the end-of-month drop) and recommended immediate actions.

---

## Future Improvements

- [ ] Scheduled automated briefings (daily email/Slack via Cloud Functions)
- [ ] Connect to live GA4 properties (not just sample data)
- [ ] Add competitor intelligence scanning
- [ ] Multi-period comparison (week-over-week, month-over-month)
- [ ] Export briefings as PDF reports
- [ ] Deploy as a Cloud Run service with authentication

---

## Data Source

This project uses Google's official [GA4 obfuscated sample e-commerce dataset](https://developers.google.com/analytics/bigquery/web-ecommerce-demo-dataset) (`bigquery-public-data.ga4_obfuscated_sample_ecommerce`). Some traffic source names appear as `<Other>` or `(data deleted)` due to Google's privacy obfuscation — in a production deployment with real GA4 data, full channel attribution would be visible.

---

## License

MIT

---

## Author

**mufibra23** — [github.com/mufibra23](https://github.com/mufibra23)
