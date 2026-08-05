from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import plotly.express as px


REPORTS_DIR = ROOT / "docs" / "analise_markdown"
METRICS_CSV_PATH = REPORTS_DIR / "benchmark_full_inference_metrics_2026-08-05.csv"
DETAILS_CSV_PATH = REPORTS_DIR / "benchmark_full_inference_results_2026-08-05.csv"
GRAPHS_DIR = REPORTS_DIR / "benchmark_graficos_2026-08-05"


def main() -> None:
    if not METRICS_CSV_PATH.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {METRICS_CSV_PATH}")
    if not DETAILS_CSV_PATH.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {DETAILS_CSV_PATH}")

    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    metrics_df = pd.read_csv(METRICS_CSV_PATH)
    details_df = pd.read_csv(DETAILS_CSV_PATH)

    fig_acc = px.bar(
        metrics_df,
        x="technique",
        y="accuracy",
        color="provider",
        text="accuracy",
        title="Acuracia por tecnica",
    )
    fig_acc.update_layout(template="plotly_white")
    fig_acc.write_html(GRAPHS_DIR / "01_acuracia_por_tecnica.html")

    fig_f1 = px.bar(
        metrics_df,
        x="technique",
        y="macro_f1",
        color="provider",
        text="macro_f1",
        title="Macro-F1 por tecnica",
    )
    fig_f1.update_layout(template="plotly_white")
    fig_f1.write_html(GRAPHS_DIR / "02_macro_f1_por_tecnica.html")

    fig_latency = px.bar(
        metrics_df,
        x="technique",
        y="avg_latency_ms",
        color="provider",
        text="avg_latency_ms",
        title="Latencia media por tecnica (ms)",
    )
    fig_latency.update_layout(template="plotly_white")
    fig_latency.write_html(GRAPHS_DIR / "03_latencia_media_por_tecnica.html")

    family_rows = []
    for technique, part in details_df.groupby("technique"):
        for family, family_part in part.groupby("true_fault"):
            family_rows.append(
                {
                    "technique": technique,
                    "family": family,
                    "recall": round((family_part["predicted_fault"] == family_part["true_fault"]).mean(), 4),
                }
            )
    family_df = pd.DataFrame(family_rows)
    fig_recall = px.bar(
        family_df,
        x="family",
        y="recall",
        color="technique",
        barmode="group",
        title="Recall por familia de falha",
    )
    fig_recall.update_layout(template="plotly_white")
    fig_recall.write_html(GRAPHS_DIR / "04_recall_por_familia.html")

    llm_compare_df = metrics_df[metrics_df["technique"].isin(["llm_vector_rag_groq", "llm_vector_rag_ollama_small"])].copy()
    fig_llm = px.bar(
        llm_compare_df,
        x="technique",
        y=["accuracy", "macro_f1"],
        barmode="group",
        title="Comparacao direta do llm_vector_rag: Groq vs Ollama local",
    )
    fig_llm.update_layout(template="plotly_white")
    fig_llm.write_html(GRAPHS_DIR / "05_llm_vector_rag_groq_vs_ollama.html")

    if "ood_flag" in details_df.columns:
        ood_df = details_df[details_df["ood_flag"].notna()].copy()
        if not ood_df.empty:
            ood_rate_df = (
                ood_df.groupby("technique")["ood_flag"]
                .mean()
                .reset_index()
                .rename(columns={"ood_flag": "ood_rate"})
            )
            fig_ood = px.bar(
                ood_rate_df,
                x="technique",
                y="ood_rate",
                text="ood_rate",
                title="Taxa de sinalizacao OOD por tecnica",
            )
            fig_ood.update_layout(template="plotly_white")
            fig_ood.write_html(GRAPHS_DIR / "08_taxa_ood_por_tecnica.html")

    print(f"Graficos gerados em: {GRAPHS_DIR}")


if __name__ == "__main__":
    main()
