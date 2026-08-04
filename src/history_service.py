from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from typing import Any
import json
import math

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from src.fault_semantics import canonicalize_fault_label, format_fault_label_pt
from src.mongo_store import STORE
from src.settings import RAW_DATA_DIR


DATASET_PATH = RAW_DATA_DIR / "banner.csv"
FEATURE_COLUMNS = [
    "temperature_c",
    "rpm",
    "z_rms_velocity_mm_s",
    "x_rms_velocity_mm_s",
    "z_peak_acceleration_g",
    "x_peak_acceleration_g",
    "z_rms_acceleration_g",
    "x_rms_acceleration_g",
    "z_kurtosis",
    "x_kurtosis",
    "z_crest_factor",
    "x_crest_factor",
]


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


@dataclass
class HistorySearchResult:
    neighbors: list[dict[str, Any]]
    fault_distribution: list[dict[str, Any]]
    summary: str


class HistoryService:
    def __init__(self) -> None:
        self._df_cache: pd.DataFrame | None = None

    def load_dataset(self) -> pd.DataFrame:
        if self._df_cache is None:
            df = pd.read_csv(DATASET_PATH)
            df["created_at"] = pd.to_datetime(df["created_at"], utc=True)
            df["canonical_fault"] = df["fault"].map(canonicalize_fault_label)
            for column in FEATURE_COLUMNS:
                df[column] = pd.to_numeric(df[column], errors="coerce")
            self._df_cache = df
        return self._df_cache.copy()

    def ingest_history_to_mongo(self, limit: int | None = None) -> dict[str, Any]:
        df = self.load_dataset()
        if limit:
            df = df.head(limit)
        records = json.loads(df.to_json(orient="records", date_format="iso"))
        inserted = STORE.replace_many("history", records)
        return {"inserted": inserted, "source_rows": len(df)}

    def load_history_frame(self, prefer_mongo: bool = True) -> pd.DataFrame:
        if prefer_mongo:
            records = STORE.find_all("history")
            if records:
                df = pd.DataFrame(records)
                if "created_at" in df.columns:
                    df["created_at"] = pd.to_datetime(df["created_at"], utc=True, errors="coerce")
                if "canonical_fault" not in df.columns and "fault" in df.columns:
                    df["canonical_fault"] = df["fault"].map(canonicalize_fault_label)
                return df
        return self.load_dataset()

    @cached_property
    def scaler(self) -> StandardScaler:
        df = self.load_dataset()
        filled = df[FEATURE_COLUMNS].fillna(df[FEATURE_COLUMNS].median())
        return StandardScaler().fit(filled)

    def normalize_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(payload)
        normalized["fault"] = canonicalize_fault_label(normalized.get("fault"))
        for feature in FEATURE_COLUMNS:
            normalized[feature] = _safe_float(normalized.get(feature), float("nan"))
        return normalized

    def validate_event(self, event: dict[str, Any]) -> dict[str, Any]:
        warnings: list[str] = []
        errors: list[str] = []
        temp = _safe_float(event.get("temperature_c"), math.nan)
        rpm = _safe_float(event.get("rpm"), math.nan)
        vib_x = _safe_float(event.get("x_rms_velocity_mm_s"), math.nan)
        vib_z = _safe_float(event.get("z_rms_velocity_mm_s"), math.nan)
        if not math.isnan(temp) and not (-40 <= temp <= 220):
            errors.append("temperature_c fora da faixa plausível")
        if not math.isnan(rpm) and not (0 <= rpm <= 10000):
            errors.append("rpm fora da faixa plausível")
        if not math.isnan(vib_x) and vib_x < 0:
            errors.append("x_rms_velocity_mm_s negativa")
        if not math.isnan(vib_z) and vib_z < 0:
            errors.append("z_rms_velocity_mm_s negativa")
        if not math.isnan(rpm) and rpm == 0 and ((not math.isnan(vib_x) and vib_x > 3) or (not math.isnan(vib_z) and vib_z > 3)):
            warnings.append("máquina desligada com vibração relevante")
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    def _prepare_history_matrix(self, df: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray]:
        filled = df[FEATURE_COLUMNS].copy()
        filled = filled.fillna(filled.median())
        matrix = self.scaler.transform(filled)
        return filled, matrix

    def search_similar_events(self, event: dict[str, Any], top_k: int = 5) -> HistorySearchResult:
        df = self.load_history_frame()
        normalized = self.normalize_event(event)
        if df.empty:
            return HistorySearchResult(neighbors=[], fault_distribution=[], summary="Sem histórico disponível.")

        same_rpm = df[df["rpm"] == normalized.get("rpm")]
        candidate_df = same_rpm if len(same_rpm) >= max(20, top_k) else df
        _, matrix = self._prepare_history_matrix(candidate_df)

        event_vector = pd.DataFrame([{feature: normalized.get(feature, np.nan) for feature in FEATURE_COLUMNS}])
        event_vector = event_vector.fillna(candidate_df[FEATURE_COLUMNS].median())
        scaled_event = self.scaler.transform(event_vector)
        distances = np.linalg.norm(matrix - scaled_event, axis=1)
        ranked = candidate_df.assign(similarity_distance=distances).sort_values("similarity_distance").head(top_k)

        neighbors = []
        for _, row in ranked.iterrows():
            neighbors.append(
                {
                    "id": int(row["id"]) if not pd.isna(row["id"]) else None,
                    "created_at": row["created_at"].isoformat() if not pd.isna(row["created_at"]) else "",
                    "fault": row["fault"],
                    "canonical_fault": row["canonical_fault"],
                    "canonical_fault_label": format_fault_label_pt(row["canonical_fault"]),
                    "rpm": _safe_float(row["rpm"]),
                    "temperature_c": _safe_float(row["temperature_c"]),
                    "x_rms_velocity_mm_s": _safe_float(row["x_rms_velocity_mm_s"]),
                    "z_rms_velocity_mm_s": _safe_float(row["z_rms_velocity_mm_s"]),
                    "distance": round(_safe_float(row["similarity_distance"]), 4),
                }
            )

        fault_distribution_df = ranked.groupby("canonical_fault").size().sort_values(ascending=False).reset_index(name="count")
        total = int(fault_distribution_df["count"].sum()) or 1
        fault_distribution = [
            {
                "canonical_fault": row["canonical_fault"],
                "label": format_fault_label_pt(row["canonical_fault"]),
                "count": int(row["count"]),
                "pct": round((int(row["count"]) / total) * 100, 2),
            }
            for _, row in fault_distribution_df.iterrows()
        ]
        summary = (
            f"{len(neighbors)} vizinhos recuperados"
            f" | principal hipótese histórica: {fault_distribution[0]['label']}" if fault_distribution else "Sem distribuição de falhas."
        )
        return HistorySearchResult(neighbors=neighbors, fault_distribution=fault_distribution, summary=summary)

    def dataset_metrics(self) -> dict[str, Any]:
        df = self.load_history_frame()
        return {
            "rows": len(df),
            "raw_faults": int(df["fault"].nunique()),
            "canonical_faults": int(df["canonical_fault"].nunique()),
            "min_date": df["created_at"].min(),
            "max_date": df["created_at"].max(),
            "rpm_counts": df["rpm"].value_counts().sort_index().to_dict(),
            "fault_counts": df["canonical_fault"].value_counts().to_dict(),
        }


HISTORY_SERVICE = HistoryService()
