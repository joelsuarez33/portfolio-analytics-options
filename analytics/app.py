import streamlit as st
import pandas as pd
import numpy as np
import itertools
from google.cloud import bigquery
from google.oauth2 import service_account
from scipy.stats import norm
from py_vollib.black_scholes.implied_volatility import implied_volatility
import requests

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Monitor Cuantitativo GGAL", layout="wide")
R_RISK_FREE = 0.34

# --- EXTRACCIÓN Y CACHÉ ---
@st.cache_data(ttl=300)
def obtener_spot_live():
    try:
        r = requests.get("https://data912.com/live/arg_stocks", timeout=5)
        return float(pd.DataFrame(r.json()).loc[lambda df: df['symbol'] == 'GGAL', 'c'].iloc[0])
    except:
        return None

@st.cache_data(ttl=300)
def cargar_datos_bq():
    # En producción (Streamlit Cloud), lee de st.secrets
    # Streamlit convierte el secreto configurado en la web a un diccionario de Python
    cred_dict = dict(st.secrets["gcp_service_account"])
    credentials = service_account.Credentials.from_service_account_info(cred_dict)
    
    # Inyectamos las credenciales al cliente de BigQuery
    client = bigquery.Client(credentials=credentials, project=cred_dict["project_id"])
    
    query = f"""
        SELECT 
            ticker, tipo, strike, precio, volumen, dte
        FROM `{cred_dict["project_id"]}.mercado_financiero_dev.fct_opciones_latest`
        WHERE dte > 0 AND precio > 0 AND volumen > 0
    """
    # Se asigna explícitamente a un dataframe y se retorna
    df_raw = client.query(query).to_dataframe()
    return df_raw

# --- FUNCIONES MATEMÁTICAS ---
def pop_bs(spot, be, t_years, sigma, es_alcista):
    if t_years <= 0 or pd.isna(sigma) or sigma == 0: return 0
    d2 = (np.log(spot / be) + (R_RISK_FREE - (sigma**2) / 2) * t_years) / (sigma * np.sqrt(t_years))
    return norm.cdf(d2) if es_alcista else norm.cdf(-d2)

def evaluar_spreads(df_opts, spot, flag, tipo_flujo, dte):
    opts = df_opts[df_opts['tipo'] == flag].sort_values('strike')
    if len(opts) < 2: return None
    
    t_years = dte / 365.0
    spreads = []
    
    for (i1, row1), (i2, row2) in itertools.combinations(opts.iterrows(), 2):
        k1, p1, vi1 = row1['strike'], row1['precio'], row1['vi']
        k2, p2, vi2 = row2['strike'], row2['precio'], row2['vi']
        
        sigma_avg = np.mean([vi1, vi2]) if pd.notna(vi1) and pd.notna(vi2) else 0.45
        ancho_base = k2 - k1

        if flag == 'c':
            dif_prima = p1 - p2 
            if tipo_flujo == 'debit':
                est, k_long, k_short, costo, max_prof = 'Bull Call (Deb)', k1, k2, dif_prima, ancho_base - dif_prima
                be, alcista = k1 + costo, True
            else:
                est, k_long, k_short, costo, max_prof = 'Bear Call (Cred)', k2, k1, ancho_base - dif_prima, dif_prima 
                be, alcista = k1 + max_prof, False
        else:
            dif_prima = p2 - p1 
            if tipo_flujo == 'debit':
                est, k_long, k_short, costo, max_prof = 'Bear Put (Deb)', k2, k1, dif_prima, ancho_base - dif_prima
                be, alcista = k2 - costo, False
            else:
                est, k_long, k_short, costo, max_prof = 'Bull Put (Cred)', k1, k2, ancho_base - dif_prima, dif_prima
                be, alcista = k2 - max_prof, True

        if costo > 0 and max_prof > 0:
            pop = pop_bs(spot, be, t_years, sigma_avg, alcista)
            ev = (pop * max_prof) - ((1 - pop) * costo)
            rr = max_prof / costo
            kelly = (pop - ((1 - pop) / rr)) if rr > 0 else 0
            
            if ev > 0 and kelly > 0 and pop > 0.20:
                spreads.append({
                    'Estrategia': est, 'K_Long': k_long, 'K_Short': k_short,
                    'Riesgo_Max': costo, 'Benef_Max': max_prof, 'R/R': rr,
                    'POP': pop, 'EV': ev, 'Kelly': kelly
                })

    if not spreads: return None
    df_s = pd.DataFrame(spreads)
    return df_s.loc[df_s['Kelly'].idxmax()]

# --- INTERFAZ UI ---
st.title("📊 Terminal Analítica de Opciones GGAL")
spot = obtener_spot_live()

if not spot:
    st.error("Error obteniendo Spot.")
    st.stop()

st.metric(label="Precio Spot GGAL", value=f"${spot:.2f}")

with st.spinner('Consumiendo DWH...'):
    df = cargar_datos_bq()

if df.empty:
    st.warning("Sin datos en la base.")
    st.stop()

# Cálculo base de VI
df['t_years'] = df['dte'] / 365.0
df['vi'] = df.apply(lambda r: implied_volatility(r['precio'], spot, r['strike'], r['t_years'], R_RISK_FREE, r['tipo']) if r['tipo'] in ['c','p'] else np.nan, axis=1)

# Estructura de pestañas
tab1, tab2 = st.tabs(["Monitor General y Sintéticos", "Optimizador de Spreads (Kelly)"])

with tab1:
    st.header("Monitor de Mercado")
    dtes = sorted(df['dte'].unique())
    
    for dte in dtes:
        st.subheader(f"Días al Vencimiento: {dte}")
        bloque = df[df['dte'] == dte].copy()
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**CALLS**")
            calls = bloque[bloque['tipo'] == 'c'][['ticker', 'strike', 'precio', 'vi', 'volumen']].sort_values('strike')
            st.dataframe(calls.style.format({'strike': '${:.2f}', 'precio': '${:.2f}', 'vi': '{:.2%}'}), hide_index=True, use_container_width=True)
            
        with col2:
            st.markdown("**PUTS**")
            puts = bloque[bloque['tipo'] == 'p'][['ticker', 'strike', 'precio', 'vi', 'volumen']].sort_values('strike')
            st.dataframe(puts.style.format({'strike': '${:.2f}', 'precio': '${:.2f}', 'vi': '{:.2%}'}), hide_index=True, use_container_width=True)
            
        # Tasas Sintéticas
        if not calls.empty and not puts.empty:
            merged = pd.merge(calls, puts, on='strike', suffixes=('_call', '_put'))
            merged = merged[(merged['volumen_call'] > 0) & (merged['volumen_put'] > 0)].copy()
            if not merged.empty:
                merged['sintetico'] = merged['strike'] + merged['precio_call'] - merged['precio_put']
                merged['rendimiento'] = (merged['sintetico'] / spot) - 1
                merged['tna'] = merged['rendimiento'] * (365 / dte)
                
                res_sint = merged[['strike', 'precio_call', 'precio_put', 'sintetico', 'tna']].copy()
                st.markdown("**Tasas Sintéticas (TNA Implícita)**")
                st.dataframe(res_sint.style.format({'strike': '${:.2f}', 'precio_call': '${:.2f}', 'precio_put': '${:.2f}', 'sintetico': '${:.2f}', 'tna': '{:.2%}'}), hide_index=True)
        st.divider()

with tab2:
    st.header("Análisis de Riesgo Estructural")
    st.info("Filtra las combinaciones de opciones buscando un Edge matemático positivo aplicando Black-Scholes y el Criterio de Kelly sobre spreads 1:1.")
    
    dtes = sorted(df['dte'].unique())
    resultados_totales = []
    
    for dte in dtes:
        df_dte = df[df['dte'] == dte].copy()
        vol_c = df_dte[df_dte['tipo'] == 'c']['volumen'].sum()
        vol_p = df_dte[df_dte['tipo'] == 'p']['volumen'].sum()
        
        df_filt = pd.concat([
            df_dte[(df_dte['tipo'] == 'c') & (df_dte['volumen'] >= 0.01 * vol_c)],
            df_dte[(df_dte['tipo'] == 'p') & (df_dte['volumen'] >= 0.01 * vol_p)]
        ])
        
        if df_filt.empty: continue
        
        res = [
            evaluar_spreads(df_filt, spot, 'c', 'debit', dte),
            evaluar_spreads(df_filt, spot, 'p', 'debit', dte),
            evaluar_spreads(df_filt, spot, 'c', 'credit', dte),
            evaluar_spreads(df_filt, spot, 'p', 'credit', dte)
        ]
        valid_res = [r for r in res if r is not None]
        
        if valid_res:
            temp_df = pd.DataFrame(valid_res)
            temp_df.insert(0, 'DTE', dte) 
            resultados_totales.append(temp_df)
            
    if resultados_totales:
        df_final = pd.concat(resultados_totales, ignore_index=True)
        df_final = df_final.sort_values(by=['Kelly'], ascending=False)
        
        st.dataframe(
            df_final.style.format({
                'K_Long': '${:.2f}', 'K_Short': '${:.2f}',
                'Riesgo_Max': '${:.2f}', 'Benef_Max': '${:.2f}',
                'R/R': '{:.2f}', 'POP': '{:.2%}',
                'EV': '${:.2f}', 'Kelly': '{:.2%}'
            }),
            hide_index=True,
            use_container_width=True
        )
    else:
        st.warning("No se encontraron spreads con ventaja estadística bajo las condiciones actuales de liquidez.")