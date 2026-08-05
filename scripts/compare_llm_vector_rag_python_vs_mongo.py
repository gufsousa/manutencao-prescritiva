from __future__ import annotations

import argparse
import json
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any, Callable
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
from sklearn.metrics import accuracy_score, f1_score

from scripts.benchmark_shared import (
    BENCHMARK_FAMILIES,
    GROQ_MODEL,
    build_reference_artifacts,
    event_payload_from_row,
    prepare_data,
    predict_llm_vector_rag,
)
from src.document_service import DOCUMENT_SERVICE, DocumentSearchResult
from src.mongo_store import STORE
from src.settings import SETTINGS
from src.vectorization import embed_text


REPORTS_DIR = ROOT / "docs" / "analise_markdown"
DETAILS_CSV_PATH = REPORTS_DIR / "benchmark_llm_vector_rag_python_vs_mongo_2026-08-05.csv"
METRICS_CSV_PATH = REPORTS_DIR / "benchmark_llm_vector_rag_python_vs_mongo_metrics_2026-08-05.csv"
REPORT_MD_PATH = REPORTS_DIR / "11_benchmark_llm_vector_rag_python_vs_mongo_2026-08-05.md"
INDEX_NAME = "document_chunks_vector_index"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compara llm_vector_rag_groq usando busca documental em Python versus MongoDB Atlas Vector Search."
    )
    parser.add_argument("--samples-total", type=int, default=20, help="Total de amostras do benchmark.")
    parser.add_argument("--top-k-docs", type=int, default=4, help="Quantidade de chunks documentais por consulta.")
    parser.add_argument("--create-index", action="store_true", help="Cria/atualiza o indice vetorial no Atlas.")
    parser.add_argument("--exact", action="store_true", default=True, help="Usa ENN no Atlas para comparacao justa.")
    parser.add_argument("--num-candidates", type=int, default=100, help="Usado apenas se --exact nao for informado.")
    return parser.parse_args()


def _collection():
    db = STORE.get_database()
    if db is None:
        raise RuntimeError("MongoDB nao esta habilitado. Configure MONGO_ENABLED=true e MONGO_CONNECTION_STRING.")
    return db[SETTINGS.mongo_document_chunks_collection]


def ensure_vector_index(index_name: str) -> dict[str, Any]:
    collection = _collection()
    command = {
        "createSearchIndexes": collection.name,
        "indexes": [
            {
                "name": index_name,
                "type": "vectorSearch",
                "definition": {
                    "fields": [
                        {
                            "type": "vector",
                            "path": "vector",
                            "numDimensions": SETTINGS.vector_dimensions,
                            "similarity": "cosine",
                        },
                        {"type": "filter", "path": "fault_family"},
                    ]
                },
            }
        ],
    }
    return collection.database.command(command)


def atlas_search_chunks(
    query_text: str,
    fault_family: str | None = None,
    top_k: int = 4,
    *,
    exact: bool = True,
    num_candidates: int = 100,
    index_name: str = INDEX_NAME,
) -> DocumentSearchResult:
    query_vector = embed_text(query_text)
    vector_stage: dict[str, Any] = {
        "index": index_name,
        "path": "vector",
        "queryVector": query_vector,
        "limit": top_k,
    }
    if exact:
        vector_stage["exact"] = True
    else:
        vector_stage["numCandidates"] = num_candidates
    if fault_family:
        vector_stage["filter"] = {"fault_family": fault_family}

    pipeline = [
        {"$vectorSearch": vector_stage},
        {
            "$project": {
                "_id": 0,
                "id": 1,
                "document_id": 1,
                "source_file": 1,
                "title": 1,
                "fault_family": 1,
                "chunk_index": 1,
                "chunk_text": 1,
                "score": {"$meta": "vectorSearchScore"},
            }
        },
    ]
    rows = list(_collection().aggregate(pipeline))
    normalized_rows = [{**row, "score": round(float(row["score"]), 4)} for row in rows]
    return DocumentSearchResult(chunks=normalized_rows, summary=f"{len(normalized_rows)} chunk(s) recuperados via Atlas.")


@contextmanager
def patched_search_chunks(fn: Callable[..., DocumentSearchResult]):
    original = DOCUMENT_SERVICE.search_chunks
    DOCUMENT_SERVICE.search_chunks = fn  # type: ignore[method-assign]
    try:
        yield
    finally:
        DOCUMENT_SERVICE.search_chunks = original  # type: ignore[method-assign]


def run_document_retrieval(
    backend: str,
    event: dict[str, Any],
    *,
    top_k_docs: int,
    exact: bool,
    num_candidates: int,
) -> tuple[list[dict[str, Any]], float]:
    query_text = "\n".join(
        [
            "Evento de manutencao prescritiva",
            f"rpm: {event.get('rpm')}",
            f"temperature_c: {event.get('temperature_c')}",
            f"x_rms_velocity_mm_s: {event.get('x_rms_velocity_mm_s')}",
            f"z_rms_velocity_mm_s: {event.get('z_rms_velocity_mm_s')}",
            f"x_peak_acceleration_g: {event.get('x_peak_acceleration_g')}",
            f"z_peak_acceleration_g: {event.get('z_peak_acceleration_g')}",
            f"x_rms_acceleration_g: {event.get('x_rms_acceleration_g')}",
            f"z_rms_acceleration_g: {event.get('z_rms_acceleration_g')}",
            f"x_kurtosis: {event.get('x_kurtosis')}",
            f"z_kurtosis: {event.get('z_kurtosis')}",
            f"x_crest_factor: {event.get('x_crest_factor')}",
            f"z_crest_factor: {event.get('z_crest_factor')}",
        ]
    )
    started = perf_counter()
    if backend == "python":
        result = DOCUMENT_SERVICE.search_chunks(query_text=query_text, top_k=top_k_docs)
    elif backend == "mongo":
        result = atlas_search_chunks(query_text=query_text, top_k=top_k_docs, exact=exact, num_candidates=num_candidates)
    else:
        raise ValueError(f"Backend invalido: {backend}")
    elapsed_ms = round((perf_counter() - started) * 1000, 3)
    return result.chunks, elapsed_ms


def retrieval_overlap(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> tuple[int, bool]:
    left_ids = [item["id"] for item in left]
    right_ids = [item["id"] for item in right]
    return len(set(left_ids) & set(right_ids)), left_ids == right_ids


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


def render_report(metrics_df: pd.DataFrame, details_df: pd.DataFrame, samples_total: int, top_k_docs: int) -> str:
    summary = details_df.groupby("backend").agg(
        rows=("sample_id", "count"),
        accuracy=("correct", "mean"),
        avg_latency_ms=("elapsed_ms", "mean"),
        avg_doc_latency_ms=("doc_latency_ms", "mean"),
    ).reset_index()
    paired = (
        details_df.pivot(index="sample_id", columns="backend", values="predicted_fault")
        .reset_index()
        .rename_axis(None, axis=1)
    )
    same_prediction_ratio = float((paired["python"] == paired["mongo"]).mean()) if {"python", "mongo"} <= set(paired.columns) else 0.0

    overlap_df = (
        details_df[details_df["backend"] == "mongo"][["sample_id", "retrieval_overlap_at_k", "retrieval_same_order"]]
        .copy()
        .sort_values("sample_id")
    )
    lines = [
        "# Comparativo llm_vector_rag_groq: Python vs Mongo Atlas",
        "",
        "## Escopo",
        "",
        f"- Benchmark com **{samples_total} amostras** balanceadas.",
        f"- Pipeline avaliado: `llm_vector_rag_groq` com modelo `{GROQ_MODEL}`.",
        "- O que muda entre as execucoes: apenas a busca documental.",
        "- Backend A: ranking documental em Python.",
        "- Backend B: ranking documental no MongoDB Atlas via `$vectorSearch`.",
        f"- `top_k_docs`: {top_k_docs}.",
        "",
        "## Metricas por backend",
        "",
        dataframe_to_markdown(metrics_df),
        "",
        "## Resumo agregado",
        "",
        dataframe_to_markdown(summary),
        "",
        "## Consistencia entre backends",
        "",
        f"- Mesma falha predita entre Python e Mongo em **{same_prediction_ratio:.2%}** das amostras.",
        f"- Overlap medio dos chunks documentais no backend Mongo: **{overlap_df['retrieval_overlap_at_k'].mean():.2f}** em top-{top_k_docs}.",
        f"- Mesma ordem exata de chunks entre Python e Mongo em **{overlap_df['retrieval_same_order'].mean():.2%}** das amostras.",
        "",
        "## Leitura tecnica",
        "",
        "- Se a acuracia e as predicoes finais ficarem proximas, isso indica que a migracao do ranking vetorial para o Atlas preserva o comportamento do pipeline atual.",
        "- Se o Atlas reduzir latencia mantendo a mesma saida, ele passa a ser uma opcao forte para evolucao arquitetural.",
        "- Se houver divergencia alta, o gargalo passa a ser tuning de index, estrategia ANN/ENN ou detalhes de score entre os motores.",
        "",
        f"- Relatorio gerado em `{datetime.now(UTC).isoformat()}`.",
    ]
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    if args.samples_total % len(BENCHMARK_FAMILIES) != 0:
        raise ValueError("samples-total deve ser multiplo do numero de familias do benchmark.")
    samples_per_family = args.samples_total // len(BENCHMARK_FAMILIES)

    if args.create_index:
        print("Criando/atualizando indice vetorial do Atlas...")
        print(ensure_vector_index(INDEX_NAME))

    benchmark_df, reference_df = prepare_data(samples_per_family=samples_per_family)
    artifacts = build_reference_artifacts(reference_df)
    reference_text_records = artifacts["reference_text_records"]

    records: list[dict[str, Any]] = []
    total = len(benchmark_df)

    for sample_index, (_, row) in enumerate(benchmark_df.iterrows(), start=1):
        event = event_payload_from_row(row)
        true_fault = row["canonical_fault"]
        print(f"[{sample_index}/{total}] sample_id={int(row['id'])} true_fault={true_fault}")

        python_chunks, python_doc_latency = run_document_retrieval(
            "python",
            event,
            top_k_docs=args.top_k_docs,
            exact=args.exact,
            num_candidates=args.num_candidates,
        )
        mongo_chunks, mongo_doc_latency = run_document_retrieval(
            "mongo",
            event,
            top_k_docs=args.top_k_docs,
            exact=args.exact,
            num_candidates=args.num_candidates,
        )
        overlap_at_k, same_order = retrieval_overlap(python_chunks, mongo_chunks)

        python_result = predict_llm_vector_rag(event, "groq", GROQ_MODEL, reference_text_records, BENCHMARK_FAMILIES)

        with patched_search_chunks(
            lambda query_text, fault_family=None, top_k=None: atlas_search_chunks(
                query_text,
                fault_family=fault_family,
                top_k=args.top_k_docs,
                exact=args.exact,
                num_candidates=args.num_candidates,
            )
        ):
            mongo_result = predict_llm_vector_rag(event, "groq", GROQ_MODEL, reference_text_records, BENCHMARK_FAMILIES)

        records.append(
            {
                "sample_id": int(row["id"]),
                "true_fault": true_fault,
                "backend": "python",
                "model": GROQ_MODEL,
                "predicted_fault": python_result["predicted_fault"],
                "confidence_proxy": python_result["confidence_proxy"],
                "elapsed_ms": python_result["elapsed_ms"],
                "doc_latency_ms": python_doc_latency,
                "correct": python_result["predicted_fault"] == true_fault,
                "retrieval_overlap_at_k": overlap_at_k,
                "retrieval_same_order": same_order,
                "retrieved_chunk_ids": json.dumps([item["id"] for item in python_chunks], ensure_ascii=False),
                "raw_response": python_result["raw_response"],
                "usage": json.dumps(python_result["usage"], ensure_ascii=False),
            }
        )
        records.append(
            {
                "sample_id": int(row["id"]),
                "true_fault": true_fault,
                "backend": "mongo",
                "model": GROQ_MODEL,
                "predicted_fault": mongo_result["predicted_fault"],
                "confidence_proxy": mongo_result["confidence_proxy"],
                "elapsed_ms": mongo_result["elapsed_ms"],
                "doc_latency_ms": mongo_doc_latency,
                "correct": mongo_result["predicted_fault"] == true_fault,
                "retrieval_overlap_at_k": overlap_at_k,
                "retrieval_same_order": same_order,
                "retrieved_chunk_ids": json.dumps([item["id"] for item in mongo_chunks], ensure_ascii=False),
                "raw_response": mongo_result["raw_response"],
                "usage": json.dumps(mongo_result["usage"], ensure_ascii=False),
            }
        )

        checkpoint_df = pd.DataFrame(records)
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        checkpoint_df.to_csv(DETAILS_CSV_PATH, index=False, encoding="utf-8-sig")
        print(
            f"  checkpoint salvo apos sample_id={int(row['id'])} "
            f"(python={python_result['predicted_fault']}, mongo={mongo_result['predicted_fault']}, overlap={overlap_at_k})"
        )

    details_df = pd.DataFrame(records)
    metrics_rows = []
    for backend, part in details_df.groupby("backend"):
        metrics_rows.append(
            {
                "backend": backend,
                "rows": len(part),
                "accuracy": round(accuracy_score(part["true_fault"], part["predicted_fault"]), 4),
                "macro_f1": round(f1_score(part["true_fault"], part["predicted_fault"], average="macro"), 4),
                "avg_latency_ms": round(part["elapsed_ms"].mean(), 3),
                "avg_doc_latency_ms": round(part["doc_latency_ms"].mean(), 3),
                "same_prediction_ratio": round(
                    float(
                        (
                            details_df[details_df["backend"] == "python"]["predicted_fault"].reset_index(drop=True)
                            == details_df[details_df["backend"] == "mongo"]["predicted_fault"].reset_index(drop=True)
                        ).mean()
                    ),
                    4,
                )
                if {"python", "mongo"} <= set(details_df["backend"].unique())
                else None,
            }
        )
    metrics_df = pd.DataFrame(metrics_rows).sort_values("backend")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    details_df.to_csv(DETAILS_CSV_PATH, index=False, encoding="utf-8-sig")
    metrics_df.to_csv(METRICS_CSV_PATH, index=False, encoding="utf-8-sig")
    REPORT_MD_PATH.write_text(render_report(metrics_df, details_df, args.samples_total, args.top_k_docs), encoding="utf-8")

    print(f"Detalhes: {DETAILS_CSV_PATH}")
    print(f"Metricas: {METRICS_CSV_PATH}")
    print(f"Relatorio: {REPORT_MD_PATH}")
    print(metrics_df.to_string(index=False))


if __name__ == "__main__":
    main()
