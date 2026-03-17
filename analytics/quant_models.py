import os
import json
import pandas as pd
import numpy as np
from google.cloud import bigquery
from google.oauth2 import service_account 
from scipy.stats import norm
from py_vollib.black_scholes.implied_volatility import implied_volatility
import requests
from dotenv import load_dotenv

# Local environment variables
load_dotenv()

# Configuration
PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "portfolio-analytics-eng")
R_RISK_FREE = 0.34

def get_live_spot():
    """Fetches current spot price for dynamic BSM calculations."""
    try:
        r = requests.get("https://data912.com/live/arg_stocks", timeout=5)
        return float(pd.DataFrame(r.json()).loc[lambda df: df['symbol'] == 'GGAL', 'c'].iloc[0])
    except Exception as e:
        print(f"Error fetching Spot: {e}")
        return None

def calculate_bsm_probability(spot, strike, t_years, sigma, is_call):
    """Calculates N(d2) for the theoretical probability of expiring ITM."""
    if t_years <= 0 or pd.isna(sigma) or sigma <= 0: return 0
    d2 = (np.log(spot / strike) + (R_RISK_FREE - (sigma**2) / 2) * t_years) / (sigma * np.sqrt(t_years))
    return norm.cdf(d2) if is_call else norm.cdf(-d2)

def main():
    spot = get_live_spot()
    if not spot: return
    print(f"--- STARTING QUANTITATIVE MODEL | SPOT: ${spot:.2f} ---")

    # 1. Credentials Resolution (Local vs CI/CD)
    gcp_sa_key = os.environ.get("GCP_SA_KEY")
    
    if gcp_sa_key:
        # GitHub Actions Environment: Load from injected memory secret
        info = json.loads(gcp_sa_key)
        credentials = service_account.Credentials.from_service_account_info(info)
    else:
        # Local Environment: Load via environment variable
        key_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if not key_path or not os.path.exists(key_path):
            raise FileNotFoundError("Missing GOOGLE_APPLICATION_CREDENTIALS environment variable or JSON file does not exist.")
        credentials = service_account.Credentials.from_service_account_file(key_path)

    client = bigquery.Client(credentials=credentials, project=PROJECT_ID)
    
    # 2. Extract modeled data from dbt
    query = f"""
        SELECT 
            ticker, tipo AS option_type, strike, precio AS price, volumen AS volume, dte
        FROM `{PROJECT_ID}.mercado_financiero_dev.fct_options_latest`
    """
    
    df = client.query(query).to_dataframe()
    if df.empty:
        return print("No modeled data found in BigQuery to process.")

    df = df[df['dte'] > 0].copy()
    df['t_years'] = df['dte'] / 365.0

    # 3. Implied Volatility Vectorization
    def get_iv(row):
        try:
            return implied_volatility(row['price'], spot, row['strike'], row['t_years'], R_RISK_FREE, row['option_type'])
        except:
            return np.nan

    df['iv'] = df.apply(get_iv, axis=1)
    df = df.dropna(subset=['iv'])

    # 4. Probability Calculation (N(d2))
    df['pop'] = df.apply(lambda r: calculate_bsm_probability(spot, r['strike'], r['t_years'], r['iv'], r['option_type'] == 'c'), axis=1)

    # 5. Asymmetric Risk Modeling
    w_avg = df['price'] * 0.30 
    l_avg = df['price'] * 0.70

    df['ev'] = (df['pop'] * w_avg) - ((1 - df['pop']) * l_avg)
    
    df['rr_ratio'] = w_avg / l_avg
    df['kelly_f'] = np.where(
        df['rr_ratio'] > 0,
        df['pop'] - ((1 - df['pop']) / df['rr_ratio']),
        0
    )
    
    df_edge = df[(df['ev'] > 0) & (df['kelly_f'] > 0)].sort_values(by='kelly_f', ascending=False)
    
    pd.set_option('display.float_format', '{:.4f}'.format)
    print("\n[RESULTS] Top 5 Options with Positive Mathematical Expectancy:")
    print(df_edge[['ticker', 'strike', 'dte', 'iv', 'pop', 'ev', 'kelly_f']].head(5).to_string(index=False))

if __name__ == "__main__":
    main()
