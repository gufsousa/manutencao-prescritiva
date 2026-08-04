from __future__ import annotations

from datetime import datetime, UTC
from typing import Any
import json
import uuid

from src.mongo_store import STORE
from src.settings import LOGS_DIR


LOCAL_LOG_FILE = LOGS_DIR / "inference_logs.jsonl"
LOCAL_BENCHMARK_FILE = LOGS_DIR / "benchmark_logs.jsonl"


def _append_local_jsonl(path, payload: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def log_inference(payload: dict[str, Any]) -> dict[str, Any]:
    item = {
        "id": str(uuid.uuid4()),
        "created_at": datetime.now(UTC).isoformat(),
        **payload,
    }
    STORE.append_log("logs", item)
    _append_local_jsonl(LOCAL_LOG_FILE, item)
    return item


def log_benchmark(payload: dict[str, Any]) -> dict[str, Any]:
    item = {
        "id": str(uuid.uuid4()),
        "created_at": datetime.now(UTC).isoformat(),
        **payload,
    }
    STORE.append_log("benchmarks", item)
    _append_local_jsonl(LOCAL_BENCHMARK_FILE, item)
    return item
