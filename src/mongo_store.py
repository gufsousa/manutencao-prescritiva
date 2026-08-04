from __future__ import annotations

from typing import Any
import json
from pathlib import Path
from copy import deepcopy

from pymongo import MongoClient
from pymongo.server_api import ServerApi

from src.settings import APP_DATA_DIR, SETTINGS


LOCAL_STATE_FILE = APP_DATA_DIR / "local_store.json"


class MongoStore:
    def __init__(self) -> None:
        self._client: MongoClient | None = None
        self._local_state = self._load_local_state()

    def _load_local_state(self) -> dict[str, list[dict[str, Any]]]:
        if not LOCAL_STATE_FILE.exists():
            return {}
        try:
            return json.loads(LOCAL_STATE_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _save_local_state(self) -> None:
        LOCAL_STATE_FILE.write_text(json.dumps(self._local_state, ensure_ascii=False, indent=2), encoding="utf-8")

    def enabled(self) -> bool:
        return SETTINGS.mongo_enabled and bool(SETTINGS.mongo_connection_string)

    def get_database(self):
        if not self.enabled():
            return None
        if self._client is None:
            self._client = MongoClient(
                SETTINGS.mongo_connection_string,
                server_api=ServerApi("1"),
                serverSelectionTimeoutMS=15000,
                connectTimeoutMS=15000,
                socketTimeoutMS=30000,
                retryWrites=True,
            )
        return self._client[SETTINGS.mongo_database]

    def ping(self) -> dict[str, Any]:
        if not self.enabled():
            return {"mode": "local", "connected": False}
        try:
            db = self.get_database()
            assert db is not None
            db.command("ping")
            return {"mode": "mongo", "connected": True, "database": db.name}
        except Exception as exc:
            return {"mode": "local", "connected": False, "error": str(exc)}

    def _collection_name(self, logical_name: str) -> str:
        mapping = {
            "history": SETTINGS.mongo_history_collection,
            "documents": SETTINGS.mongo_documents_collection,
            "document_chunks": SETTINGS.mongo_document_chunks_collection,
            "logs": SETTINGS.mongo_logs_collection,
            "benchmarks": SETTINGS.mongo_benchmarks_collection,
            "conversations": SETTINGS.mongo_conversations_collection,
        }
        return mapping[logical_name]

    def replace_many(self, logical_name: str, documents: list[dict[str, Any]]) -> int:
        collection_name = self._collection_name(logical_name)
        db = self.get_database()
        if db is not None:
            collection = db[collection_name]
            collection.delete_many({})
            if documents:
                collection.insert_many([deepcopy(item) for item in documents])
            return len(documents)
        self._local_state[collection_name] = documents
        self._save_local_state()
        return len(documents)

    def insert_one(self, logical_name: str, document: dict[str, Any]) -> dict[str, Any]:
        collection_name = self._collection_name(logical_name)
        db = self.get_database()
        if db is not None:
            db[collection_name].insert_one(deepcopy(document))
            return document
        self._local_state.setdefault(collection_name, []).append(document)
        self._save_local_state()
        return document

    def find_all(self, logical_name: str, limit: int | None = None) -> list[dict[str, Any]]:
        collection_name = self._collection_name(logical_name)
        db = self.get_database()
        if db is not None:
            cursor = db[collection_name].find({}, {"_id": 0})
            if limit:
                cursor = cursor.limit(limit)
            return list(cursor)
        items = list(self._local_state.get(collection_name, []))
        return items[:limit] if limit else items

    def append_log(self, logical_name: str, document: dict[str, Any]) -> None:
        self.insert_one(logical_name, document)

    def get_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        if self.get_database() is not None:
            db = self.get_database()
            assert db is not None
            for logical_name in ["history", "documents", "document_chunks", "logs", "benchmarks", "conversations"]:
                counts[logical_name] = db[self._collection_name(logical_name)].count_documents({})
            return counts
        for logical_name in ["history", "documents", "document_chunks", "logs", "benchmarks", "conversations"]:
            counts[logical_name] = len(self._local_state.get(self._collection_name(logical_name), []))
        return counts


STORE = MongoStore()
