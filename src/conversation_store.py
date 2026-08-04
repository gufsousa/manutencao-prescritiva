from __future__ import annotations

from datetime import datetime, UTC
from typing import Any
import json
import uuid

from src.mongo_store import STORE
from src.settings import APP_DATA_DIR


LOCAL_CONVERSATIONS_FILE = APP_DATA_DIR / "conversations.json"


def _load_local_conversations() -> list[dict[str, Any]]:
    if not LOCAL_CONVERSATIONS_FILE.exists():
        return []
    try:
        return json.loads(LOCAL_CONVERSATIONS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def _save_local_conversations(items: list[dict[str, Any]]) -> None:
    LOCAL_CONVERSATIONS_FILE.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def list_conversations(limit: int = 30) -> list[dict[str, Any]]:
    items = STORE.find_all("conversations", limit=limit)
    if items:
        return sorted(items, key=lambda item: item.get("updated_at", ""), reverse=True)[:limit]
    local_items = _load_local_conversations()
    return sorted(local_items, key=lambda item: item.get("updated_at", ""), reverse=True)[:limit]


def get_conversation(conversation_id: str) -> dict[str, Any] | None:
    for item in list_conversations(limit=200):
        if item.get("id") == conversation_id:
            return item
    return None


def save_conversation(messages: list[dict[str, str]], title: str | None = None, conversation_id: str | None = None) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    existing = list_conversations(limit=200)
    if conversation_id is None:
        conversation_id = str(uuid.uuid4())

    auto_title = title or "Nova conversa"
    for message in messages:
        if message.get("role") == "user":
            auto_title = message.get("content", "Nova conversa").strip().splitlines()[0][:72] or auto_title
            break

    payload = {
        "id": conversation_id,
        "title": auto_title,
        "updated_at": now,
        "messages": messages,
    }

    replaced = False
    for index, item in enumerate(existing):
        if item.get("id") == conversation_id:
            existing[index] = payload
            replaced = True
            break
    if not replaced:
        existing.append(payload)

    STORE.replace_many("conversations", existing[:200])
    _save_local_conversations(existing[:200])
    return payload
