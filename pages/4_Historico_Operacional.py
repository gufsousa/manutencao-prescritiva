from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from src.history_service import HISTORY_SERVICE
from src.sidebar import render_shared_sidebar
from src.ui import hero, inject_theme, metric_card


inject_theme()
render_shared_sidebar(current_page="historico")
hero("Historico Operacional", "Exploracao do historico do banner.csv, ingestao e recuperacao de vizinhos similares.", eyebrow="base historica")

metrics = HISTORY_SERVICE.dataset_metrics()
col1, col2, col3 = st.columns(3)
with col1:
    metric_card("Registros", f"{metrics['rows']:,}".replace(",", "."))
with col2:
    metric_card("Rotulos crus", str(metrics["raw_faults"]), tone="amber")
with col3:
    metric_card("Familias canonicas", str(metrics["canonical_faults"]), tone="green")

if st.button("Reingestar historico completo", width="stretch"):
    result = HISTORY_SERVICE.ingest_history_to_mongo()
    st.success(f"Ingestao concluida com {result['inserted']} registros.")

df = HISTORY_SERVICE.load_history_frame()
fault_filter = st.selectbox("Filtrar familia canonica", [""] + sorted(df["canonical_fault"].dropna().unique().tolist()))
rpm_filter = st.selectbox("Filtrar rpm", [""] + sorted(str(item) for item in df["rpm"].dropna().unique().tolist()))
filtered_df = df.copy()
if fault_filter:
    filtered_df = filtered_df[filtered_df["canonical_fault"] == fault_filter]
if rpm_filter:
    filtered_df = filtered_df[filtered_df["rpm"].astype(str) == rpm_filter]

st.dataframe(
    filtered_df[["id", "created_at", "fault", "canonical_fault", "rpm", "temperature_c", "x_rms_velocity_mm_s", "z_rms_velocity_mm_s"]].head(200),
    width="stretch",
    hide_index=True,
)

st.markdown("### Teste de similaridade")
sample_options = filtered_df.head(20).to_dict(orient="records")
labels = {f"Evento {row['id']} | {row['canonical_fault']} | rpm={row['rpm']}": row for row in sample_options}
selected_label = st.selectbox("Escolha um evento para buscar similares", [""] + list(labels.keys()))
if selected_label and st.button("Buscar vizinhos", width="stretch"):
    event = labels[selected_label]
    result = HISTORY_SERVICE.search_similar_events(event, top_k=5)
    st.write(result.summary)
    st.dataframe(pd.DataFrame(result.neighbors), width="stretch", hide_index=True)
    st.dataframe(pd.DataFrame(result.fault_distribution), width="stretch", hide_index=True)
    st.code(json.dumps(event, ensure_ascii=False, indent=2, default=str), language="json")
