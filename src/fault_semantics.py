from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import re

import yaml

from src.settings import CONFIG_DIR


@dataclass(frozen=True)
class FaultSemanticEntry:
    key: str
    label_pt: str
    kind: str
    family: str
    aliases: tuple[str, ...]


def _normalize_label(value: Any) -> str:
    return str(value or "").strip().lower()


def _compact_label(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", _normalize_label(value))


def _load_catalog() -> tuple[FaultSemanticEntry, ...]:
    payload = yaml.safe_load((CONFIG_DIR / "fault_lexicon.yaml").read_text(encoding="utf-8")) or {}
    entries = payload.get("entries") or []
    catalog: list[FaultSemanticEntry] = []
    for item in entries:
        catalog.append(
            FaultSemanticEntry(
                key=str(item["key"]).strip(),
                label_pt=str(item["label_pt"]).strip(),
                kind=str(item["kind"]).strip(),
                family=str(item["family"]).strip(),
                aliases=tuple(str(alias).strip().lower() for alias in (item.get("aliases") or [])),
            )
        )
    return tuple(catalog)


FAULT_CATALOG = _load_catalog()
FAULT_BY_KEY = {entry.key: entry for entry in FAULT_CATALOG}
STATE_KEYS = {entry.key for entry in FAULT_CATALOG if entry.kind == "state"}
FAULT_KEYS = {entry.key for entry in FAULT_CATALOG if entry.kind == "fault"}


def canonicalize_fault_label(value: Any) -> str:
    compact = _compact_label(value)
    if not compact:
        return "nao_informada"

    for entry in FAULT_CATALOG:
        variants = {_compact_label(entry.key), *(_compact_label(alias) for alias in entry.aliases)}
        if compact in variants:
            return entry.key

    if "desalinh" in compact:
        return "desalinhamento"
    if "desbalance" in compact or "desabalance" in compact or "desbanlance" in compact:
        return "desbalanceamento"
    if "rolamentoinner" in compact:
        return "rolamento_inner"
    if "rolamentoouter" in compact:
        return "rolamento_outer"
    if "rolamentoball" in compact:
        return "rolamento_ball"
    if "rolamentocomb" in compact:
        return "rolamento_combination"
    if "cocked" in compact or "cocke" in compact:
        return "cocked_rotor"
    if "eccentric" in compact:
        return "eccentric_rotor"
    if "correia" in compact:
        return "correia"
    if "polia" in compact:
        return "polia"
    if "ventoinha" in compact:
        return "ventoinha"
    if "faltafase" in compact:
        return "falta_fase"
    if "normal" in compact:
        return "normal"
    if "motor" in compact and "deslig" in compact:
        return "motor_desligado"
    return _normalize_label(value)


def get_fault_entry(value: Any) -> FaultSemanticEntry | None:
    return FAULT_BY_KEY.get(canonicalize_fault_label(value))


def format_fault_label_pt(value: Any) -> str:
    canonical = canonicalize_fault_label(value)
    entry = FAULT_BY_KEY.get(canonical)
    return entry.label_pt if entry else canonical.replace("_", " ").title()


def get_fault_family(value: Any) -> str:
    entry = get_fault_entry(value)
    return entry.family if entry else "desconhecido"


def get_label_kind(value: Any) -> str:
    entry = get_fault_entry(value)
    return entry.kind if entry else "unknown"


def is_state_label(value: Any) -> bool:
    return canonicalize_fault_label(value) in STATE_KEYS


def is_fault_label(value: Any) -> bool:
    return canonicalize_fault_label(value) in FAULT_KEYS


def get_fault_catalog(include_other: bool = False, kind: str | None = None) -> list[dict[str, str]]:
    items = [
        {
            "key": entry.key,
            "label_pt": entry.label_pt,
            "kind": entry.kind,
            "family": entry.family,
        }
        for entry in FAULT_CATALOG
        if kind in (None, "", "all") or entry.kind == kind
    ]
    if include_other:
        items.append({"key": "other", "label_pt": "Outro / rotulo livre", "kind": "custom", "family": "custom"})
    return items


def get_state_catalog() -> list[dict[str, str]]:
    return get_fault_catalog(kind="state")


def get_fault_only_catalog() -> list[dict[str, str]]:
    return get_fault_catalog(kind="fault")
