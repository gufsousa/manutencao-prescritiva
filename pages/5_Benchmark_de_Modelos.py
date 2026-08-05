from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from src.sidebar import render_shared_sidebar
from src.ui import hero, inject_theme, metric_card


inject_theme()
render_shared_sidebar(current_page="benchmark")
hero(
    "Resultados de Benchmark",
    "Painel estatico com os resultados consolidados dos benchmarks executados em 5 de agosto de 2026.",
    eyebrow="resultados consolidados",
)

DOCS_DIR = Path("docs/analise_markdown")
FULL_METRICS_PATH = DOCS_DIR / "benchmark_full_inference_metrics_2026-08-05.csv"
GROQ_SWEEP_PATH = DOCS_DIR / "benchmark_groq_model_sweep_metrics_2026-08-05.csv"
PYTHON_VS_MONGO_PATH = DOCS_DIR / "benchmark_llm_vector_rag_python_vs_mongo_metrics_2026-08-05.csv"

full_df = pd.read_csv(FULL_METRICS_PATH)
groq_df = pd.read_csv(GROQ_SWEEP_PATH)
backend_df = pd.read_csv(PYTHON_VS_MONGO_PATH)

best_full = full_df.sort_values(["accuracy", "macro_f1"], ascending=False).iloc[0]
best_groq = groq_df.sort_values(["accuracy", "macro_f1"], ascending=False).iloc[0]
mongo_row = backend_df[backend_df["backend"] == "mongo"].iloc[0]
python_row = backend_df[backend_df["backend"] == "python"].iloc[0]

col1, col2, col3, col4 = st.columns(4)
with col1:
    metric_card("Melhor tecnica", str(best_full["technique"]), tone="green")
with col2:
    metric_card("Accuracy lider", f"{best_full['accuracy']:.2f}", tone="amber")
with col3:
    metric_card("Melhor modelo Groq", str(best_groq["model"]), tone="green")
with col4:
    metric_card("Mongo vs Python", "mesma qualidade", tone="amber")

st.info(
    "Esta pagina mostra apenas os resultados finais ja consolidados. "
    "O benchmark funcional ao vivo foi removido da interface para a apresentacao."
)

st.markdown("### Benchmark completo de tecnicas")
st.dataframe(full_df, width="stretch", hide_index=True)

left, right = st.columns(2)
with left:
    fig_accuracy = px.bar(
        full_df.sort_values("accuracy", ascending=False),
        x="technique",
        y="accuracy",
        color="provider",
        title="Accuracy por tecnica",
    )
    fig_accuracy.update_layout(height=420, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_accuracy, width="stretch")

with right:
    fig_latency = px.bar(
        full_df.sort_values("avg_latency_ms"),
        x="technique",
        y="avg_latency_ms",
        color="provider",
        title="Latencia media por tecnica (ms)",
    )
    fig_latency.update_layout(height=420, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_latency, width="stretch")

st.markdown("### Sweep Groq no pipeline llm_vector_rag")
st.dataframe(groq_df, width="stretch", hide_index=True)

left, right = st.columns(2)
with left:
    fig_groq_acc = px.bar(
        groq_df.sort_values("accuracy", ascending=False),
        x="model",
        y="accuracy",
        color="model",
        title="Accuracy por modelo Groq",
    )
    fig_groq_acc.update_layout(height=420, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
    st.plotly_chart(fig_groq_acc, width="stretch")

with right:
    fig_groq_latency = px.bar(
        groq_df.sort_values("avg_latency_ms"),
        x="model",
        y="avg_latency_ms",
        color="model",
        title="Latencia media por modelo Groq (ms)",
    )
    fig_groq_latency.update_layout(height=420, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
    st.plotly_chart(fig_groq_latency, width="stretch")

st.markdown("### Python vs Mongo Atlas Vector Search")
st.dataframe(backend_df, width="stretch", hide_index=True)

left, right = st.columns(2)
with left:
    fig_backend_doc = px.bar(
        backend_df,
        x="backend",
        y="avg_doc_latency_ms",
        color="backend",
        title="Latencia media da recuperacao documental (ms)",
    )
    fig_backend_doc.update_layout(height=380, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
    st.plotly_chart(fig_backend_doc, width="stretch")

with right:
    comparison_df = pd.DataFrame(
        [
            {"metric": "accuracy", "python": python_row["accuracy"], "mongo": mongo_row["accuracy"]},
            {"metric": "macro_f1", "python": python_row["macro_f1"], "mongo": mongo_row["macro_f1"]},
            {"metric": "same_prediction_ratio", "python": 1.0, "mongo": mongo_row["same_prediction_ratio"]},
        ]
    )
    melted = comparison_df.melt(id_vars="metric", var_name="backend", value_name="value")
    fig_backend_quality = px.bar(
        melted,
        x="metric",
        y="value",
        color="backend",
        barmode="group",
        title="Qualidade final: Python vs Mongo",
    )
    fig_backend_quality.update_layout(height=380, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_backend_quality, width="stretch")

st.caption(
    "Leitura curta: na comparacao ponta a ponta com 20 amostras, Python e Mongo tiveram a mesma qualidade final; "
    "a diferenca observada ficou mais na latencia da recuperacao documental e na vantagem arquitetural de escalar a busca nativamente no banco."
)
