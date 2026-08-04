from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.agent_service import AGENT
from src.benchmark_service import BENCHMARK_SERVICE
from src.mongo_store import STORE
from src.sidebar import render_shared_sidebar
from src.ui import hero, inject_theme, metric_card


inject_theme()
render_shared_sidebar(current_page="benchmark")
hero("Benchmark de Modelos", "Comparacao de latencia e comportamento dos modelos Groq em cenarios curtos de manutencao.", eyebrow="benchmark controlado")

scenarios = BENCHMARK_SERVICE.sample_scenarios()
scenario_names = [scenario.name for scenario in scenarios]
selected_models = st.multiselect("Modelos", AGENT.available_models(), default=AGENT.available_models()[:1])
selected_scenarios = st.multiselect("Cenarios", scenario_names, default=scenario_names[: min(3, len(scenario_names))])

if st.button("Rodar benchmark", type="primary", width="stretch"):
    if not selected_models or not selected_scenarios:
        st.warning("Selecione ao menos um modelo e um cenario.")
    else:
        results = BENCHMARK_SERVICE.run(selected_models, selected_scenarios)
        st.session_state["benchmark_results"] = results
        st.success(f"Benchmark concluido com {len(results)} execucao(oes).")

results = st.session_state.get("benchmark_results") or STORE.find_all("benchmarks", limit=200)
results_df = pd.DataFrame(results)

col1, col2, col3 = st.columns(3)
with col1:
    metric_card("Execucoes", str(len(results_df)))
with col2:
    metric_card("Modelos avaliados", str(results_df["model"].nunique()) if not results_df.empty else "0", tone="amber")
with col3:
    avg_latency = round(results_df["elapsed_ms"].mean(), 2) if not results_df.empty else 0.0
    metric_card("Latencia media", f"{avg_latency} ms", tone="green")

if not results_df.empty:
    st.dataframe(results_df, width="stretch", hide_index=True)
    left, right = st.columns(2)
    with left:
        fig_latency = px.bar(
            results_df,
            x="scenario_name",
            y="elapsed_ms",
            color="model",
            barmode="group",
            title="Latencia por cenario",
        )
        fig_latency.update_layout(height=420, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_latency, width="stretch")
    with right:
        fig_confidence = px.bar(
            results_df,
            x="scenario_name",
            y="confidence_pct",
            color="model",
            barmode="group",
            title="Confianca reportada por cenario",
        )
        fig_confidence.update_layout(height=420, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_confidence, width="stretch")
else:
    st.info("Nenhum benchmark executado ainda.")
