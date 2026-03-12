# Quantitative Options Terminal (GGAL)

End-to-End Analytics Engineering Pipeline focused on the Argentine financial market.

## Arquitectura Técnica
1. **Extracción (GCP):** Cloud Functions orchestrated via Cloud Scheduler to capture real-time options chains from financial APIs.
2. **Carga (BigQuery):** Columnar storage for raw data (JSON).
3. **Transformación (dbt):** Dimensional modeling, RegEx-based parsing, Call-Put parity equations, and Data Quality Testing.
4. **Análisis (Python/Streamlit):** Stochastic models implementing Black-Scholes-Merton (BSM) and Kelly Criterion to evaluate mathematical edge in 1:1 spreads.

**Tech Stack:** Python, SQL, dbt, and Google Cloud Platform (GCP).

**Key features:**
1. **Implied Volatility (IV) Calculation):** Numerical root-finding via py_vollib.
2. **Risk Management:** Automated Kelly Criterion weighting for optimal position sizing.
3. **Synthetic Arbitrage:** Monitoring TNA (Annual Percentage Rate) through synthetic stock positions.
