from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.history_service import HISTORY_SERVICE
from src.mongo_store import STORE
from src.sidebar import render_shared_sidebar
from src.ui import hero, inject_theme, metric_card


inject_theme()
render_shared_sidebar(current_page="dashboard")
hero(
    "BI de Inferencias",
    "Superficie executiva para PCP e coordenacao: volume, latencia, distribuicao de falhas e comportamento do copiloto.",
    eyebrow="business intelligence",
)

history_metrics = HISTORY_SERVICE.dataset_metrics()
logs = pd.DataFrame(STORE.find_all("logs"))
counts = STORE.get_counts()

col1, col2, col3, col4 = st.columns(4)
with col1:
    metric_card("Inferencias registradas", str(counts["logs"]))
with col2:
    metric_card("Benchmarks", str(counts["benchmarks"]), tone="amber")
with col3:
    metric_card("Chunks vetoriais", str(counts["document_chunks"]), tone="green")
with col4:
    refusal_count = int((logs["refusal_reason"].fillna("") != "").sum()) if not logs.empty and "refusal_reason" in logs else 0
    metric_card("Recusas", str(refusal_count), tone="amber")

metrics_row_1, metrics_row_2, metrics_row_3, metrics_row_4 = st.columns(4)
with metrics_row_1:
    metric_card("Falhas reais", str(history_metrics["fault_labels"]), tone="green")
with metrics_row_2:
    metric_card("Estados operacionais", str(history_metrics["state_labels"]), tone="amber")
with metrics_row_3:
    metric_card("Linhas com falha", f"{history_metrics['fault_rows']:,}".replace(",", "."), tone="green")
with metrics_row_4:
    metric_card("Linhas de estado", f"{history_metrics['state_rows']:,}".replace(",", "."), tone="amber")

left, right = st.columns((1.1, 0.9))
with left:
    fault_counts_df = pd.DataFrame(
        [{"fault": key, "count": value} for key, value in history_metrics["real_fault_counts"].items()]
    ).sort_values("count", ascending=False).head(15)
    fig_faults = px.bar(
        fault_counts_df,
        x="fault",
        y="count",
        title="Distribuicao das falhas reais no dataset",
        color="count",
        color_continuous_scale="Blues",
    )
    fig_faults.update_layout(height=440, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_faults, width="stretch")

with right:
    rpm_df = pd.DataFrame([{"rpm": str(key), "count": value} for key, value in history_metrics["rpm_counts"].items()])
    fig_rpm = px.pie(rpm_df, names="rpm", values="count", title="Distribuicao por RPM", hole=0.52)
    fig_rpm.update_layout(height=440, paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_rpm, width="stretch")

bottom_left, bottom_right = st.columns((1.1, 0.9))
with bottom_left:
    state_counts_df = pd.DataFrame(
        [{"estado": key, "count": value} for key, value in history_metrics["state_counts"].items()]
    ).sort_values("count", ascending=False)
    if not state_counts_df.empty:
        fig_states = px.bar(
            state_counts_df,
            x="estado",
            y="count",
            title="Estados operacionais no dataset",
            color="count",
            color_continuous_scale="Oranges",
        )
        fig_states.update_layout(height=420, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_states, width="stretch")
    else:
        st.info("Nenhum estado operacional detectado no dataset.")

with bottom_right:
    if not logs.empty:
        probable_fault_df = logs["probable_fault"].fillna("nao_informado").value_counts().reset_index()
        probable_fault_df.columns = ["probable_fault", "count"]
        fig_logs = px.bar(
            probable_fault_df,
            x="probable_fault",
            y="count",
            title="Falhas propostas pelo agente",
            color="count",
            color_continuous_scale="Sunsetdark",
        )
        fig_logs.update_layout(height=420, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_logs, width="stretch")
    else:
        st.info("Nenhuma inferencia registrada ainda.")

latency_left, latency_right = st.columns((1.1, 0.9))
with latency_left:
    if not logs.empty and "elapsed_ms" in logs:
        fig_latency = px.box(logs, y="elapsed_ms", title="Latencia das inferencias (ms)", points="all")
        fig_latency.update_layout(height=420, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_latency, width="stretch")
    else:
        st.info("Sem latencia registrada ainda.")

with latency_right:
    st.info(
        "No dataset completo ha 12 falhas reais canonicas e 5 estados operacionais. "
        "O BI agora separa esses dois grupos para nao tratar `normal`, `motor_desligado` e similares como falhas."
    )
