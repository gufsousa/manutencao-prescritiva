from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.metrics import silhouette_score
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.benchmark_shared import event_payload_from_row, event_to_text
from src.fault_semantics import canonicalize_fault_label, format_fault_label_pt
from src.history_service import FEATURE_COLUMNS, HISTORY_SERVICE
from src.vectorization import embed_many


OUTPUT_DIR = Path("docs/analise_markdown/viz_vizinhos_2026-08-06")
GLOBAL_HTML = OUTPUT_DIR / "01_espacos_numericos_vs_textuais.html"
CASES_HTML = OUTPUT_DIR / "02_casos_vizinhos_numericos_vs_textuais.html"
SUMMARY_MD = OUTPUT_DIR / "README.md"
METRICS_JSON = OUTPUT_DIR / "metrics.json"
NEIGHBORS_JSON = OUTPUT_DIR / "neighbor_cases.json"
BENCHMARK_RESULTS = Path("docs/analise_markdown/benchmark_full_inference_results_2026-08-05.csv")

FOCUS_CLASSES = [
    "cocked_rotor",
    "correia",
    "rolamento_inner",
    "rolamento_outer",
    "rolamento_ball",
    "desbalanceamento",
    "polia",
    "desalinhamento",
    "normal",
]
SAMPLES_PER_CLASS = 120
SEED = 42
TOP_K = 5

CASE_SPECS = [
    ("desbalanceamento", "desalinhamento"),
    ("cocked_rotor", "rolamento_inner"),
    ("rolamento_inner", "desalinhamento"),
]

COLORS = {
    "cocked_rotor": "#f59e0b",
    "correia": "#22c55e",
    "rolamento_inner": "#ef4444",
    "rolamento_outer": "#dc2626",
    "rolamento_ball": "#fb7185",
    "desbalanceamento": "#3b82f6",
    "polia": "#8b5cf6",
    "desalinhamento": "#14b8a6",
    "normal": "#94a3b8",
}


@dataclass
class CaseSelection:
    sample_id: int
    true_fault: str
    predicted_fault: str
    title: str


def load_balanced_subset() -> pd.DataFrame:
    df = HISTORY_SERVICE.load_dataset().copy()
    df["canonical_fault"] = df["canonical_fault"].map(canonicalize_fault_label)

    frames: list[pd.DataFrame] = []
    for label in FOCUS_CLASSES:
        part = df[df["canonical_fault"] == label].copy()
        if len(part) < SAMPLES_PER_CLASS:
            raise ValueError(f"Classe {label} nao possui {SAMPLES_PER_CLASS} amostras.")
        frames.append(part.sample(SAMPLES_PER_CLASS, random_state=SEED))

    subset = pd.concat(frames, ignore_index=True)
    subset = subset.drop_duplicates(subset=["id"]).reset_index(drop=True)
    return subset


def select_cases(subset: pd.DataFrame) -> list[CaseSelection]:
    benchmark_df = pd.read_csv(BENCHMARK_RESULTS)
    llm_df = benchmark_df[benchmark_df["technique"] == "llm_vector_rag_groq"].copy()
    cases: list[CaseSelection] = []

    required_ids: list[int] = []
    for true_fault, predicted_fault in CASE_SPECS:
        rows = llm_df[
            (llm_df["true_fault"] == true_fault)
            & (llm_df["predicted_fault"] == predicted_fault)
        ]
        if rows.empty:
            continue
        sample_id = int(rows.iloc[0]["sample_id"])
        required_ids.append(sample_id)
        cases.append(
            CaseSelection(
                sample_id=sample_id,
                true_fault=true_fault,
                predicted_fault=predicted_fault,
                title=f"{true_fault} -> {predicted_fault}",
            )
        )

    if required_ids:
        full_df = HISTORY_SERVICE.load_dataset().copy()
        full_df["canonical_fault"] = full_df["canonical_fault"].map(canonicalize_fault_label)
        extra = full_df[full_df["id"].isin(required_ids)].copy()
        subset = pd.concat([subset, extra], ignore_index=True).drop_duplicates(subset=["id"]).reset_index(drop=True)
    return cases, subset


def build_spaces(subset: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    numeric_df = subset[FEATURE_COLUMNS].copy()
    numeric_df = numeric_df.fillna(numeric_df.median())
    numeric = StandardScaler().fit_transform(numeric_df)

    texts = [event_to_text(event_payload_from_row(row), include_label=False) for _, row in subset.iterrows()]
    text = np.array(embed_many(texts), dtype=float)
    return numeric, text


def reduce_spaces(numeric: np.ndarray, text: np.ndarray) -> dict[str, np.ndarray]:
    text_pca_source = PCA(n_components=min(50, text.shape[1], len(text) - 1), random_state=SEED).fit_transform(text)

    return {
        "numeric_pca": PCA(n_components=2, random_state=SEED).fit_transform(numeric),
        "text_pca": PCA(n_components=2, random_state=SEED).fit_transform(text),
        "numeric_tsne": TSNE(
            n_components=2,
            random_state=SEED,
            perplexity=35,
            init="pca",
            learning_rate="auto",
        ).fit_transform(numeric),
        "text_tsne": TSNE(
            n_components=2,
            random_state=SEED,
            perplexity=35,
            init="pca",
            learning_rate="auto",
        ).fit_transform(text_pca_source),
    }


def neighbor_metrics(matrix: np.ndarray, labels: np.ndarray, metric: str) -> dict[str, float | dict[str, float]]:
    nn = NearestNeighbors(n_neighbors=TOP_K + 1, metric=metric)
    nn.fit(matrix)
    indices = nn.kneighbors(return_distance=False)

    global_ratios: list[float] = []
    class_ratios: dict[str, list[float]] = {label: [] for label in sorted(set(labels))}
    for idx in range(len(labels)):
        neighbor_idx = indices[idx][1:]
        ratio = float((labels[neighbor_idx] == labels[idx]).mean())
        global_ratios.append(ratio)
        class_ratios[labels[idx]].append(ratio)

    silhouette = silhouette_score(
        matrix,
        labels,
        metric=metric,
        sample_size=min(1000, len(labels)),
        random_state=SEED,
    )

    return {
        "top5_purity_mean": round(float(np.mean(global_ratios)), 4),
        "silhouette": round(float(silhouette), 4),
        "per_class_purity": {
            label: round(float(np.mean(values)), 4)
            for label, values in class_ratios.items()
        },
    }


def build_neighbor_cases(
    subset: pd.DataFrame,
    numeric: np.ndarray,
    text: np.ndarray,
    cases: list[CaseSelection],
) -> list[dict[str, object]]:
    numeric_nn = NearestNeighbors(n_neighbors=TOP_K + 1, metric="euclidean").fit(numeric)
    text_nn = NearestNeighbors(n_neighbors=TOP_K + 1, metric="cosine").fit(text)

    rows_by_id = {int(row["id"]): index for index, row in subset.reset_index(drop=True).iterrows()}
    payloads: list[dict[str, object]] = []
    for case in cases:
        if case.sample_id not in rows_by_id:
            continue
        idx = rows_by_id[case.sample_id]
        numeric_distances, numeric_indices = numeric_nn.kneighbors(numeric[idx].reshape(1, -1))
        text_distances, text_indices = text_nn.kneighbors(text[idx].reshape(1, -1))

        def serialize_neighbors(distances: np.ndarray, indices: np.ndarray, score_name: str) -> list[dict[str, object]]:
            items: list[dict[str, object]] = []
            for distance, neighbor_idx in zip(distances[0][1:], indices[0][1:], strict=False):
                row = subset.iloc[int(neighbor_idx)]
                items.append(
                    {
                        "id": int(row["id"]),
                        "canonical_fault": row["canonical_fault"],
                        "label_pt": format_fault_label_pt(row["canonical_fault"]),
                        score_name: round(float(distance), 4),
                    }
                )
            return items

        payloads.append(
            {
                "sample_id": case.sample_id,
                "title": case.title,
                "true_fault": case.true_fault,
                "predicted_fault": case.predicted_fault,
                "numeric_neighbors": serialize_neighbors(numeric_distances, numeric_indices, "distance"),
                "text_neighbors": serialize_neighbors(text_distances, text_indices, "cosine_distance"),
            }
        )
    return payloads


def write_global_plot(subset: pd.DataFrame, reduced: dict[str, np.ndarray]) -> None:
    fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=(
            "Motor matematico: PCA",
            "Embedding textual local: PCA",
            "Motor matematico: t-SNE",
            "Embedding textual local: t-SNE",
        ),
        horizontal_spacing=0.08,
        vertical_spacing=0.1,
    )

    labels = subset["canonical_fault"].tolist()
    for label in FOCUS_CLASSES:
        mask = subset["canonical_fault"] == label
        color = COLORS.get(label, "#cbd5e1")
        legend_name = format_fault_label_pt(label)
        showlegend = True
        for row, col, key in [
            (1, 1, "numeric_pca"),
            (1, 2, "text_pca"),
            (2, 1, "numeric_tsne"),
            (2, 2, "text_tsne"),
        ]:
            coords = reduced[key]
            fig.add_trace(
                go.Scattergl(
                    x=coords[mask, 0],
                    y=coords[mask, 1],
                    mode="markers",
                    marker={"size": 6, "opacity": 0.72, "color": color},
                    name=legend_name,
                    legendgroup=label,
                    showlegend=showlegend,
                    hovertemplate=(
                        "Classe: %{customdata[0]}<br>"
                        "ID: %{customdata[1]}<extra></extra>"
                    ),
                    customdata=np.column_stack(
                        [
                            subset.loc[mask, "canonical_fault"].map(format_fault_label_pt),
                            subset.loc[mask, "id"].astype(int),
                        ]
                    ),
                ),
                row=row,
                col=col,
            )
            showlegend = False

    fig.update_layout(
        title="Comparacao visual entre o espaco numerico e o espaco textual vetorizado",
        template="plotly_dark",
        height=980,
        width=1400,
        legend_title="Classe canonica",
    )
    fig.write_html(GLOBAL_HTML, include_plotlyjs="cdn")


def write_case_plot(
    subset: pd.DataFrame,
    reduced: dict[str, np.ndarray],
    neighbor_cases: list[dict[str, object]],
) -> None:
    rows = max(len(neighbor_cases), 1)
    subplot_titles: list[str] = []
    for case in neighbor_cases:
        subplot_titles.append(f"{case['title']} | Motor matematico")
        subplot_titles.append(f"{case['title']} | Embedding textual")

    fig = make_subplots(
        rows=rows,
        cols=2,
        subplot_titles=tuple(subplot_titles),
        horizontal_spacing=0.08,
        vertical_spacing=0.08,
    )

    subset_by_id = subset.set_index("id")
    for row_index, case in enumerate(neighbor_cases, start=1):
        sample_id = int(case["sample_id"])
        query_row = subset_by_id.loc[sample_id]

        for col_index, key, neighbor_key, coord_key, score_label in [
            (1, "numeric", "numeric_neighbors", "numeric_tsne", "distance"),
            (2, "text", "text_neighbors", "text_tsne", "cosine_distance"),
        ]:
            coords = reduced[coord_key]
            fig.add_trace(
                go.Scattergl(
                    x=coords[:, 0],
                    y=coords[:, 1],
                    mode="markers",
                    marker={"size": 5, "opacity": 0.14, "color": "#94a3b8"},
                    showlegend=False,
                    hoverinfo="skip",
                ),
                row=row_index,
                col=col_index,
            )

            query_idx = subset.index[subset["id"] == sample_id][0]
            query_x = float(coords[query_idx, 0])
            query_y = float(coords[query_idx, 1])

            for neighbor in case[neighbor_key]:
                neighbor_id = int(neighbor["id"])
                neighbor_idx = subset.index[subset["id"] == neighbor_id][0]
                nx = float(coords[neighbor_idx, 0])
                ny = float(coords[neighbor_idx, 1])
                nlabel = neighbor["canonical_fault"]
                fig.add_trace(
                    go.Scattergl(
                        x=[query_x, nx],
                        y=[query_y, ny],
                        mode="lines",
                        line={"color": COLORS.get(nlabel, "#f8fafc"), "width": 1.8},
                        opacity=0.7,
                        showlegend=False,
                        hoverinfo="skip",
                    ),
                    row=row_index,
                    col=col_index,
                )
                fig.add_trace(
                    go.Scattergl(
                        x=[nx],
                        y=[ny],
                        mode="markers",
                        marker={
                            "size": 11,
                            "color": COLORS.get(nlabel, "#f8fafc"),
                            "line": {"color": "#f8fafc", "width": 1},
                        },
                        name=f"Vizinho {key}",
                        showlegend=False,
                        customdata=[[format_fault_label_pt(nlabel), neighbor_id, neighbor[score_label]]],
                        hovertemplate=(
                            "Vizinho: %{customdata[0]}<br>"
                            "ID: %{customdata[1]}<br>"
                            f"{score_label}: "
                            "%{customdata[2]}<extra></extra>"
                        ),
                    ),
                    row=row_index,
                    col=col_index,
                )

            fig.add_trace(
                go.Scattergl(
                    x=[query_x],
                    y=[query_y],
                    mode="markers",
                    marker={
                        "size": 17,
                        "symbol": "star",
                        "color": COLORS.get(case["true_fault"], "#fde047"),
                        "line": {"color": "#ffffff", "width": 2},
                    },
                    name="Consulta",
                    showlegend=False,
                    customdata=[[format_fault_label_pt(case["true_fault"]), sample_id, case["predicted_fault"]]],
                    hovertemplate=(
                        "Consulta: %{customdata[0]}<br>"
                        "ID: %{customdata[1]}<br>"
                        "Predicao LLM benchmark: %{customdata[2]}<extra></extra>"
                    ),
                ),
                row=row_index,
                col=col_index,
            )

    fig.update_layout(
        title="Casos reais em que o llm_vector_rag_groq confundiu classes",
        template="plotly_dark",
        height=max(420 * rows, 520),
        width=1450,
    )
    fig.write_html(CASES_HTML, include_plotlyjs="cdn")


def write_summary(metrics: dict[str, object], neighbor_cases: list[dict[str, object]]) -> None:
    lines = [
        "# Visualizacao de Vizinhos: motor matematico vs embedding textual local",
        "",
        "Data de referencia: **6 de agosto de 2026**.",
        "",
        "## Escopo",
        "",
        f"- classes analisadas: {', '.join(FOCUS_CLASSES)};",
        f"- amostragem balanceada: `{SAMPLES_PER_CLASS}` eventos por classe;",
        "- comparacao entre o espaco numerico do motor historico e o espaco textual vetorizado usado na etapa de recuperacao por embeddings;",
        "- o foco aqui e a geometria dos vizinhos, nao a etapa generativa final do LLM.",
        "",
        "## Metricas resumidas",
        "",
        f"- pureza media dos `top-{TOP_K}` vizinhos no espaco numerico: `{metrics['numeric']['top5_purity_mean']}`",
        f"- pureza media dos `top-{TOP_K}` vizinhos no espaco textual: `{metrics['text']['top5_purity_mean']}`",
        f"- silhouette no espaco numerico: `{metrics['numeric']['silhouette']}`",
        f"- silhouette no espaco textual: `{metrics['text']['silhouette']}`",
        "",
        "Leitura curta:",
        "",
        "- o espaco textual ficou mais misturado do que o espaco numerico no recorte das classes mais frageis;",
        "- isso nao significa que o LLM seja inutil, mas indica que a etapa de textualizacao + embedding local perde separacao diagnostica importante;",
        "- o resultado conversa com a literatura e com a intuicao de dominio: features de vibracao ja resumidas para texto tendem a preservar menos estrutura discriminativa do que o vetor numerico original.",
        "",
        "## Artefatos gerados",
        "",
        f"- `{GLOBAL_HTML.as_posix()}`",
        f"- `{CASES_HTML.as_posix()}`",
        f"- `{METRICS_JSON.as_posix()}`",
        f"- `{NEIGHBORS_JSON.as_posix()}`",
        "",
        "## Casos destacados",
        "",
    ]

    for case in neighbor_cases:
        lines.extend(
            [
                f"### {case['title']}",
                "",
                f"- sample_id: `{case['sample_id']}`",
                f"- classe real: `{case['true_fault']}`",
                f"- classe prevista pelo `llm_vector_rag_groq`: `{case['predicted_fault']}`",
                f"- vizinhos numericos: {', '.join(item['canonical_fault'] for item in case['numeric_neighbors'])}",
                f"- vizinhos textuais: {', '.join(item['canonical_fault'] for item in case['text_neighbors'])}",
                "",
            ]
        )

    SUMMARY_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    subset = load_balanced_subset()
    cases, subset = select_cases(subset)

    numeric, text = build_spaces(subset)
    reduced = reduce_spaces(numeric, text)

    labels = subset["canonical_fault"].to_numpy()
    metrics = {
        "numeric": neighbor_metrics(numeric, labels, metric="euclidean"),
        "text": neighbor_metrics(text, labels, metric="cosine"),
    }
    neighbor_cases = build_neighbor_cases(subset, numeric, text, cases)

    write_global_plot(subset, reduced)
    write_case_plot(subset, reduced, neighbor_cases)
    write_summary(metrics, neighbor_cases)

    METRICS_JSON.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    NEIGHBORS_JSON.write_text(json.dumps(neighbor_cases, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[ok] {GLOBAL_HTML}")
    print(f"[ok] {CASES_HTML}")
    print(f"[ok] {SUMMARY_MD}")
    print(f"[ok] {METRICS_JSON}")
    print(f"[ok] {NEIGHBORS_JSON}")


if __name__ == "__main__":
    main()
