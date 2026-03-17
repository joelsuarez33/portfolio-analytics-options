import streamlit as st
import pandas as pd
import numpy as np
import itertools
from google.cloud import bigquery
from google.oauth2 import service_account
from scipy.stats import norm
from py_vollib.black_scholes.implied_volatility import implied_volatility
import requests

# --- CONFIGURATION ---
st.set_page_config(page_title="Quantitative Options Terminal | GGAL", layout="wide")

# Market Constants
R_RISK_FREE = 0.34  # Risk-free rate (Approximate local APR)

# --- DATA INGESTION & CACHE ---
@st.cache_data(ttl=300)
def get_live_spot():
    """Fetches real-time GGAL spot price from external API."""
    try:
        r = requests.get("https://data912.com/live/arg_stocks", timeout=5)
        df_live = pd.DataFrame(r.json())
        spot_price = float(df_live.loc[df_live['symbol'] == 'GGAL', 'c'].iloc[0])
        return spot_price
    except Exception as e:
        st.error(f"Error fetching Spot price: {e}")
        return None

@st.cache_data(ttl=300)
def load_bq_data():
    """Loads processed financial data from BigQuery DWH."""
    try:
        cred_dict = dict(st.secrets["gcp_service_account"])
        credentials = service_account.Credentials.from_service_account_info(cred_dict)
        client = bigquery.Client(credentials=credentials, project=cred_dict["project_id"])
        
        query = f"""
            SELECT 
                ticker, tipo as type, strike, precio as price, volumen as volume, dte
            FROM `{cred_dict["project_id"]}.mercado_financiero_dev.fct_opciones_latest`
            WHERE dte > 0 AND precio > 0 AND volumen > 0
        """
        return client.query(query).to_dataframe()
    except Exception as e:
        st.error(f"DWH Connection Error: {e}")
        return pd.DataFrame()

# --- QUANTITATIVE MODELS ---
def calculate_iv_safe(price, spot, strike, t_years, option_type):
    """Numerical root-finding for Implied Volatility (IV)."""
    if option_type not in ['c', 'p'] or t_years <= 0:
        return np.nan
    try:
        return implied_volatility(price, spot, strike, t_years, R_RISK_FREE, option_type)
    except:
        return np.nan

def pop_bs(spot, break_even, t_years, sigma, is_bullish):
    """Calculates Probability of Profit (POP) using Black-Scholes d2."""
    if t_years <= 0 or pd.isna(sigma) or sigma <= 0: 
        return 0.0
    d2 = (np.log(spot / break_even) + (R_RISK_FREE - (sigma**2) / 2) * t_years) / (sigma * np.sqrt(t_years))
    return norm.cdf(d2) if is_bullish else norm.cdf(-d2)

def evaluate_spreads(df_opts, spot, flag, flow_type, dte):
    """Analyzes combinations to find optimal Kelly Criterion spreads."""
    opts = df_opts[df_opts['type'] == flag].sort_values('strike')
    if len(opts) < 2: return None
    
    t_years = dte / 365.0
    spreads = []
    
    for (i1, row1), (i2, row2) in itertools.combinations(opts.iterrows(), 2):
        k1, p1, vi1 = row1['strike'], row1['price'], row1['vi']
        k2, p2, vi2 = row2['strike'], row2['price'], row2['vi']
        
        sigma_avg = np.nanmean([vi1, vi2]) if not (np.isnan(vi1) and np.isnan(vi2)) else 0.45
        width = k2 - k1

        if flag == 'c':
            premium_diff = p1 - p2 
            if flow_type == 'debit':
                strategy, k_long, k_short, cost, max_profit = 'Bull Call (Deb)', k1, k2, premium_diff, width - premium_diff
                be, bullish = k1 + cost, True
            else:
                strategy, k_long, k_short, cost, max_profit = 'Bear Call (Cred)', k2, k1, width - premium_diff, premium_diff 
                be, bullish = k1 + max_profit, False
        else:
            premium_diff = p2 - p1 
            if flow_type == 'debit':
                strategy, k_long, k_short, cost, max_profit = 'Bear Put (Deb)', k2, k1, premium_diff, width - premium_diff
                be, bullish = k2 - cost, False
            else:
                strategy, k_long, k_short, cost, max_profit = 'Bull Put (Cred)', k1, k2, width - premium_diff, premium_diff
                be, bullish = k2 - max_profit, True

        if cost > 0 and max_profit > 0:
            pop = pop_bs(spot, be, t_years, sigma_avg, bullish)
            rr_ratio = max_profit / cost
            pop_fail = 1 - pop
            
            # Kelly Criterion: f* = p - (q/r)
            kelly = (pop - (pop_fail / rr_ratio)) if rr_ratio > 0 else 0
            ev = (pop * max_profit) - (pop_fail * cost)
            
            if ev > 0 and kelly > 0 and pop > 0.20:
                spreads.append({
                    'Strategy': strategy, 'K_Long': k_long, 'K_Short': k_short,
                    'Max_Risk': cost, 'Max_Profit': max_profit, 'R/R': rr_ratio,
                    'POP': pop, 'EV': ev, 'Kelly': kelly
                })

    if not spreads: return None
    df_s = pd.DataFrame(spreads)
    return df_s.loc[df_s['Kelly'].idxmax()]

# --- UI INTERFACE ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2622/2622649.png", width=100)
    st.markdown("### Developer")
    st.markdown("**Joel Suarez**")
    st.markdown("Analytics Engineer")
    st.divider()
    st.markdown("[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/joel-f-suarez/)")
    st.markdown("[![GitHub](https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white)](https://github.com/joelsuarez33/portfolio-analytics-options)")
    st.divider()
    st.caption("🚀 Tech Stack: Python | GCP | dbt | Streamlit")

st.title("📊 Quantitative Options Terminal (GGAL)")
spot = get_live_spot()

if not spot:
    st.error("Live market data unavailable.")
    st.stop()

st.metric(label="GGAL Spot Price (BCBA)", value=f"${spot:.2f}")

with st.spinner('Querying Data Warehouse...'):
    df = load_bq_data()

if df.empty:
    st.warning("No data found in BigQuery.")
    st.stop()

# Base Calculations
df['t_years'] = df['dte'] / 365.0
df['vi'] = df.apply(lambda r: calculate_iv_safe(r['price'], spot, r['strike'], r['t_years'], r['type']), axis=1)

tab1, tab2 = st.tabs(["Market Monitor & Synthetics", "Spread Optimizer (Kelly Criterion)"])

with tab1:
    st.header("Real-Time Market Monitor")
    dtes = sorted(df['dte'].unique())
    
    for dte in dtes:
        with st.expander(f"Days to Expiration: {dte}", expanded=True):
            block = df[df['dte'] == dte].copy()
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**CALLS**")
                calls = block[block['type'] == 'c'][['ticker', 'strike', 'price', 'vi', 'volume']].sort_values('strike')
                st.dataframe(calls.style.format({'strike': '${:.2f}', 'price': '${:.2f}', 'vi': '{:.2%}'}), hide_index=True, use_container_width=True)
                
            with col2:
                st.markdown("**PUTS**")
                puts = block[block['type'] == 'p'][['ticker', 'strike', 'price', 'vi', 'volume']].sort_values('strike')
                st.dataframe(puts.style.format({'strike': '${:.2f}', 'price': '${:.2f}', 'vi': '{:.2%}'}), hide_index=True, use_container_width=True)
            
            # Synthetic Arbitrage (APR Monitoring)
            if not calls.empty and not puts.empty:
                merged = pd.merge(calls, puts, on='strike', suffixes=('_c', '_p'))
                merged = merged[(merged['volume_c'] > 0) & (merged['volume_p'] > 0)].copy()
                if not merged.empty:
                    merged['synthetic'] = merged['strike'] + merged['price_c'] - merged['price_p']
                    merged['yield'] = (merged['synthetic'] / spot) - 1
                    merged['apr'] = merged['yield'] * (365 / dte)
                    
                    st.markdown("**Synthetic APR (Arbitrage Monitor)**")
                    st.dataframe(merged[['strike', 'price_c', 'price_p', 'synthetic', 'apr']].style.format({
                        'strike': '${:.2f}', 'price_c': '${:.2f}', 'price_p': '${:.2f}', 'synthetic': '${:.2f}', 'apr': '{:.2%}'
                    }), hide_index=True)

with tab2:
    st.header("Structural Risk Analysis")
    st.info("Filtering for mathematical edge using Black-Scholes & Kelly Criterion on 1:1 Vertical Spreads.")
    
    total_results = []
    for dte in dtes:
        df_dte = df[df['dte'] == dte].copy()
        vol_c = df_dte[df_dte['type'] == 'c']['volume'].sum()
        vol_p = df_dte[df_dte['type'] == 'p']['volume'].sum()
        
        # Filter for liquidity (Top 1% volume per DTE)
        df_filt = pd.concat([
            df_dte[(df_dte['type'] == 'c') & (df_dte['volume'] >= 0.01 * vol_c)],
            df_dte[(df_dte['type'] == 'p') & (df_dte['volume'] >= 0.01 * vol_p)]
        ])
        
        if df_filt.empty: continue
        
        # Evaluate 4 spread types
        scenarios = [
            evaluate_spreads(df_filt, spot, 'c', 'debit', dte),
            evaluate_spreads(df_filt, spot, 'p', 'debit', dte),
            evaluate_spreads(df_filt, spot, 'c', 'credit', dte),
            evaluate_spreads(df_filt, spot, 'p', 'credit', dte)
        ]
        
        valid = [s for s in scenarios if s is not None]
        if valid:
            temp_df = pd.DataFrame(valid)
            temp_df.insert(0, 'DTE', dte) 
            total_results.append(temp_df)
            
    if total_results:
        final_df = pd.concat(total_results, ignore_index=True).sort_values(by=['Kelly'], ascending=False)
        st.dataframe(
            final_df.style.format({
                'K_Long': '${:.2f}', 'K_Short': '${:.2f}',
                'Max_Risk': '${:.2f}', 'Max_Profit': '${:.2f}',
                'R/R': '{:.2f}', 'POP': '{:.2%}',
                'EV': '${:.2f}', 'Kelly': '{:.2%}'
            }),
            hide_index=True,
            use_container_width=True
        )
    else:
        st.warning("No spreads with positive expected value found under current liquidity conditions.")
