from __future__ import annotations

from pathlib import Path
import json


ROOT = Path(__file__).resolve().parent.parent
NOTEBOOK_PATH = ROOT / "notebooks" / "02_benchmark_tecnicas_inferencia_llm_vs_numericas.ipynb"


def md_cell(source: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": source.splitlines(keepends=True),
    }


def code_cell(source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source.splitlines(keepends=True),
    }


cells = [
    md_cell(
        """# Benchmark de Tecnicas de Inferencia: numericas vs LLM total com vetores

Este notebook reutiliza a mesma base logica do benchmark executavel do repositorio, evitando drift entre notebook exploratorio e script de avaliacao.
"""
    ),
    code_cell(
        """from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import plotly.express as px
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score

ROOT = Path.cwd().resolve().parent if Path.cwd().name == "notebooks" else Path.cwd().resolve()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.benchmark_shared import (
    BENCHMARK_FAMILIES,
    GROQ_MODEL,
    OLLAMA_MODEL,
    TOTAL_EXPECTED_SAMPLES,
    build_reference_artifacts,
    event_payload_from_row,
    predict_centroid_euclidean,
    predict_cosine_knn,
    predict_euclidean_knn,
    predict_llm_vector_rag,
    predict_mahalanobis_weighted_knn,
    predict_text_vector_vote,
    prepare_data,
)
"""
    ),
    code_cell(
        """benchmark_df, reference_df = prepare_data()
artifacts = build_reference_artifacts(reference_df)
scaler = artifacts["scaler"]
reference_text_records = artifacts["reference_text_records"]
centroid_model = artifacts["centroid_model"]

display(benchmark_df[["id", "canonical_fault", "rpm", "temperature_c", "x_rms_velocity_mm_s", "z_rms_velocity_mm_s"]].head())
print({"benchmark_rows": len(benchmark_df), "reference_rows": len(reference_df), "expected_rows": TOTAL_EXPECTED_SAMPLES})
"""
    ),
    code_cell(
        """records = []
llm_variants = [
    ("llm_vector_rag_groq", "groq", GROQ_MODEL),
    ("llm_vector_rag_ollama_small", "ollama", OLLAMA_MODEL),
]

for _, row in benchmark_df.iterrows():
    event = event_payload_from_row(row)
    true_fault = row["canonical_fault"]

    statistical_results = [
        ("euclidean_knn", predict_euclidean_knn(event, reference_df, scaler)),
        ("mahalanobis_weighted_knn", predict_mahalanobis_weighted_knn(event, reference_df, scaler)),
        ("cosine_knn", predict_cosine_knn(event, reference_df, scaler)),
        ("centroid_euclidean", predict_centroid_euclidean(event, reference_df, scaler, centroid_model)),
        ("text_vector_vote", predict_text_vector_vote(event, reference_text_records)),
    ]

    for technique, result in statistical_results:
        records.append(
            {
                "sample_id": int(row["id"]),
                "true_fault": true_fault,
                "technique": technique,
                "provider": "local",
                "model": "deterministic",
                "predicted_fault": result["predicted_fault"],
                "confidence_proxy": result["confidence_proxy"],
                "elapsed_ms": result["elapsed_ms"],
                "correct": result["predicted_fault"] == true_fault,
            }
        )

    for technique, provider, model in llm_variants:
        result = predict_llm_vector_rag(event, provider, model, reference_text_records, BENCHMARK_FAMILIES)
        records.append(
            {
                "sample_id": int(row["id"]),
                "true_fault": true_fault,
                "technique": technique,
                "provider": provider,
                "model": model,
                "predicted_fault": result["predicted_fault"],
                "confidence_proxy": result["confidence_proxy"],
                "elapsed_ms": result["elapsed_ms"],
                "correct": result["predicted_fault"] == true_fault,
            }
        )

results_df = pd.DataFrame(records)
results_df.head()
"""
    ),
    code_cell(
        """metrics_rows = []
for technique, part in results_df.groupby("technique"):
    metrics_rows.append(
        {
            "technique": technique,
            "provider": part["provider"].iloc[0],
            "model": part["model"].iloc[0],
            "rows": len(part),
            "accuracy": round(accuracy_score(part["true_fault"], part["predicted_fault"]), 4),
            "macro_f1": round(f1_score(part["true_fault"], part["predicted_fault"], average="macro"), 4),
            "avg_latency_ms": round(part["elapsed_ms"].mean(), 3),
        }
    )

metrics_df = pd.DataFrame(metrics_rows).sort_values(["accuracy", "macro_f1", "avg_latency_ms"], ascending=[False, False, True])
display(metrics_df)
"""
    ),
    code_cell(
        """fig_acc = px.bar(metrics_df, x="technique", y="accuracy", color="technique", text="accuracy", title="Acuracia por tecnica")
fig_acc.update_layout(showlegend=False)
fig_acc.show()

fig_f1 = px.bar(metrics_df, x="technique", y="macro_f1", color="technique", text="macro_f1", title="Macro-F1 por tecnica")
fig_f1.update_layout(showlegend=False)
fig_f1.show()

fig_latency = px.bar(metrics_df, x="technique", y="avg_latency_ms", color="technique", text="avg_latency_ms", title="Latencia media por tecnica")
fig_latency.update_layout(showlegend=False)
fig_latency.show()
"""
    ),
    code_cell(
        """for technique in results_df["technique"].unique():
    part = results_df[results_df["technique"] == technique].copy()
    labels = sorted(set(part["true_fault"]).union(set(part["predicted_fault"])))
    cm = confusion_matrix(part["true_fault"], part["predicted_fault"], labels=labels)
    cm_df = pd.DataFrame(cm, index=[f"real::{x}" for x in labels], columns=[f"pred::{x}" for x in labels])
    print(f"\\n=== {technique} ===")
    display(cm_df)
    print(classification_report(part["true_fault"], part["predicted_fault"], labels=labels, zero_division=0))
"""
    ),
    md_cell(
        """## Observacao

O notebook importa a mesma logica de `scripts/benchmark_shared.py` usada pelo benchmark executavel. Isso reduz manutencao duplicada e ajuda a manter consistencia entre exploracao e relatorio oficial.
"""
    ),
]


notebook = {
    "cells": cells,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {
            "name": "python",
            "version": "3.14",
        },
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

NOTEBOOK_PATH.parent.mkdir(parents=True, exist_ok=True)
NOTEBOOK_PATH.write_text(json.dumps(notebook, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Notebook gerado em: {NOTEBOOK_PATH}")
