from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
from sklearn.metrics import accuracy_score, f1_score

from scripts.run_full_inference_benchmark import (
    BENCHMARK_FAMILIES,
    DETAILS_CSV_PATH,
    OLLAMA_MODEL,
    REPORTS_DIR,
    build_reference_artifacts,
    event_payload_from_row,
    prepare_data,
    predict_llm_vector_rag,
)


SWEEP_MODELS = [
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
    "qwen/qwen3.6-27b",
]

SWEEP_CSV_PATH = REPORTS_DIR / "benchmark_groq_model_sweep_results_2026-08-05.csv"
SWEEP_METRICS_PATH = REPORTS_DIR / "benchmark_groq_model_sweep_metrics_2026-08-05.csv"
SWEEP_REPORT_PATH = REPORTS_DIR / "10_benchmark_groq_model_sweep_2026-08-05.md"


def run_sweep() -> tuple[pd.DataFrame, pd.DataFrame]:
    benchmark_df, reference_df = prepare_data()
    artifacts = build_reference_artifacts(reference_df)
    reference_text_records = artifacts["reference_text_records"]

    records: list[dict] = []
    total = len(benchmark_df)
    for model in SWEEP_MODELS:
        print(f"== Modelo Groq: {model} ==")
        try:
            for sample_index, (_, row) in enumerate(benchmark_df.iterrows(), start=1):
                event = event_payload_from_row(row)
                true_fault = row["canonical_fault"]
                print(f"  [{sample_index}/{total}] sample_id={int(row['id'])} true_fault={true_fault}")
                result = predict_llm_vector_rag(event, "groq", model, reference_text_records)
                records.append(
                    {
                        "sample_id": int(row["id"]),
                        "true_fault": true_fault,
                        "provider": "groq",
                        "model": model,
                        "predicted_fault": result["predicted_fault"],
                        "confidence_proxy": result["confidence_proxy"],
                        "elapsed_ms": result["elapsed_ms"],
                        "correct": result["predicted_fault"] == true_fault,
                        "raw_response": result["raw_response"],
                        "usage": json.dumps(result["usage"], ensure_ascii=False),
                    }
                )
        except Exception as exc:
            print(f"  !! modelo {model} falhou: {exc}")
        checkpoint = pd.DataFrame(records)
        checkpoint.to_csv(SWEEP_CSV_PATH, index=False, encoding="utf-8-sig")
        print(f"Checkpoint salvo em {SWEEP_CSV_PATH}")

    details_df = pd.DataFrame(records)
    metrics_rows = []
    for model, part in details_df.groupby("model"):
        metrics_rows.append(
            {
                "provider": "groq",
                "model": model,
                "rows": len(part),
                "accuracy": round(accuracy_score(part["true_fault"], part["predicted_fault"]), 4),
                "macro_f1": round(f1_score(part["true_fault"], part["predicted_fault"], average="macro"), 4),
                "avg_latency_ms": round(part["elapsed_ms"].mean(), 3),
            }
        )
    metrics_df = pd.DataFrame(metrics_rows).sort_values(["accuracy", "macro_f1", "avg_latency_ms"], ascending=[False, False, True])
    return details_df, metrics_df


def dataframe_to_markdown(df: pd.DataFrame) -> str:
    headers = [str(col) for col in df.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for _, row in df.iterrows():
        values = []
        for value in row.tolist():
            if isinstance(value, float):
                values.append(f"{value:.4f}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def render_report(metrics_df: pd.DataFrame) -> str:
    previous_metrics = pd.read_csv(REPORTS_DIR / "benchmark_full_inference_metrics_2026-08-05.csv")
    ollama_ref = previous_metrics[previous_metrics["technique"] == "llm_vector_rag_ollama_small"].iloc[0]
    current_ref = previous_metrics[previous_metrics["technique"] == "llm_vector_rag_groq"].iloc[0]

    lines = [
        "# Sweep de Modelos Groq para llm_vector_rag",
        "",
        "## Escopo",
        "",
        "- Avaliacao em 50 amostras balanceadas.",
        f"- Familias: {', '.join(BENCHMARK_FAMILIES)}.",
        "- Objetivo: comparar diferentes modelos Groq no mesmo pipeline `llm_vector_rag`.",
        "",
        "## Modelos testados",
        "",
    ]
    for model in SWEEP_MODELS:
        lines.append(f"- `{model}`")
    lines.extend(
        [
            "",
            "## Resultado consolidado",
            "",
            dataframe_to_markdown(metrics_df),
            "",
            "## Referencias cruzadas",
            "",
            f"- Referencia anterior Groq `llama-3.1-8b-instant`: acuracia **{current_ref['accuracy']:.4f}**, macro-F1 **{current_ref['macro_f1']:.4f}**.",
            f"- Referencia local Ollama `{OLLAMA_MODEL}`: acuracia **{ollama_ref['accuracy']:.4f}**, macro-F1 **{ollama_ref['macro_f1']:.4f}**.",
            "",
            "## Leitura tecnica",
            "",
            "- Se um modelo Groq maior superar o `llama-3.1-8b-instant`, isso indica que o pipeline `llm_vector_rag` ainda tem margem de ganho por capacidade de raciocinio e aderencia de sintese.",
            "- Se a melhora for pequena, reforca que o gargalo principal nao esta apenas no modelo, mas na representacao do evento, na recuperacao e no tipo de supervisao disponivel.",
            "- O contraste com o Ollama local mostra a perda de qualidade ao trazer o mesmo paradigma para um modelo menor em execucao edge.",
            "",
            f"- Relatorio gerado em `{datetime.now(UTC).isoformat()}`.",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    details_df, metrics_df = run_sweep()
    SWEEP_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    details_df.to_csv(SWEEP_CSV_PATH, index=False, encoding="utf-8-sig")
    metrics_df.to_csv(SWEEP_METRICS_PATH, index=False, encoding="utf-8-sig")
    SWEEP_REPORT_PATH.write_text(render_report(metrics_df), encoding="utf-8")
    print(f"Resultados: {SWEEP_CSV_PATH}")
    print(f"Metricas: {SWEEP_METRICS_PATH}")
    print(f"Relatorio: {SWEEP_REPORT_PATH}")
    print(metrics_df.to_string(index=False))


if __name__ == "__main__":
    main()
