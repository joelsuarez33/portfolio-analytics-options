# Quantitative Options Terminal — GGAL
### End-to-End Analytics Engineering Pipeline | Argentine Financial Market

[![Live Demo](https://img.shields.io/badge/Live_Demo-Streamlit-FF4B4B?style=flat&logo=streamlit)](https://portfolio-analytics-options.streamlit.app/)
[![GCP](https://img.shields.io/badge/GCP-Cloud_Functions_%2B_BigQuery-4285F4?style=flat&logo=googlecloud)](https://cloud.google.com/)
[![dbt](https://img.shields.io/badge/dbt-Dimensional_Modeling-FF694B?style=flat&logo=dbt)](https://www.getdbt.com/)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python)](https://www.python.org/)

---

## The Problem

Options chains in emerging markets like Argentina are published as unstructured, infrequent snapshots — no clean API, no historical continuity, no standardized format. Manual analysis means stale data, hours of reconciliation, and no systematic way to identify mathematical edge before it disappears.

This pipeline eliminates that. It captures, structures, and analyzes GGAL options data automatically — delivering a live, quantitative dashboard with zero manual intervention.

---

## Live Demo

🔗 **[portfolio-analytics-options.streamlit.app](https://portfolio-analytics-options.streamlit.app/)**

---

## Architecture

```
Financial API
     │
     ▼
┌─────────────────────────────┐
│  GCP Cloud Functions        │  ← Scheduled extraction (Cloud Scheduler)
│  Real-time options chain    │    Captures raw JSON options chains
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│  BigQuery (Raw Layer)       │  ← Columnar storage
│  JSON ingestion             │    Append-only, immutable raw data
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│  dbt (Transformation Layer) │  ← Dimensional modeling
│  · RegEx-based parsing      │    Call-Put parity equations
│  · Data Quality Tests       │    Standardized schema
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│  Python + Streamlit         │  ← Quantitative analysis layer
│  · Black-Scholes-Merton     │    Stochastic pricing models
│  · Kelly Criterion          │    Risk-adjusted position sizing
│  · Synthetic Arbitrage      │    APR monitoring via synthetic stocks
└─────────────────────────────┘
```

---

## Key Features

### 1. Implied Volatility (IV) Calculation
Numerical root-finding via `py_vollib` to extract market-implied volatility from live options prices — the core input for all downstream stochastic models.

### 2. Black-Scholes-Merton Pricing
Full BSM implementation to calculate theoretical option value, Delta, Gamma, Theta, and Vega. Used to identify mispriced contracts relative to current spot price.

### 3. Kelly Criterion — Optimal Position Sizing
Automated Kelly weighting applied to 1:1 spread strategies. Outputs mathematically optimal position size given edge and odds — removing discretion from risk management.

### 4. Synthetic Arbitrage Monitoring
Real-time APR tracking via synthetic stock positions (long call + short put). Flags spreads where the implied financing rate deviates from market benchmarks.

### 5. Data Quality Layer (dbt Tests)
Automated freshness, uniqueness, and referential integrity tests on every model — ensuring the analysis layer always runs on clean, validated data.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Orchestration | GCP Cloud Scheduler + Cloud Functions |
| Storage | BigQuery (columnar, append-only) |
| Transformation | dbt (dimensional modeling, DQ tests) |
| Analysis | Python (py_vollib, pandas, numpy) |
| Visualization | Streamlit |
| Version Control | Git |

---

## What This Is Not

This is not a tutorial project. There is no pre-cleaned Kaggle dataset, no static CSV, and no hardcoded sample data. Every record in this pipeline was captured live from a financial API, parsed from raw JSON, validated through dbt tests, and priced with stochastic models.

The Argentine options market is illiquid, inconsistently quoted, and structurally different from US markets — which makes it a harder, more interesting engineering problem.

---

## Project Structure

```
portfolio-analytics-options/
├── cloud_functions/
│   └── extract_options/      # GCP Cloud Function — API extraction
├── dbt_project/
│   ├── models/
│   │   ├── staging/          # Raw JSON parsing + RegEx cleaning
│   │   └── marts/            # Dimensional models (calls, puts, spreads)
│   └── tests/                # Data quality assertions
├── streamlit_app/
│   ├── app.py                # Main dashboard
│   └── models/               # BSM + Kelly implementations
└── README.md
```

---

## Running Locally

```bash
git clone https://github.com/joelsuarez33/portfolio-analytics-options
cd portfolio-analytics-options
pip install -r requirements.txt
streamlit run streamlit_app/app.py
```

> **Note:** GCP credentials required for BigQuery access. The live demo at [portfolio-analytics-options.streamlit.app](https://portfolio-analytics-options.streamlit.app/) runs against the production dataset.

---

## Author

**Joel Suarez** — Analytics Engineer | Finance Data Specialist  
[LinkedIn](https://www.linkedin.com/in/joel-f-suarez/) · [GitHub](https://github.com/joelsuarez33)
