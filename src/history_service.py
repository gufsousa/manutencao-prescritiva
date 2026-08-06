from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from statistics import NormalDist
from typing import Any
import json
import math
from copy import deepcopy

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from src.fault_semantics import canonicalize_fault_label, format_fault_label_pt, is_fault_label, is_state_label
from src.mongo_store import STORE
from src.settings import CONFIG_DIR, RAW_DATA_DIR


DATASET_PATH = RAW_DATA_DIR / "banner.csv"
DATASET_METRICS_SNAPSHOT_PATH = CONFIG_DIR / "dataset_metrics_snapshot.json"
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
    candidate_fault: str
    confidence_pct: float
    similarity_metric: str
    ood_score: float
    ood_threshold_95: float
    ood_threshold_99: float
    ood_flag: bool
    ood_status: str
    summary: str


class HistoryService:
    def __init__(self) -> None:
        self._df_cache: pd.DataFrame | None = None

    def _invalidate_cached_metrics(self) -> None:
        self.__dict__.pop("_dataset_metrics_cache", None)
        self.__dict__.pop("_storage_metrics_cache", None)

    def load_dataset(self) -> pd.DataFrame:
        if self._df_cache is None:
            df = pd.read_csv(DATASET_PATH)
            df["created_at"] = pd.to_datetime(df["created_at"], utc=True)
            unique_faults = df["fault"].dropna().astype(str).unique().tolist()
            canonical_map = {fault_label: canonicalize_fault_label(fault_label) for fault_label in unique_faults}
            df["canonical_fault"] = df["fault"].map(lambda value: canonical_map.get(str(value), canonicalize_fault_label(value)))
            for column in FEATURE_COLUMNS:
                df[column] = pd.to_numeric(df[column], errors="coerce")
            self._df_cache = df
        return self._df_cache.copy()

    def ingest_history_to_mongo(
        self,
        limit: int | None = None,
        *,
        source: str = "protected",
        allow_partial: bool = False,
        sample_fraction: float | None = None,
        incremental: bool = False,
    ) -> dict[str, Any]:
        if limit is None and sample_fraction is None and source != "page":
            raise PermissionError("Reingestao completa do historico permitida apenas pela pagina da aplicacao.")
        if limit is not None and not allow_partial:
            raise PermissionError("Ingestao parcial do historico exige allow_partial=True.")
        if sample_fraction is not None:
            if not (0 < sample_fraction < 1):
                raise ValueError("sample_fraction deve estar entre 0 e 1.")
            if source not in {"page", "test"}:
                raise PermissionError("Amostragem representativa do historico permitida apenas pela pagina da aplicacao.")

        if sample_fraction is not None:
            df = self.build_representative_sample(sample_fraction=sample_fraction)
        else:
            df = self.load_dataset()
        if limit:
            df = df.head(limit)
        records = json.loads(df.to_json(orient="records", date_format="iso"))
        if incremental:
            result = STORE.insert_many_missing_by_id("history", records)
            inserted = result["inserted"]
            skipped = result["skipped"]
        else:
            inserted = STORE.replace_many("history", records)
            skipped = 0
        self._invalidate_cached_metrics()
        return {
            "inserted": inserted,
            "skipped": skipped,
            "source_rows": len(df),
            "source": source,
            "partial": limit is not None or sample_fraction is not None,
            "sample_fraction": sample_fraction,
            "incremental": incremental,
        }

    def load_history_frame(self, prefer_mongo: bool = True) -> pd.DataFrame:
        if prefer_mongo:
            storage = self.storage_metrics()
            can_use_mongo_for_similarity = storage["is_fully_synced"] or storage["coverage_pct"] >= 95.0
            records = STORE.find_all("history") if can_use_mongo_for_similarity else []
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

    def _inverse_covariance(self, matrix: np.ndarray) -> np.ndarray:
        covariance = np.cov(matrix, rowvar=False)
        regularization = np.eye(covariance.shape[0]) * 1e-6
        return np.linalg.pinv(covariance + regularization)

    def _mahalanobis_distances(self, matrix: np.ndarray, query_vector: np.ndarray, inv_cov: np.ndarray) -> np.ndarray:
        deltas = matrix - query_vector
        squared = np.einsum("ij,jk,ik->i", deltas, inv_cov, deltas)
        squared = np.clip(squared, a_min=0.0, a_max=None)
        return np.sqrt(squared)

    def _chi_square_threshold(self, degrees_of_freedom: int, confidence: float) -> float:
        z_score = NormalDist().inv_cdf(confidence)
        factor = 1 - (2 / (9 * degrees_of_freedom)) + z_score * math.sqrt(2 / (9 * degrees_of_freedom))
        return float(max(degrees_of_freedom * (factor**3), 0.0))

    def _weighted_fault_distribution(self, ranked: pd.DataFrame) -> list[dict[str, Any]]:
        weighted_votes = (
            ranked.groupby("canonical_fault")["vote_weight"]
            .sum()
            .sort_values(ascending=False)
            .reset_index(name="weight")
        )
        total_weight = float(weighted_votes["weight"].sum()) or 1.0
        return [
            {
                "canonical_fault": row["canonical_fault"],
                "label": format_fault_label_pt(row["canonical_fault"]),
                "count": int((ranked["canonical_fault"] == row["canonical_fault"]).sum()),
                "weight": round(float(row["weight"]), 6),
                "pct": round((float(row["weight"]) / total_weight) * 100, 2),
            }
            for _, row in weighted_votes.iterrows()
        ]

    def _class_ood_score(self, candidate_df: pd.DataFrame, class_label: str, scaled_event: np.ndarray) -> float:
        class_df = candidate_df[candidate_df["canonical_fault"] == class_label]
        if len(class_df) < 3:
            class_df = candidate_df
        _, class_matrix = self._prepare_history_matrix(class_df)
        inv_cov = self._inverse_covariance(class_matrix)
        centroid = class_matrix.mean(axis=0, keepdims=True)
        return float(self._mahalanobis_distances(centroid, scaled_event, inv_cov)[0])

    def build_representative_sample(self, sample_fraction: float = 0.20, random_state: int = 42) -> pd.DataFrame:
        df = self.load_dataset().sort_values(["created_at", "id"]).reset_index(drop=True)
        if df.empty:
            return df

        target_size = max(
            math.ceil(len(df) * sample_fraction),
            int(df["created_at"].dt.strftime("%Y-%m-%d").nunique()),
            int(df["canonical_fault"].nunique()),
        )
        target_size = min(target_size, len(df))
        day_key = df["created_at"].dt.strftime("%Y-%m-%d")

        selected_indices: set[int] = set()

        # Garante pelo menos um registro por dia presente no CSV.
        for _, group in df.groupby(day_key, sort=True):
            selected_indices.add(int(group.index[0]))

        # Garante pelo menos um registro por familia de falha canonica.
        covered_faults = set(df.loc[list(selected_indices), "canonical_fault"].dropna().tolist())
        for fault_name, group in df.groupby("canonical_fault", sort=True):
            if fault_name in covered_faults:
                continue
            selected_indices.add(int(group.index[0]))
            covered_faults.add(fault_name)

        remaining_target = max(target_size - len(selected_indices), 0)
        if remaining_target == 0:
            return df.loc[sorted(selected_indices)].reset_index(drop=True)

        remaining_df = df.drop(index=list(selected_indices)).copy()
        remaining_df["day_key"] = remaining_df["created_at"].dt.strftime("%Y-%m-%d")
        day_counts = remaining_df["day_key"].value_counts().sort_index()
        if day_counts.empty:
            return df.loc[sorted(selected_indices)].reset_index(drop=True)

        raw_allocation = (day_counts / day_counts.sum()) * remaining_target
        floor_allocation = np.floor(raw_allocation).astype(int)
        allocation = floor_allocation.copy()
        remaining_slots = remaining_target - int(allocation.sum())

        fractional = (raw_allocation - floor_allocation).sort_values(ascending=False)
        for day_name in fractional.index:
            if remaining_slots <= 0:
                break
            if allocation[day_name] < day_counts[day_name]:
                allocation[day_name] += 1
                remaining_slots -= 1

        sampled_frames: list[pd.DataFrame] = []
        for day_name, day_target in allocation.items():
            if day_target <= 0:
                continue
            day_frame = remaining_df[remaining_df["day_key"] == day_name]
            if day_target >= len(day_frame):
                sampled_frames.append(day_frame)
            else:
                sampled_frames.append(day_frame.sample(n=int(day_target), random_state=random_state))

        sampled_df = pd.concat(sampled_frames, ignore_index=False) if sampled_frames else remaining_df.iloc[0:0]
        final_indices = sorted(selected_indices.union(set(int(idx) for idx in sampled_df.index.tolist())))
        return df.loc[final_indices].reset_index(drop=True)

    def search_similar_events(self, event: dict[str, Any], top_k: int = 5) -> HistorySearchResult:
        df = self.load_history_frame()
        normalized = self.normalize_event(event)
        if df.empty:
            return HistorySearchResult(
                neighbors=[],
                fault_distribution=[],
                candidate_fault=canonicalize_fault_label(normalized.get("fault")),
                confidence_pct=0.0,
                similarity_metric="mahalanobis_weighted_knn",
                ood_score=0.0,
                ood_threshold_95=0.0,
                ood_threshold_99=0.0,
                ood_flag=False,
                ood_status="sem_historico",
                summary="Sem histórico disponível.",
            )

        same_rpm = df[df["rpm"] == normalized.get("rpm")]
        candidate_df = same_rpm if len(same_rpm) >= max(20, top_k) else df
        _, matrix = self._prepare_history_matrix(candidate_df)
        inv_cov = self._inverse_covariance(matrix)

        event_vector = pd.DataFrame([{feature: normalized.get(feature, np.nan) for feature in FEATURE_COLUMNS}])
        event_vector = event_vector.fillna(candidate_df[FEATURE_COLUMNS].median())
        scaled_event = self.scaler.transform(event_vector)
        distances = self._mahalanobis_distances(matrix, scaled_event, inv_cov)
        weights = 1.0 / (distances + 0.05)
        ranked = (
            candidate_df.assign(similarity_distance=distances, vote_weight=weights)
            .sort_values("similarity_distance")
            .head(top_k)
        )

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
                    "vote_weight": round(_safe_float(row["vote_weight"]), 6),
                }
            )

        fault_distribution = self._weighted_fault_distribution(ranked)
        candidate_fault = fault_distribution[0]["canonical_fault"] if fault_distribution else canonicalize_fault_label(normalized.get("fault"))
        confidence_pct = float(fault_distribution[0]["pct"]) if fault_distribution else 0.0
        squared_ood_score = self._class_ood_score(candidate_df, candidate_fault, scaled_event) ** 2
        ood_threshold_95_sq = self._chi_square_threshold(len(FEATURE_COLUMNS), 0.95)
        ood_threshold_99_sq = self._chi_square_threshold(len(FEATURE_COLUMNS), 0.99)
        ood_flag = squared_ood_score > ood_threshold_99_sq
        if squared_ood_score > ood_threshold_99_sq:
            ood_status = "ood"
        elif squared_ood_score > ood_threshold_95_sq:
            ood_status = "fronteira"
        else:
            ood_status = "in_distribution"
        summary = (
            (
                f"{len(neighbors)} vizinhos recuperados"
                f" | metrica: Mahalanobis + k-NN ponderado"
                f" | principal hipótese histórica: {fault_distribution[0]['label']}"
                f" | confiança ponderada: {confidence_pct:.2f}%"
                f" | OOD: {ood_status} (score={math.sqrt(squared_ood_score):.3f})"
            )
            if fault_distribution
            else "Sem distribuição de falhas."
        )
        return HistorySearchResult(
            neighbors=neighbors,
            fault_distribution=fault_distribution,
            candidate_fault=candidate_fault,
            confidence_pct=confidence_pct,
            similarity_metric="mahalanobis_weighted_knn",
            ood_score=round(math.sqrt(squared_ood_score), 4),
            ood_threshold_95=round(math.sqrt(ood_threshold_95_sq), 4),
            ood_threshold_99=round(math.sqrt(ood_threshold_99_sq), 4),
            ood_flag=ood_flag,
            ood_status=ood_status,
            summary=summary,
        )

    @cached_property
    def _dataset_metrics_cache(self) -> dict[str, Any]:
        if DATASET_METRICS_SNAPSHOT_PATH.exists():
            return json.loads(DATASET_METRICS_SNAPSHOT_PATH.read_text(encoding="utf-8"))

        df = self.load_dataset()
        canonical_series = df["canonical_fault"].dropna()
        state_labels = sorted({label for label in canonical_series.unique().tolist() if is_state_label(label)})
        fault_labels = sorted({label for label in canonical_series.unique().tolist() if is_fault_label(label)})
        fault_mask = df["canonical_fault"].map(is_fault_label)
        state_mask = df["canonical_fault"].map(is_state_label)
        fault_counts = df.loc[fault_mask, "canonical_fault"].value_counts().to_dict()
        state_counts = df.loc[state_mask, "canonical_fault"].value_counts().to_dict()
        return {
            "rows": len(df),
            "raw_faults": int(df["fault"].nunique()),
            "canonical_faults": int(df["canonical_fault"].nunique()),
            "state_labels": len(state_labels),
            "fault_labels": len(fault_labels),
            "state_catalog": state_labels,
            "fault_catalog": fault_labels,
            "fault_rows": int(fault_mask.sum()),
            "state_rows": int(state_mask.sum()),
            "min_date": df["created_at"].min(),
            "max_date": df["created_at"].max(),
            "rpm_counts": df["rpm"].value_counts().sort_index().to_dict(),
            "fault_counts": df["canonical_fault"].value_counts().to_dict(),
            "real_fault_counts": fault_counts,
            "state_counts": state_counts,
        }

    def dataset_metrics(self) -> dict[str, Any]:
        return deepcopy(self._dataset_metrics_cache)

    def storage_metrics(self) -> dict[str, Any]:
        return deepcopy(self._storage_metrics_cache)

    @cached_property
    def _storage_metrics_cache(self) -> dict[str, Any]:
        csv_rows = self.dataset_metrics()["rows"]
        stored_rows = STORE.get_counts()["history"]
        gap = csv_rows - stored_rows
        coverage_pct = round((stored_rows / csv_rows) * 100, 2) if csv_rows else 0.0
        return {
            "csv_rows": csv_rows,
            "stored_rows": stored_rows,
            "gap_rows": gap,
            "coverage_pct": coverage_pct,
            "is_fully_synced": gap == 0,
        }


HISTORY_SERVICE = HistoryService()
