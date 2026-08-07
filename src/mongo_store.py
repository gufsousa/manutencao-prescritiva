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
        self._last_mongo_error: str = ""

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

    def last_mongo_error(self) -> str:
        return self._last_mongo_error

    def _remember_mongo_error(self, exc: Exception) -> None:
        self._last_mongo_error = str(exc)
        try:
            if self._client is not None:
                self._client.close()
        except Exception:
            pass
        self._client = None

    def get_database(self):
        if not self.enabled():
            return None
        try:
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
        except Exception as exc:
            self._remember_mongo_error(exc)
            return None

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

    def _batched(self, documents: list[dict[str, Any]], batch_size: int = 1000):
        for start in range(0, len(documents), batch_size):
            yield documents[start : start + batch_size]

    def replace_many(self, logical_name: str, documents: list[dict[str, Any]]) -> int:
        collection_name = self._collection_name(logical_name)
        db = self.get_database()
        if db is not None:
            try:
                collection = db[collection_name]
                collection.delete_many({})
                if documents:
                    for batch in self._batched(documents):
                        collection.insert_many([deepcopy(item) for item in batch], ordered=False)
                self._last_mongo_error = ""
                return len(documents)
            except Exception as exc:
                self._remember_mongo_error(exc)
        self._local_state[collection_name] = documents
        self._save_local_state()
        return len(documents)

    def get_existing_ids(self, logical_name: str) -> set[str]:
        collection_name = self._collection_name(logical_name)
        db = self.get_database()
        if db is not None:
            try:
                cursor = db[collection_name].find({"id": {"$exists": True}}, {"_id": 0, "id": 1})
                self._last_mongo_error = ""
                return {str(item["id"]) for item in cursor if item.get("id") is not None}
            except Exception as exc:
                self._remember_mongo_error(exc)
        return {
            str(item["id"])
            for item in self._local_state.get(collection_name, [])
            if isinstance(item, dict) and item.get("id") is not None
        }

    def insert_many_missing_by_id(self, logical_name: str, documents: list[dict[str, Any]]) -> dict[str, int]:
        collection_name = self._collection_name(logical_name)
        existing_ids = self.get_existing_ids(logical_name)
        missing_documents = [
            deepcopy(item)
            for item in documents
            if item.get("id") is not None and str(item["id"]) not in existing_ids
        ]

        db = self.get_database()
        if db is not None:
            try:
                if missing_documents:
                    collection = db[collection_name]
                    for batch in self._batched(missing_documents):
                        collection.insert_many(batch, ordered=False)
                self._last_mongo_error = ""
                return {"requested": len(documents), "inserted": len(missing_documents), "skipped": len(documents) - len(missing_documents)}
            except Exception as exc:
                self._remember_mongo_error(exc)

        target = self._local_state.setdefault(collection_name, [])
        if missing_documents:
            target.extend(missing_documents)
            self._save_local_state()
        return {"requested": len(documents), "inserted": len(missing_documents), "skipped": len(documents) - len(missing_documents)}

    def insert_one(self, logical_name: str, document: dict[str, Any]) -> dict[str, Any]:
        collection_name = self._collection_name(logical_name)
        db = self.get_database()
        if db is not None:
            try:
                db[collection_name].insert_one(deepcopy(document))
                self._last_mongo_error = ""
                return document
            except Exception as exc:
                self._remember_mongo_error(exc)
        self._local_state.setdefault(collection_name, []).append(document)
        self._save_local_state()
        return document

    def find_all(self, logical_name: str, limit: int | None = None) -> list[dict[str, Any]]:
        collection_name = self._collection_name(logical_name)
        db = self.get_database()
        if db is not None:
            try:
                cursor = db[collection_name].find({}, {"_id": 0})
                if limit:
                    cursor = cursor.limit(limit)
                self._last_mongo_error = ""
                return list(cursor)
            except Exception as exc:
                self._remember_mongo_error(exc)
        items = list(self._local_state.get(collection_name, []))
        return items[:limit] if limit else items

    def append_log(self, logical_name: str, document: dict[str, Any]) -> None:
        self.insert_one(logical_name, document)

    def get_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        db = self.get_database()
        if db is not None:
            assert db is not None
            try:
                for logical_name in ["history", "documents", "document_chunks", "logs", "benchmarks", "conversations"]:
                    counts[logical_name] = db[self._collection_name(logical_name)].count_documents({})
                self._last_mongo_error = ""
                return counts
            except Exception as exc:
                self._remember_mongo_error(exc)
        for logical_name in ["history", "documents", "document_chunks", "logs", "benchmarks", "conversations"]:
            counts[logical_name] = len(self._local_state.get(self._collection_name(logical_name), []))
        return counts


STORE = MongoStore()
