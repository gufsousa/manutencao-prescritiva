from __future__ import annotations

import json
import math

import pandas as pd
import streamlit as st

from src.fault_semantics import get_label_kind
from src.history_service import HISTORY_SERVICE
from src.sidebar import render_shared_sidebar
from src.ui import hero, inject_theme, metric_card


inject_theme()
render_shared_sidebar(current_page="historico")
hero("Historico Operacional", "Exploracao do historico do banner.csv, ingestao e recuperacao de vizinhos similares.", eyebrow="base historica")

metrics = HISTORY_SERVICE.dataset_metrics()
storage_metrics = HISTORY_SERVICE.storage_metrics()
sample_target = math.ceil(storage_metrics["csv_rows"] * 0.20)
col1, col2, col3, col4 = st.columns(4)
with col1:
    metric_card("Registros", f"{metrics['rows']:,}".replace(",", "."))
with col2:
    metric_card("Rotulos crus", str(metrics["raw_faults"]), tone="amber")
with col3:
    metric_card("Familias canonicas", str(metrics["canonical_faults"]), tone="green")
with col4:
    metric_card("Estados operacionais", str(metrics["state_labels"]), tone="amber")

st.markdown("### Cobertura do historico persistido")
cover1, cover2, cover3 = st.columns(3)
with cover1:
    metric_card("CSV banner", f"{storage_metrics['csv_rows']:,}".replace(",", "."))
with cover2:
    metric_card("Persistido", f"{storage_metrics['stored_rows']:,}".replace(",", "."), tone="amber")
with cover3:
    metric_card("Cobertura", f"{storage_metrics['coverage_pct']}%", tone="green" if storage_metrics["is_fully_synced"] else "amber")

st.info(
    "Neste ambiente, o Mongo gratis usa uma amostra representativa de 20% do `banner.csv`, "
    "preservando cobertura temporal e de familias de falha para exploracao e busca historica."
)
st.caption(
    "Meta de amostragem: "
    f"{sample_target:,} registros. Atual: {storage_metrics['stored_rows']:,}.".replace(",", ".")
)

st.caption(
    "Camada semantica atual: "
    f"{metrics['fault_labels']} falhas reais e {metrics['state_labels']} estados operacionais canonicos."
)

if st.button("Reingestar amostra representativa de 20% pela pagina", width="stretch"):
    result = HISTORY_SERVICE.ingest_history_to_mongo(source="page", sample_fraction=0.20)
    st.success(f"Ingestao concluida com {result['inserted']} registros.")

df = HISTORY_SERVICE.load_history_frame()
df["semantic_kind"] = df["canonical_fault"].map(get_label_kind)
kind_filter = st.selectbox("Filtrar categoria semantica", ["", "fault", "state"])
fault_filter = st.selectbox("Filtrar familia canonica", [""] + sorted(df["canonical_fault"].dropna().unique().tolist()))
rpm_filter = st.selectbox("Filtrar rpm", [""] + sorted(str(item) for item in df["rpm"].dropna().unique().tolist()))
filtered_df = df.copy()
if kind_filter:
    filtered_df = filtered_df[filtered_df["semantic_kind"] == kind_filter]
if fault_filter:
    filtered_df = filtered_df[filtered_df["canonical_fault"] == fault_filter]
if rpm_filter:
    filtered_df = filtered_df[filtered_df["rpm"].astype(str) == rpm_filter]

st.dataframe(
    filtered_df[["id", "created_at", "fault", "canonical_fault", "semantic_kind", "rpm", "temperature_c", "x_rms_velocity_mm_s", "z_rms_velocity_mm_s"]].head(200),
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
