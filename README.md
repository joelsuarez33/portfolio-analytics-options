# Quantitative Options Terminal (GGAL)

Pipeline End-to-End de Analytics Engineering enfocado en el mercado financiero argentino.

## Arquitectura Técnica
1. **Extracción (GCP):** Cloud Functions orquestadas vía Cloud Scheduler capturan la cadena de opciones en tiempo real desde APIs financieras.
2. **Carga (BigQuery):** Almacenamiento columnar de datos crudos (JSON).
3. **Transformación (dbt):** Modelado dimensional, parsing con RegEx, ecuaciones de paridad Call-Put y Data Quality Testing.
4. **Análisis (Python/Streamlit):** Modelos estocásticos aplicando Black-Scholes-Merton (BSM) y Criterio de Kelly para evaluar ventaja estadística matemática (Edge) en spreads 1:1.

Desarrollado con Python, SQL, dbt y Google Cloud Platform.