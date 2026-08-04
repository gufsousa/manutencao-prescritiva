from __future__ import annotations

import pandas as pd
import streamlit as st

from src.mongo_store import STORE
from src.sidebar import render_shared_sidebar
from src.ui import hero, inject_theme, metric_card


inject_theme()
render_shared_sidebar(current_page="observabilidade")
hero("Observabilidade", "Logs do agente, status do armazenamento e rastreabilidade das execucoes.", eyebrow="tracing operacional")

status = STORE.ping()
counts = STORE.get_counts()
logs_df = pd.DataFrame(STORE.find_all("logs", limit=500))
benchmarks_df = pd.DataFrame(STORE.find_all("benchmarks", limit=500))

col1, col2, col3, col4 = st.columns(4)
with col1:
    metric_card("Modo", status.get("mode", "local"))
with col2:
    metric_card("Conectado", "Sim" if status.get("connected") else "Nao", tone="green" if status.get("connected") else "amber")
with col3:
    metric_card("Logs", str(counts["logs"]))
with col4:
    metric_card("Benchmarks", str(counts["benchmarks"]), tone="amber")

st.markdown("### Status do storage")
st.json(status, expanded=True)

st.markdown("### Logs de inferencia")
if not logs_df.empty:
    st.dataframe(logs_df, width="stretch", hide_index=True)
else:
    st.info("Nenhum log de inferencia disponivel.")

st.markdown("### Logs de benchmark")
if not benchmarks_df.empty:
    st.dataframe(benchmarks_df, width="stretch", hide_index=True)
else:
    st.info("Nenhum log de benchmark disponivel.")
