from __future__ import annotations

from collections import Counter
from statistics import NormalDist
from time import perf_counter
from typing import Any
from urllib import request
import json
import re

import numpy as np
import pandas as pd
from groq import Groq
from sklearn.neighbors import NearestCentroid
from sklearn.preprocessing import StandardScaler

from src.document_service import DOCUMENT_SERVICE
from src.fault_semantics import canonicalize_fault_label, format_fault_label_pt
from src.history_service import FEATURE_COLUMNS, HISTORY_SERVICE
from src.settings import SETTINGS
from src.vectorization import cosine_similarity, embed_many, embed_text

SEED = 42
TOP_K = 5
BENCHMARK_FAMILIES = [
    "desalinhamento",
    "desbalanceamento",
    "rolamento_inner",
    "correia",
    "cocked_rotor",
]
SAMPLES_PER_FAMILY = 10
TOTAL_EXPECTED_SAMPLES = len(BENCHMARK_FAMILIES) * SAMPLES_PER_FAMILY
GROQ_MODEL = "llama-3.1-8b-instant"
OLLAMA_MODEL = "qwen2.5-coder:7b"
GROQ_CLIENT = Groq(api_key=SETTINGS.groq_api_key) if SETTINGS.groq_api_key else None


def safe_float(value: Any, default: float = np.nan) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def extract_json(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return {}
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}


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


def event_payload_from_row(row: pd.Series) -> dict[str, Any]:
    payload = {
        "id": int(row["id"]) if not pd.isna(row["id"]) else None,
        "created_at": str(row.get("created_at", "")),
        "fault": "nao_informada",
    }
    for feature in FEATURE_COLUMNS:
        payload[feature] = safe_float(row.get(feature))
    payload["rpm"] = safe_float(row.get("rpm"))
    payload["temperature_c"] = safe_float(row.get("temperature_c"))
    return payload


def event_to_text(event: dict[str, Any], include_label: bool = False, label: str | None = None) -> str:
    lines = [
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
    if include_label and label:
        lines.append(f"fault_class: {label}")
        lines.append(f"fault_label_pt: {format_fault_label_pt(label)}")
    return "\n".join(lines)


def chat_complete_groq(messages: list[dict[str, str]], model: str) -> tuple[str, dict[str, Any]]:
    if GROQ_CLIENT is None:
        raise RuntimeError("GROQ_API_KEY ausente.")
    completion = GROQ_CLIENT.chat.completions.create(model=model, temperature=0, messages=messages)
    content = completion.choices[0].message.content or ""
    usage = {
        "prompt_tokens": getattr(completion.usage, "prompt_tokens", None),
        "completion_tokens": getattr(completion.usage, "completion_tokens", None),
        "total_tokens": getattr(completion.usage, "total_tokens", None),
    }
    return content, usage


def chat_complete_ollama(messages: list[dict[str, str]], model: str) -> tuple[str, dict[str, Any]]:
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0},
    }
    req = request.Request(
        url=f"{SETTINGS.ollama_base_url}/api/chat",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=180) as response:
        data = json.loads(response.read().decode("utf-8"))
    content = ((data.get("message") or {}).get("content") or "").strip()
    usage = {
        "prompt_tokens": data.get("prompt_eval_count"),
        "completion_tokens": data.get("eval_count"),
        "total_tokens": (data.get("prompt_eval_count") or 0) + (data.get("eval_count") or 0),
    }
    return content, usage


def prepare_data(
    benchmark_families: list[str] | None = None,
    samples_per_family: int = SAMPLES_PER_FAMILY,
    seed: int = SEED,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    families = benchmark_families or BENCHMARK_FAMILIES
    DOCUMENT_SERVICE.ingest_default_documents()
    df = HISTORY_SERVICE.load_dataset().copy()
    df["canonical_fault"] = df["canonical_fault"].map(canonicalize_fault_label)
    eligible_df = df[df["canonical_fault"].isin(families)].copy()

    sample_frames = []
    for family in families:
        family_df = eligible_df[eligible_df["canonical_fault"] == family].copy()
        if len(family_df) < samples_per_family:
            raise ValueError(f"Familia {family} nao possui amostras suficientes.")
        sample_frames.append(family_df.sample(samples_per_family, random_state=seed))

    benchmark_df = pd.concat(sample_frames, ignore_index=True)
    benchmark_df = benchmark_df.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    reference_df = eligible_df[~eligible_df["id"].isin(set(benchmark_df["id"]))].copy().reset_index(drop=True)

    assert len(benchmark_df) == len(families) * samples_per_family
    assert benchmark_df["canonical_fault"].value_counts().eq(samples_per_family).all()
    return benchmark_df, reference_df


def build_reference_artifacts(reference_df: pd.DataFrame) -> dict[str, Any]:
    reference_features = reference_df[FEATURE_COLUMNS].copy().fillna(reference_df[FEATURE_COLUMNS].median())
    scaler = StandardScaler().fit(reference_features)
    reference_scaled = scaler.transform(reference_features)

    reference_text_records = []
    for _, row in reference_df.iterrows():
        event = event_payload_from_row(row)
        label = canonicalize_fault_label(row["canonical_fault"])
        text = event_to_text(event, include_label=True, label=label)
        reference_text_records.append(
            {
                "id": int(row["id"]),
                "label": label,
                "text": text,
                "event": event,
            }
        )

    reference_text_vectors = embed_many([item["text"] for item in reference_text_records])
    for item, vector in zip(reference_text_records, reference_text_vectors, strict=False):
        item["vector"] = vector

    centroid_model = NearestCentroid()
    centroid_model.fit(reference_scaled, reference_df["canonical_fault"])
    return {
        "scaler": scaler,
        "reference_scaled": reference_scaled,
        "reference_text_records": reference_text_records,
        "centroid_model": centroid_model,
    }


def inverse_covariance(matrix: np.ndarray) -> np.ndarray:
    covariance = np.cov(matrix, rowvar=False)
    regularization = np.eye(covariance.shape[0]) * 1e-6
    return np.linalg.pinv(covariance + regularization)


def mahalanobis_distances(matrix: np.ndarray, query_vector: np.ndarray, inv_cov: np.ndarray) -> np.ndarray:
    deltas = matrix - query_vector
    squared = np.einsum("ij,jk,ik->i", deltas, inv_cov, deltas)
    squared = np.clip(squared, a_min=0.0, a_max=None)
    return np.sqrt(squared)


def chi_square_threshold(degrees_of_freedom: int, confidence: float) -> float:
    z_score = NormalDist().inv_cdf(confidence)
    factor = 1 - (2 / (9 * degrees_of_freedom)) + z_score * np.sqrt(2 / (9 * degrees_of_freedom))
    return float(max(degrees_of_freedom * (factor**3), 0.0))


def candidate_reference(reference_slice: pd.DataFrame, event: dict[str, Any], top_k: int = TOP_K) -> pd.DataFrame:
    same_rpm = reference_slice[reference_slice["rpm"] == event.get("rpm")]
    return same_rpm if len(same_rpm) >= max(20, top_k) else reference_slice


def predict_euclidean_knn(event: dict[str, Any], reference_df: pd.DataFrame, scaler: StandardScaler) -> dict[str, Any]:
    started = perf_counter()
    candidate_df = candidate_reference(reference_df, event)
    candidate_features = candidate_df[FEATURE_COLUMNS].copy().fillna(reference_df[FEATURE_COLUMNS].median())
    candidate_scaled = scaler.transform(candidate_features)
    event_frame = pd.DataFrame([{feature: event.get(feature, np.nan) for feature in FEATURE_COLUMNS}]).fillna(
        reference_df[FEATURE_COLUMNS].median()
    )
    event_scaled = scaler.transform(event_frame)
    distances = np.linalg.norm(candidate_scaled - event_scaled, axis=1)
    ranked = candidate_df.assign(score=distances).sort_values("score").head(TOP_K)
    majority = ranked["canonical_fault"].mode().iloc[0]
    return {
        "predicted_fault": majority,
        "confidence_proxy": round((ranked["canonical_fault"] == majority).mean() * 100, 2),
        "elapsed_ms": round((perf_counter() - started) * 1000, 3),
    }


def predict_mahalanobis_weighted_knn(event: dict[str, Any], reference_df: pd.DataFrame, scaler: StandardScaler) -> dict[str, Any]:
    started = perf_counter()
    candidate_df = candidate_reference(reference_df, event)
    candidate_features = candidate_df[FEATURE_COLUMNS].copy().fillna(reference_df[FEATURE_COLUMNS].median())
    candidate_scaled = scaler.transform(candidate_features)
    event_frame = pd.DataFrame([{feature: event.get(feature, np.nan) for feature in FEATURE_COLUMNS}]).fillna(
        reference_df[FEATURE_COLUMNS].median()
    )
    event_scaled = scaler.transform(event_frame)
    inv_cov = inverse_covariance(candidate_scaled)
    distances = mahalanobis_distances(candidate_scaled, event_scaled, inv_cov)
    weights = 1.0 / (distances + 0.05)
    ranked = candidate_df.assign(score=distances, vote_weight=weights).sort_values("score").head(TOP_K)
    weighted_votes = ranked.groupby("canonical_fault")["vote_weight"].sum().sort_values(ascending=False)
    majority = weighted_votes.index[0]
    confidence = round(float(weighted_votes.iloc[0] / weighted_votes.sum()) * 100, 2)

    class_df = candidate_df[candidate_df["canonical_fault"] == majority]
    if len(class_df) < 3:
        class_df = candidate_df
    class_scaled = scaler.transform(class_df[FEATURE_COLUMNS].copy().fillna(reference_df[FEATURE_COLUMNS].median()))
    class_inv_cov = inverse_covariance(class_scaled)
    class_centroid = class_scaled.mean(axis=0, keepdims=True)
    ood_score = float(mahalanobis_distances(class_centroid, event_scaled, class_inv_cov)[0])
    ood_threshold_99 = float(np.sqrt(chi_square_threshold(len(FEATURE_COLUMNS), 0.99)))

    return {
        "predicted_fault": majority,
        "confidence_proxy": confidence,
        "elapsed_ms": round((perf_counter() - started) * 1000, 3),
        "ood_flag": ood_score > ood_threshold_99,
        "ood_score": round(ood_score, 4),
    }


def predict_cosine_knn(event: dict[str, Any], reference_df: pd.DataFrame, scaler: StandardScaler) -> dict[str, Any]:
    started = perf_counter()
    candidate_df = candidate_reference(reference_df, event)
    candidate_features = candidate_df[FEATURE_COLUMNS].copy().fillna(reference_df[FEATURE_COLUMNS].median())
    candidate_scaled = scaler.transform(candidate_features)
    event_frame = pd.DataFrame([{feature: event.get(feature, np.nan) for feature in FEATURE_COLUMNS}]).fillna(
        reference_df[FEATURE_COLUMNS].median()
    )
    event_scaled = scaler.transform(event_frame)[0]
    similarities = np.array([cosine_similarity(event_scaled.tolist(), row.tolist()) for row in candidate_scaled])
    ranked = candidate_df.assign(score=similarities).sort_values("score", ascending=False).head(TOP_K)
    majority = ranked["canonical_fault"].mode().iloc[0]
    return {
        "predicted_fault": majority,
        "confidence_proxy": round((ranked["canonical_fault"] == majority).mean() * 100, 2),
        "elapsed_ms": round((perf_counter() - started) * 1000, 3),
    }


def predict_centroid_euclidean(
    event: dict[str, Any],
    reference_df: pd.DataFrame,
    scaler: StandardScaler,
    centroid_model: NearestCentroid,
) -> dict[str, Any]:
    started = perf_counter()
    event_frame = pd.DataFrame([{feature: event.get(feature, np.nan) for feature in FEATURE_COLUMNS}]).fillna(
        reference_df[FEATURE_COLUMNS].median()
    )
    event_scaled = scaler.transform(event_frame)
    predicted = centroid_model.predict(event_scaled)[0]
    distances = np.linalg.norm(centroid_model.centroids_ - event_scaled[0], axis=1)
    return {
        "predicted_fault": predicted,
        "confidence_proxy": round(100 / (1 + float(np.min(distances))), 2),
        "elapsed_ms": round((perf_counter() - started) * 1000, 3),
    }


def predict_text_vector_vote(event: dict[str, Any], reference_text_records: list[dict[str, Any]]) -> dict[str, Any]:
    started = perf_counter()
    query_text = event_to_text(event, include_label=False)
    query_vector = embed_text(query_text)
    ranked = sorted(
        (
            {
                "label": item["label"],
                "score": cosine_similarity(query_vector, item["vector"]),
            }
            for item in reference_text_records
        ),
        key=lambda item: item["score"],
        reverse=True,
    )[:TOP_K]
    majority = Counter([item["label"] for item in ranked]).most_common(1)[0][0]
    return {
        "predicted_fault": majority,
        "confidence_proxy": round((sum(item["label"] == majority for item in ranked) / TOP_K) * 100, 2),
        "elapsed_ms": round((perf_counter() - started) * 1000, 3),
    }


def retrieve_vector_examples(event: dict[str, Any], reference_text_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    query_text = event_to_text(event, include_label=False)
    query_vector = embed_text(query_text)
    ranked = []
    for item in reference_text_records:
        ranked.append(
            {
                "id": item["id"],
                "canonical_fault": item["label"],
                "label_pt": format_fault_label_pt(item["label"]),
                "score": round(cosine_similarity(query_vector, item["vector"]), 4),
                "text": item["text"],
            }
        )
    return sorted(ranked, key=lambda x: x["score"], reverse=True)[:TOP_K]


def predict_llm_vector_rag(
    event: dict[str, Any],
    provider: str,
    model: str,
    reference_text_records: list[dict[str, Any]],
    benchmark_families: list[str] | None = None,
) -> dict[str, Any]:
    started = perf_counter()
    query_text = event_to_text(event, include_label=False)
    examples = retrieve_vector_examples(event, reference_text_records)
    doc_result = DOCUMENT_SERVICE.search_chunks(query_text=query_text, top_k=4)
    allowed_classes = benchmark_families or BENCHMARK_FAMILIES
    prompt = f"""Voce e um classificador tecnico de falhas de manutencao prescritiva.

Classes permitidas: {", ".join(allowed_classes)}

Responda apenas em JSON com:
- predicted_fault
- confidence_pct
- rationale
"""
    payload = {
        "event": event,
        "retrieved_examples": [
            {
                "canonical_fault": item["canonical_fault"],
                "label_pt": item["label_pt"],
                "score": item["score"],
                "text": item["text"][:500],
            }
            for item in examples
        ],
        "retrieved_document_chunks": [
            {
                "title": item["title"],
                "fault_family": item["fault_family"],
                "score": item["score"],
                "excerpt": item["chunk_text"][:400],
            }
            for item in doc_result.chunks
        ],
    }
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, default=str)},
    ]
    if provider == "groq":
        content, usage = chat_complete_groq(messages, model)
    elif provider == "ollama":
        content, usage = chat_complete_ollama(messages, model)
    else:
        raise ValueError(f"Provider desconhecido: {provider}")
    parsed = extract_json(content)
    predicted_fault = canonicalize_fault_label(parsed.get("predicted_fault"))
    return {
        "predicted_fault": predicted_fault,
        "confidence_proxy": parsed.get("confidence_pct"),
        "elapsed_ms": round((perf_counter() - started) * 1000, 3),
        "usage": usage,
        "raw_response": content,
    }
