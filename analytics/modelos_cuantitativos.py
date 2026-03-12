import os
import json
import pandas as pd
import numpy as np
from google.cloud import bigquery
from google.oauth2 import service_account 
from scipy.stats import norm
from py_vollib.black_scholes.implied_volatility import implied_volatility
import requests

# Configuración inicial
PROJECT_ID = "portfolio-analytics-eng"
R_RISK_FREE = 0.34

def obtener_spot_live():
    """Obtiene el spot actual para los cálculos dinámicos de BSM."""
    try:
        r = requests.get("https://data912.com/live/arg_stocks", timeout=5)
        return float(pd.DataFrame(r.json()).loc[lambda df: df['symbol'] == 'GGAL', 'c'].iloc[0])
    except Exception as e:
        print(f"Error obteniendo Spot: {e}")
        return None

def calcular_probabilidad_bsm(spot, strike, t_years, sigma, es_call):
    """Calcula N(d2) para la probabilidad teórica de expiración ITM."""
    if t_years <= 0 or pd.isna(sigma) or sigma <= 0: return 0
    d2 = (np.log(spot / strike) + (R_RISK_FREE - (sigma**2) / 2) * t_years) / (sigma * np.sqrt(t_years))
    return norm.cdf(d2) if es_call else norm.cdf(-d2)

def main():
    spot = obtener_spot_live()
    if not spot: return
    print(f"--- INICIANDO MODELO CUANTITATIVO | SPOT: ${spot:.2f} ---")

    # 1. Resolución de Credenciales (Local vs CI/CD)
    gcp_sa_key = os.environ.get("GCP_SA_KEY")
    
    if gcp_sa_key:
        # Entorno GitHub Actions: Carga desde el secreto inyectado en memoria
        info = json.loads(gcp_sa_key)
        credentials = service_account.Credentials.from_service_account_info(info)
    else:
        # Entorno Local: Fallback a la ruta absoluta
        KEY_PATH = r"C:\Users\SUAREZJOEL(565)\py\portfolio-analytics-eng\.dbt\portfolio-analytics-eng-9acb68b83873.json"
        credentials = service_account.Credentials.from_service_account_file(KEY_PATH)

    client = bigquery.Client(credentials=credentials, project=PROJECT_ID)
    
    # 2. Extracción de datos ya modelados por dbt
    query = f"""
        SELECT 
            ticker, tipo, strike, precio, volumen, dte
        FROM `{PROJECT_ID}.mercado_financiero_dev.fct_opciones_latest`
    """
    
    df = client.query(query).to_dataframe()
    if df.empty:
        return print("No hay datos modelados en BigQuery para procesar.")

    df = df[df['dte'] > 0].copy()
    df['t_years'] = df['dte'] / 365.0

    # 3. Vectorización de Volatilidad Implícita
    def get_iv(row):
        try:
            return implied_volatility(row['precio'], spot, row['strike'], row['t_years'], R_RISK_FREE, row['tipo'])
        except:
            return np.nan

    df['iv'] = df.apply(get_iv, axis=1)
    df = df.dropna(subset=['iv'])

    # 4. Cálculo de Probabilidad (N(d2))
    df['pop'] = df.apply(lambda r: calcular_probabilidad_bsm(spot, r['strike'], r['t_years'], r['iv'], r['tipo'] == 'c'), axis=1)

    # 5. Modelado de Riesgo Asimétrico
    w_avg = df['precio'] * 0.30 
    l_avg = df['precio'] * 0.70

    df['ev'] = (df['pop'] * w_avg) - ((1 - df['pop']) * l_avg)
    
    df['rr_ratio'] = w_avg / l_avg
    df['kelly_f'] = np.where(
        df['rr_ratio'] > 0,
        df['pop'] - ((1 - df['pop']) / df['rr_ratio']),
        0
    )
    
    df_edge = df[(df['ev'] > 0) & (df['kelly_f'] > 0)].sort_values(by='kelly_f', ascending=False)
    
    pd.set_option('display.float_format', '{:.4f}'.format)
    print("\n[RESULTADOS] Top 5 Opciones con Esperanza Matemática Positiva:")
    print(df_edge[['ticker', 'strike', 'dte', 'iv', 'pop', 'ev', 'kelly_f']].head(5).to_string(index=False))

if __name__ == "__main__":
    main()