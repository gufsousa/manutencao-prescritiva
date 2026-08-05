from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score

from src.fault_semantics import canonicalize_fault_label, format_fault_label_pt
from scripts.benchmark_shared import (
    BENCHMARK_FAMILIES,
    GROQ_MODEL,
    OLLAMA_MODEL,
    SAMPLES_PER_FAMILY,
    TOTAL_EXPECTED_SAMPLES,
    build_reference_artifacts,
    dataframe_to_markdown,
    event_payload_from_row,
    predict_centroid_euclidean,
    predict_cosine_knn,
    predict_euclidean_knn,
    predict_llm_vector_rag,
    predict_mahalanobis_weighted_knn,
    predict_text_vector_vote,
    prepare_data,
)

REPORTS_DIR = ROOT / "docs" / "analise_markdown"
DETAILS_CSV_PATH = REPORTS_DIR / "benchmark_full_inference_results_2026-08-05.csv"
METRICS_CSV_PATH = REPORTS_DIR / "benchmark_full_inference_metrics_2026-08-05.csv"
REPORT_MD_PATH = REPORTS_DIR / "09_benchmark_full_inferencia_2026-08-05.md"

def run_benchmark() -> tuple[pd.DataFrame, pd.DataFrame]:
    benchmark_df, reference_df = prepare_data()
    artifacts = build_reference_artifacts(reference_df)
    scaler = artifacts["scaler"]
    reference_text_records = artifacts["reference_text_records"]
    centroid_model = artifacts["centroid_model"]

    records: list[dict[str, Any]] = []
    llm_variants = [
        ("llm_vector_rag_groq", "groq", GROQ_MODEL),
        ("llm_vector_rag_ollama_small", "ollama", OLLAMA_MODEL),
    ]

    for sample_index, (_, row) in enumerate(benchmark_df.iterrows(), start=1):
        event = event_payload_from_row(row)
        true_fault = canonicalize_fault_label(row["canonical_fault"])
        print(f"[{sample_index}/{TOTAL_EXPECTED_SAMPLES}] sample_id={int(row['id'])} true_fault={true_fault}")

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
                    "ood_flag": result.get("ood_flag"),
                    "ood_score": result.get("ood_score"),
                }
            )

        for technique, provider, model in llm_variants:
            print(f"  - running {technique} with {provider}:{model}")
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
                    "raw_response": result["raw_response"],
                    "usage": json.dumps(result["usage"], ensure_ascii=False),
                }
            )

        if sample_index % 5 == 0 or sample_index == TOTAL_EXPECTED_SAMPLES:
            checkpoint_df = pd.DataFrame(records)
            DETAILS_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
            checkpoint_df.to_csv(DETAILS_CSV_PATH, index=False, encoding="utf-8-sig")
            print(f"  checkpoint salvo com {len(checkpoint_df)} linhas em {DETAILS_CSV_PATH}")

    details_df = pd.DataFrame(records)

    metrics_rows = []
    for technique, part in details_df.groupby("technique"):
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
    return details_df, metrics_df


def family_recall_table(details_df: pd.DataFrame, technique: str) -> pd.DataFrame:
    part = details_df[details_df["technique"] == technique].copy()
    rows = []
    for family in BENCHMARK_FAMILIES:
        family_part = part[part["true_fault"] == family]
        rows.append(
            {
                "family": family,
                "label_pt": format_fault_label_pt(family),
                "recall": round((family_part["predicted_fault"] == family).mean(), 4),
            }
        )
    return pd.DataFrame(rows)


def top_confusions(details_df: pd.DataFrame, technique: str) -> list[str]:
    part = details_df[(details_df["technique"] == technique) & (details_df["predicted_fault"] != details_df["true_fault"])].copy()
    if part.empty:
        return ["Sem confusoes relevantes."]
    counts = (
        part.groupby(["true_fault", "predicted_fault"])
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
        .head(5)
    )
    return [
        f"- `{row.true_fault}` -> `{row.predicted_fault}`: {int(row.count)} ocorrencia(s)"
        for row in counts.itertuples(index=False)
    ]


def render_report(details_df: pd.DataFrame, metrics_df: pd.DataFrame) -> str:
    groq_row = metrics_df[metrics_df["technique"] == "llm_vector_rag_groq"].iloc[0]
    ollama_row = metrics_df[metrics_df["technique"] == "llm_vector_rag_ollama_small"].iloc[0]
    delta_acc = round(float(groq_row["accuracy"]) - float(ollama_row["accuracy"]), 4)
    delta_f1 = round(float(groq_row["macro_f1"]) - float(ollama_row["macro_f1"]), 4)

    lines = [
        "# Benchmark Completo de Inferencia 2026-08-05",
        "",
        "## Escopo",
        "",
        f"- Amostra robusta e balanceada com **{TOTAL_EXPECTED_SAMPLES} eventos**.",
        f"- Familias testadas: {', '.join(BENCHMARK_FAMILIES)}.",
        "- Tecnicas estatisticas e vetoriais executadas em todas as 50 amostras.",
        f"- `llm_vector_rag` executado duas vezes: uma com **Groq `{GROQ_MODEL}`** e outra com **Ollama `{OLLAMA_MODEL}`**.",
        "",
        "## Tecnicas avaliadas",
        "",
        "- `euclidean_knn`: baseline atual por distancia Euclidiana.",
        "- `mahalanobis_weighted_knn`: baseline robusto com distancia de Mahalanobis, voto ponderado e sinal OOD.",
        "- `cosine_knn`: vizinhos por cosseno nas features escaladas.",
        "- `centroid_euclidean`: centroide de classe.",
        "- `text_vector_vote`: textualizacao do evento e voto por exemplos recuperados por vetor.",
        "- `llm_vector_rag_groq`: LLM total com vetores usando Groq.",
        "- `llm_vector_rag_ollama_small`: LLM total com vetores usando Ollama local menor.",
        "",
        "## Resultado consolidado",
        "",
        dataframe_to_markdown(metrics_df),
        "",
        "## Comparacao direta do `llm_vector_rag`",
        "",
        f"- Acuracia Groq (`{GROQ_MODEL}`): **{groq_row['accuracy']:.4f}**",
        f"- Acuracia Ollama (`{OLLAMA_MODEL}`): **{ollama_row['accuracy']:.4f}**",
        f"- Delta de acuracia: **{delta_acc:+.4f}**",
        f"- Macro-F1 Groq: **{groq_row['macro_f1']:.4f}**",
        f"- Macro-F1 Ollama: **{ollama_row['macro_f1']:.4f}**",
        f"- Delta de Macro-F1: **{delta_f1:+.4f}**",
        f"- Latencia media Groq: **{groq_row['avg_latency_ms']:.3f} ms**",
        f"- Latencia media Ollama: **{ollama_row['avg_latency_ms']:.3f} ms**",
        "",
        "## Leitura tecnica",
        "",
    ]

    best = metrics_df.iloc[0]
    lines.extend(
        [
            f"- A melhor tecnica geral em acuracia foi **`{best['technique']}`** com **{best['accuracy']:.4f}**.",
            "- Se o baseline numerico ficar acima do LLM, isso reforca que a parte numerica ainda carrega o sinal mais forte nesta base.",
            "- Se o `llm_vector_rag_groq` se aproximar do baseline, isso sustenta melhor a narrativa LLM-first com recuperacao externa.",
            "- A comparacao com o Ollama local menor mede a perda de qualidade ao trazer o pipeline para execucao edge/local.",
            "",
            "## Recall por familia",
            "",
        ]
    )

    for technique in metrics_df["technique"]:
        lines.append(f"### {technique}")
        lines.append("")
        lines.append(dataframe_to_markdown(family_recall_table(details_df, technique)))
        lines.append("")
        lines.append("Principais confusoes:")
        lines.extend(top_confusions(details_df, technique))
        lines.append("")

    lines.extend(
        [
            "## Conclusao",
            "",
            "- Este benchmark mede o comportamento de tecnicas numericas, vetoriais textuais e LLM total com vetores em 50 amostras balanceadas.",
            "- O resultado ajuda a defender, com dado experimental, se o LLM deve ser o motor principal da classificacao ou a camada de orquestracao e sintese.",
            f"- Relatorio gerado em `{datetime.now(UTC).isoformat()}`.",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    print("Preparando benchmark completo...")
    details_df, metrics_df = run_benchmark()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    details_df.to_csv(DETAILS_CSV_PATH, index=False, encoding="utf-8-sig")
    metrics_df.to_csv(METRICS_CSV_PATH, index=False, encoding="utf-8-sig")
    REPORT_MD_PATH.write_text(render_report(details_df, metrics_df), encoding="utf-8")
    print("Benchmark concluido.")
    print(f"- detalhes: {DETAILS_CSV_PATH}")
    print(f"- metricas: {METRICS_CSV_PATH}")
    print(f"- relatorio: {REPORT_MD_PATH}")
    print(metrics_df.to_string(index=False))


if __name__ == "__main__":
    main()
