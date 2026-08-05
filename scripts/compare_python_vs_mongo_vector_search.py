from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Any
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.document_service import DOCUMENT_SERVICE
from src.fault_semantics import canonicalize_fault_label
from src.mongo_store import STORE
from src.settings import SETTINGS
from src.vectorization import embed_text


DEFAULT_INDEX_NAME = "document_chunks_vector_index"


@dataclass
class SearchRun:
    backend: str
    elapsed_ms: float
    results: list[dict[str, Any]]
    error: str | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compara busca vetorial em Python vs MongoDB Atlas Vector Search para os chunks documentais."
    )
    parser.add_argument(
        "--query",
        action="append",
        required=True,
        help="Consulta textual. Pode ser repetido para comparar varias consultas.",
    )
    parser.add_argument("--fault-family", help="Filtro opcional por familia de falha.")
    parser.add_argument("--top-k", type=int, default=5, help="Quantidade de resultados retornados.")
    parser.add_argument(
        "--num-candidates",
        type=int,
        default=100,
        help="numCandidates do Atlas para ANN. Ignorado em busca exata.",
    )
    parser.add_argument(
        "--exact",
        action="store_true",
        help="Usa ENN no Atlas. Sem esta flag, usa ANN com numCandidates.",
    )
    parser.add_argument(
        "--index-name",
        default=DEFAULT_INDEX_NAME,
        help="Nome do indice vetorial no Atlas.",
    )
    parser.add_argument(
        "--create-index",
        action="store_true",
        help="Cria/atualiza o indice vetorial no Atlas antes de consultar.",
    )
    parser.add_argument(
        "--reingest",
        action="store_true",
        help="Reingere os documentos padrao antes da comparacao.",
    )
    return parser.parse_args()


def _get_mongo_collection():
    db = STORE.get_database()
    if db is None:
        raise RuntimeError(
            "MongoDB nao esta habilitado. Ative MONGO_ENABLED=true e configure MONGO_CONNECTION_STRING."
        )
    return db[SETTINGS.mongo_document_chunks_collection]


def ensure_documents_loaded(reingest: bool) -> None:
    if reingest or not DOCUMENT_SERVICE.list_chunks():
        DOCUMENT_SERVICE.ingest_default_documents()


def create_vector_index(index_name: str) -> dict[str, Any]:
    collection = _get_mongo_collection()
    db = collection.database
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
                        {
                            "type": "filter",
                            "path": "fault_family",
                        },
                    ]
                },
            }
        ],
    }
    return db.command(command)


def run_python_search(query: str, fault_family: str | None, top_k: int) -> SearchRun:
    started = perf_counter()
    result = DOCUMENT_SERVICE.search_chunks(query_text=query, fault_family=fault_family, top_k=top_k)
    elapsed_ms = round((perf_counter() - started) * 1000, 3)
    rows = [
        {
            "id": chunk["id"],
            "title": chunk["title"],
            "fault_family": chunk["fault_family"],
            "chunk_index": chunk["chunk_index"],
            "score": chunk["score"],
            "source_file": chunk["source_file"],
        }
        for chunk in result.chunks
    ]
    return SearchRun(backend="python_cosine", elapsed_ms=elapsed_ms, results=rows)


def run_mongo_vector_search(
    query: str,
    fault_family: str | None,
    top_k: int,
    index_name: str,
    num_candidates: int,
    exact: bool,
) -> SearchRun:
    try:
        collection = _get_mongo_collection()
        query_vector = embed_text(query)

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
            vector_stage["filter"] = {"fault_family": canonicalize_fault_label(fault_family)}

        pipeline = [
            {"$vectorSearch": vector_stage},
            {
                "$project": {
                    "_id": 0,
                    "id": 1,
                    "title": 1,
                    "fault_family": 1,
                    "chunk_index": 1,
                    "source_file": 1,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
        ]

        started = perf_counter()
        rows = list(collection.aggregate(pipeline))
        elapsed_ms = round((perf_counter() - started) * 1000, 3)
        for row in rows:
            row["score"] = round(float(row["score"]), 4)
        return SearchRun(backend="mongo_vector_search", elapsed_ms=elapsed_ms, results=rows)
    except Exception as exc:
        return SearchRun(backend="mongo_vector_search", elapsed_ms=0.0, results=[], error=str(exc))


def compare_runs(python_run: SearchRun, mongo_run: SearchRun) -> dict[str, Any]:
    python_ids = [row["id"] for row in python_run.results]
    mongo_ids = [row["id"] for row in mongo_run.results]
    overlap = len(set(python_ids) & set(mongo_ids))
    return {
        "python_top_ids": python_ids,
        "mongo_top_ids": mongo_ids,
        "overlap_at_k": overlap,
        "same_order": python_ids == mongo_ids,
        "python_elapsed_ms": python_run.elapsed_ms,
        "mongo_elapsed_ms": mongo_run.elapsed_ms,
        "mongo_error": mongo_run.error,
    }


def main() -> None:
    args = parse_args()
    ensure_documents_loaded(reingest=args.reingest)

    if args.create_index:
        response = create_vector_index(args.index_name)
        print("Indice criado/atualizado no Atlas:")
        print(json.dumps(response, ensure_ascii=False, indent=2, default=str))

    for query in args.query:
        print("=" * 80)
        print(f"QUERY: {query}")
        if args.fault_family:
            print(f"FILTRO fault_family: {canonicalize_fault_label(args.fault_family)}")

        python_run = run_python_search(query, args.fault_family, args.top_k)
        mongo_run = run_mongo_vector_search(
            query=query,
            fault_family=args.fault_family,
            top_k=args.top_k,
            index_name=args.index_name,
            num_candidates=args.num_candidates,
            exact=args.exact,
        )
        summary = compare_runs(python_run, mongo_run)

        payload = {
            "summary": summary,
            "python_run": asdict(python_run),
            "mongo_run": asdict(mongo_run),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
