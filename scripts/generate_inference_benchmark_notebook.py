from __future__ import annotations

from pathlib import Path
import json


ROOT = Path(__file__).resolve().parent.parent
NOTEBOOK_PATH = ROOT / "notebooks" / "02_benchmark_tecnicas_inferencia_llm_vs_numericas.ipynb"


def md_cell(source: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": source.splitlines(keepends=True),
    }


def code_cell(source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source.splitlines(keepends=True),
    }


cells = [
    md_cell(
        """# Benchmark de Tecnicas de Inferencia: numericas vs LLM total com vetores

Este notebook compara o **motor atual baseado em similaridade numerica** com tecnicas alternativas, incluindo uma rota de **LLM total com recuperacao vetorial**.

## Objetivo

Comparar, em uma amostra robusta de **50 eventos balanceados**, cinco tecnicas:

1. `euclidean_knn`: voto majoritario dos vizinhos mais proximos por distancia Euclidiana.
2. `cosine_knn`: voto majoritario por similaridade cosseno nas features escaladas.
3. `centroid_euclidean`: classificador por centroide de classe.
4. `text_vector_vote`: textualizacao do evento + vetores locais + voto por exemplos recuperados.
5. `llm_vector_rag`: inferencia total pelo LLM usando exemplos recuperados por vetor e chunks documentais.

## Pergunta experimental

Em um contexto de manutencao prescritiva com dados tabulares de sensores e base documental limitada:

- o motor numerico simples continua sendo competitivo?
- um fluxo **LLM total com vetores** consegue gerar classificacao mais aderente?
- tecnicas textuais e vetoriais sem ajuste fino oferecem ganho real sobre a base atual?
"""
    ),
    md_cell(
        """## Literatura primaria que motiva o experimento

Este benchmark foi desenhado com base nas seguintes referencias:

1. **FD-LLM: Large Language Model for Fault Diagnosis of Machines** (Qaid et al., 2024, arXiv:2412.01218)  
   Link: https://arxiv.org/abs/2412.01218  
   Ideia aproveitada aqui: textualizar sinais ou features e permitir que o LLM realize a classificacao diagnostica.

2. **Agent-based Condition Monitoring Assistance with Multimodal Industrial Database Retrieval Augmented Generation** (Lowenmark et al., 2025, arXiv:2506.09247)  
   Link: https://arxiv.org/abs/2506.09247  
   Ideia aproveitada aqui: usar recuperacao estruturada e RAG multimodal/semi-estruturado para apoiar decisao em condition monitoring.

3. **Complex System Diagnostics Using a Knowledge Graph-Informed and Large Language Model-Enhanced Framework** (Marandi et al., 2025, arXiv:2505.21291)  
   Link: https://arxiv.org/abs/2505.21291  
   Ideia aproveitada aqui: o LLM melhora a interacao e a explicabilidade, mas deve ser ancorado em conhecimento externo e ferramentas.

4. **Large Language Models in Process Systems Engineering: Opportunities, Architectures, and Industrial Deployment Challenges** (Gopaluni et al., 2026, arXiv:2606.11589)  
   Link: https://arxiv.org/abs/2606.11589  
   Insight adotado: LLMs sao promissores para raciocinio com contexto e documentacao, mas tarefas de execucao numerica e garantias formais continuam desafiadoras.

### Hipotese de trabalho

- A literatura recente **nao descarta** LLMs para diagnostico industrial.
- Mas os trabalhos mais fortes costumam:
  - textualizar sinais ou features;
  - usar recuperacao externa;
  - ou fine-tunar o modelo para a tarefa.
- Por isso este notebook compara:
  - tecnicas numericas puras;
  - tecnicas vetoriais textuais sem LLM;
  - e uma tecnica de **LLM total com vetores**, mais proxima da narrativa agentic/LLM-first.
"""
    ),
    code_cell(
        """from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from time import perf_counter
import json
import math
import re

import numpy as np
import pandas as pd
import plotly.express as px
from groq import Groq
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.neighbors import NearestCentroid
from sklearn.preprocessing import StandardScaler

from src.document_service import DOCUMENT_SERVICE
from src.fault_semantics import canonicalize_fault_label, format_fault_label_pt
from src.history_service import FEATURE_COLUMNS, HISTORY_SERVICE
from src.settings import SETTINGS
from src.vectorization import cosine_similarity, embed_many, embed_text
"""
    ),
    code_cell(
        """SEED = 42
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

RUN_LLM_VECTOR_BENCHMARK = bool(SETTINGS.groq_api_key)
LLM_MODEL = SETTINGS.default_llm_model
LLM_TEMPERATURE = 0.0
MAX_LLM_SAMPLES = 50

print({
    "RUN_LLM_VECTOR_BENCHMARK": RUN_LLM_VECTOR_BENCHMARK,
    "LLM_MODEL": LLM_MODEL,
    "MAX_LLM_SAMPLES": MAX_LLM_SAMPLES,
    "TOTAL_EXPECTED_SAMPLES": TOTAL_EXPECTED_SAMPLES,
})
"""
    ),
    code_cell(
        """DOCUMENT_SERVICE.ingest_default_documents()
df = HISTORY_SERVICE.load_dataset().copy()
df["canonical_fault"] = df["canonical_fault"].map(canonicalize_fault_label)

eligible_df = df[df["canonical_fault"].isin(BENCHMARK_FAMILIES)].copy()
family_counts = eligible_df["canonical_fault"].value_counts().sort_index()
display(family_counts.to_frame("rows"))

sample_frames = []
for family in BENCHMARK_FAMILIES:
    family_df = eligible_df[eligible_df["canonical_fault"] == family].copy()
    if len(family_df) < SAMPLES_PER_FAMILY:
        raise ValueError(f"Familia {family} nao possui amostras suficientes para {SAMPLES_PER_FAMILY} eventos.")
    sample_frames.append(family_df.sample(SAMPLES_PER_FAMILY, random_state=SEED))

benchmark_df = pd.concat(sample_frames, ignore_index=True)
benchmark_df = benchmark_df.sample(frac=1.0, random_state=SEED).reset_index(drop=True)
reference_df = eligible_df[~eligible_df["id"].isin(set(benchmark_df["id"]))].copy().reset_index(drop=True)

assert len(benchmark_df) == TOTAL_EXPECTED_SAMPLES
assert benchmark_df["canonical_fault"].value_counts().eq(SAMPLES_PER_FAMILY).all()

display(benchmark_df[["id", "canonical_fault", "rpm", "temperature_c", "x_rms_velocity_mm_s", "z_rms_velocity_mm_s"]].head())
print("Reference rows:", len(reference_df))
"""
    ),
    code_cell(
        """def safe_float(value, default=np.nan):
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def event_payload_from_row(row: pd.Series) -> dict:
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


def event_to_text(event: dict, include_label: bool = False, label: str | None = None) -> str:
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
    return "\\n".join(lines)


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

print("Prepared reference artifacts.")
"""
    ),
    code_cell(
        """def _candidate_reference(reference_slice: pd.DataFrame, event: dict, top_k: int = TOP_K) -> pd.DataFrame:
    same_rpm = reference_slice[reference_slice["rpm"] == event.get("rpm")]
    return same_rpm if len(same_rpm) >= max(20, top_k) else reference_slice


def predict_euclidean_knn(event: dict, reference_slice: pd.DataFrame, top_k: int = TOP_K) -> dict:
    started = perf_counter()
    candidate_df = _candidate_reference(reference_slice, event, top_k=top_k)
    candidate_features = candidate_df[FEATURE_COLUMNS].copy().fillna(reference_df[FEATURE_COLUMNS].median())
    candidate_scaled = scaler.transform(candidate_features)
    event_frame = pd.DataFrame([{feature: event.get(feature, np.nan) for feature in FEATURE_COLUMNS}]).fillna(reference_df[FEATURE_COLUMNS].median())
    event_scaled = scaler.transform(event_frame)
    distances = np.linalg.norm(candidate_scaled - event_scaled, axis=1)
    ranked = candidate_df.assign(score=distances).sort_values("score").head(top_k)
    majority = ranked["canonical_fault"].mode().iloc[0]
    elapsed_ms = round((perf_counter() - started) * 1000, 3)
    return {
        "predicted_fault": majority,
        "confidence_proxy": round((ranked["canonical_fault"] == majority).mean() * 100, 2),
        "elapsed_ms": elapsed_ms,
        "neighbors": ranked[["id", "canonical_fault", "score"]].to_dict(orient="records"),
    }


def predict_cosine_knn(event: dict, reference_slice: pd.DataFrame, top_k: int = TOP_K) -> dict:
    started = perf_counter()
    candidate_df = _candidate_reference(reference_slice, event, top_k=top_k)
    candidate_features = candidate_df[FEATURE_COLUMNS].copy().fillna(reference_df[FEATURE_COLUMNS].median())
    candidate_scaled = scaler.transform(candidate_features)
    event_frame = pd.DataFrame([{feature: event.get(feature, np.nan) for feature in FEATURE_COLUMNS}]).fillna(reference_df[FEATURE_COLUMNS].median())
    event_scaled = scaler.transform(event_frame)[0]
    similarities = np.array([
        cosine_similarity(event_scaled.tolist(), row.tolist())
        for row in candidate_scaled
    ])
    ranked = candidate_df.assign(score=similarities).sort_values("score", ascending=False).head(top_k)
    majority = ranked["canonical_fault"].mode().iloc[0]
    elapsed_ms = round((perf_counter() - started) * 1000, 3)
    return {
        "predicted_fault": majority,
        "confidence_proxy": round((ranked["canonical_fault"] == majority).mean() * 100, 2),
        "elapsed_ms": elapsed_ms,
        "neighbors": ranked[["id", "canonical_fault", "score"]].to_dict(orient="records"),
    }


def predict_centroid_euclidean(event: dict) -> dict:
    started = perf_counter()
    event_frame = pd.DataFrame([{feature: event.get(feature, np.nan) for feature in FEATURE_COLUMNS}]).fillna(reference_df[FEATURE_COLUMNS].median())
    event_scaled = scaler.transform(event_frame)
    predicted = centroid_model.predict(event_scaled)[0]
    distances = np.linalg.norm(centroid_model.centroids_ - event_scaled[0], axis=1)
    min_distance = float(np.min(distances))
    elapsed_ms = round((perf_counter() - started) * 1000, 3)
    return {
        "predicted_fault": predicted,
        "confidence_proxy": round(100 / (1 + min_distance), 2),
        "elapsed_ms": elapsed_ms,
        "centroid_distance": min_distance,
    }


def predict_text_vector_vote(event: dict, top_k: int = TOP_K) -> dict:
    started = perf_counter()
    query_text = event_to_text(event, include_label=False)
    query_vector = embed_text(query_text)
    ranked = []
    for item in reference_text_records:
        ranked.append({
            "id": item["id"],
            "label": item["label"],
            "score": cosine_similarity(query_vector, item["vector"]),
        })
    ranked = sorted(ranked, key=lambda x: x["score"], reverse=True)[:top_k]
    majority = Counter([item["label"] for item in ranked]).most_common(1)[0][0]
    elapsed_ms = round((perf_counter() - started) * 1000, 3)
    return {
        "predicted_fault": majority,
        "confidence_proxy": round((sum(item["label"] == majority for item in ranked) / top_k) * 100, 2),
        "elapsed_ms": elapsed_ms,
        "neighbors": ranked,
    }
"""
    ),
    code_cell(
        """LLM_CLIENT = Groq(api_key=SETTINGS.groq_api_key) if SETTINGS.groq_api_key else None


def extract_json(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\\{.*\\}", text, re.DOTALL)
        if not match:
            return {}
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}


def retrieve_vector_examples(event: dict, top_k: int = TOP_K) -> list[dict]:
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
    return sorted(ranked, key=lambda x: x["score"], reverse=True)[:top_k]


LLM_VECTOR_SYSTEM_PROMPT = f\"\"\"Voce e um classificador tecnico de falhas de manutencao prescritiva.

Seu trabalho e inferir a classe de falha mais provavel usando:
- o evento atual;
- exemplos historicos recuperados por similaridade vetorial;
- trechos documentais recuperados.

Classes permitidas:
{", ".join(BENCHMARK_FAMILIES)}

Regras:
- nao use conhecimento externo;
- priorize as evidencias recuperadas;
- se houver conflito, explique de forma curta;
- responda apenas em JSON com:
  predicted_fault
  confidence_pct
  rationale
\"\"\"


def predict_llm_vector_rag(event: dict, top_k: int = TOP_K) -> dict:
    if not RUN_LLM_VECTOR_BENCHMARK or LLM_CLIENT is None:
        return {
            "predicted_fault": None,
            "confidence_proxy": None,
            "elapsed_ms": None,
            "skipped": True,
            "reason": "GROQ_API_KEY ausente ou benchmark LLM desativado.",
        }

    started = perf_counter()
    query_text = event_to_text(event, include_label=False)
    examples = retrieve_vector_examples(event, top_k=top_k)
    doc_result = DOCUMENT_SERVICE.search_chunks(query_text=query_text, top_k=4)
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
    completion = LLM_CLIENT.chat.completions.create(
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE,
        messages=[
            {"role": "system", "content": LLM_VECTOR_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False, default=str)},
        ],
    )
    content = completion.choices[0].message.content or ""
    parsed = extract_json(content)
    predicted_fault = canonicalize_fault_label(parsed.get("predicted_fault"))
    elapsed_ms = round((perf_counter() - started) * 1000, 3)
    return {
        "predicted_fault": predicted_fault,
        "confidence_proxy": parsed.get("confidence_pct"),
        "elapsed_ms": elapsed_ms,
        "raw_response": content,
        "examples": examples,
        "documents": doc_result.chunks,
    }
"""
    ),
    code_cell(
        """TECHNIQUES = {
    "euclidean_knn": lambda event: predict_euclidean_knn(event, reference_df),
    "cosine_knn": lambda event: predict_cosine_knn(event, reference_df),
    "centroid_euclidean": predict_centroid_euclidean,
    "text_vector_vote": predict_text_vector_vote,
    "llm_vector_rag": predict_llm_vector_rag,
}


records = []
llm_counter = 0
for _, row in benchmark_df.iterrows():
    event = event_payload_from_row(row)
    true_fault = canonicalize_fault_label(row["canonical_fault"])
    for technique_name, predictor in TECHNIQUES.items():
        if technique_name == "llm_vector_rag" and llm_counter >= MAX_LLM_SAMPLES:
            continue
        result = predictor(event)
        if technique_name == "llm_vector_rag":
            llm_counter += 1
        records.append(
            {
                "sample_id": int(row["id"]),
                "true_fault": true_fault,
                "technique": technique_name,
                "predicted_fault": result.get("predicted_fault"),
                "confidence_proxy": result.get("confidence_proxy"),
                "elapsed_ms": result.get("elapsed_ms"),
                "correct": result.get("predicted_fault") == true_fault if result.get("predicted_fault") else False,
                "skipped": bool(result.get("skipped", False)),
            }
        )

results_df = pd.DataFrame(records)
results_df.head()
"""
    ),
    code_cell(
        """metrics_rows = []
for technique, part in results_df.groupby("technique"):
    valid = part[~part["predicted_fault"].isna()].copy()
    if valid.empty:
        metrics_rows.append(
            {
                "technique": technique,
                "rows": len(part),
                "accuracy": np.nan,
                "macro_f1": np.nan,
                "avg_latency_ms": np.nan,
                "skipped_rows": int(part["skipped"].sum()),
            }
        )
        continue
    metrics_rows.append(
        {
            "technique": technique,
            "rows": len(valid),
            "accuracy": round(accuracy_score(valid["true_fault"], valid["predicted_fault"]), 4),
            "macro_f1": round(f1_score(valid["true_fault"], valid["predicted_fault"], average="macro"), 4),
            "avg_latency_ms": round(valid["elapsed_ms"].dropna().mean(), 3),
            "skipped_rows": int(part["skipped"].sum()),
        }
    )

metrics_df = pd.DataFrame(metrics_rows).sort_values(["accuracy", "macro_f1"], ascending=False)
display(metrics_df)
"""
    ),
    code_cell(
        """fig_acc = px.bar(
    metrics_df,
    x="technique",
    y="accuracy",
    color="technique",
    title="Acuracia por tecnica em 50 amostras balanceadas",
    text="accuracy",
)
fig_acc.update_layout(showlegend=False)
fig_acc.show()

fig_f1 = px.bar(
    metrics_df,
    x="technique",
    y="macro_f1",
    color="technique",
    title="Macro-F1 por tecnica",
    text="macro_f1",
)
fig_f1.update_layout(showlegend=False)
fig_f1.show()

fig_latency = px.bar(
    metrics_df,
    x="technique",
    y="avg_latency_ms",
    color="technique",
    title="Latencia media por tecnica (ms)",
    text="avg_latency_ms",
)
fig_latency.update_layout(showlegend=False)
fig_latency.show()
"""
    ),
    code_cell(
        """for technique in results_df["technique"].unique():
    part = results_df[(results_df["technique"] == technique) & (~results_df["predicted_fault"].isna())].copy()
    if part.empty:
        print(f"\\n=== {technique} ===")
        print("Sem resultados validos.")
        continue
    labels = sorted(set(part["true_fault"]).union(set(part["predicted_fault"])))
    cm = confusion_matrix(part["true_fault"], part["predicted_fault"], labels=labels)
    cm_df = pd.DataFrame(cm, index=[f"real::{x}" for x in labels], columns=[f"pred::{x}" for x in labels])
    print(f"\\n=== {technique} ===")
    display(cm_df)
    print(classification_report(part["true_fault"], part["predicted_fault"], labels=labels, zero_division=0))
"""
    ),
    md_cell(
        """## Como interpretar os resultados

### Se o motor Euclidiano vencer

Isso sustenta a tese de que:

- para o dataset atual, a estrutura numerica tabular ainda carrega sinal diagnostico suficiente;
- o LLM agrega mais valor em **orquestracao, explicacao e prescricao** do que como classificador bruto sem ajuste fino;
- a arquitetura hibrida continua sendo mais prudente.

### Se `text_vector_vote` ou `llm_vector_rag` aproximarem ou superarem o baseline

Isso sustenta a narrativa de que:

- a textualizacao de features, como vista na literatura, pode ser viavel;
- a recuperacao vetorial de exemplos ajuda o LLM a raciocinar sobre contexto;
- um fluxo agentic LLM-first pode ser defendido de forma mais forte.

### Se `llm_vector_rag` ficar pior, mas com boas explicacoes

Isso ainda e um achado importante:

- o modelo pode ser melhor como camada de **interpretacao e decisao assistida**;
- o motor numerico ainda deve ficar como suporte forte da inferencia;
- a literatura mais robusta costuma usar fine-tuning, tokenizacao especializada, FFT ou pipelines mais estruturados do que prompting puro.
"""
    ),
    md_cell(
        """## Conclusao esperada para a prova

Este notebook nao tenta provar que o LLM sempre substitui o motor numerico. Ele foi criado para responder tecnicamente a pergunta:

> "Se quisermos empurrar mais a arquitetura para um LLM-first, o que acontece quando comparamos o baseline numerico com tecnicas textuais, vetoriais e LLM total?"

Com isso, voce consegue demonstrar:

- baseline numerico atual;
- alternativa vetorial textual;
- alternativa LLM total com vetores;
- comparacao robusta em 50 amostras balanceadas;
- alinhamento com literatura recente.
"""
    ),
]


notebook = {
    "cells": cells,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {
            "name": "python",
            "version": "3.14",
        },
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

NOTEBOOK_PATH.parent.mkdir(parents=True, exist_ok=True)
NOTEBOOK_PATH.write_text(json.dumps(notebook, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Notebook gerado em: {NOTEBOOK_PATH}")
