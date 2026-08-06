from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agent_service import AGENT
from src.document_service import DOCUMENT_SERVICE, DocumentSearchResult
from src.history_service import HISTORY_SERVICE


FREEFORM_CASES = [
    {
        "name": "document_query_base",
        "prompt": "Quais documentos existem na base e que tipo de falha cada um cobre?",
        "expect_any": ["base documental", "documento"],
    },
    {
        "name": "concept_desbalanceamento_vs_desalinhamento",
        "prompt": "Explique a diferenca entre desbalanceamento e desalinhamento em maquinas rotativas.",
        "expect_any": ["desbalanceamento", "desalinhamento"],
    },
    {
        "name": "concept_fft",
        "prompt": "O que e FFT e por que ela e importante em manutencao preditiva?",
        "expect_any": ["fft", "nao calcula fft"],
    },
    {
        "name": "limit_fft_pipeline",
        "prompt": "O projeto calcula FFT diretamente no pipeline atual?",
        "expect_any": ["nao calcula fft"],
    },
    {
        "name": "new_fault_without_history",
        "prompt": "Tenho um documento novo sobre cavitacao. O que o sistema consegue fazer se nao houver historico dessa falha?",
        "expect_any": ["historico", "documento", "limitacao"],
    },
    {
        "name": "architecture_llm_role",
        "prompt": "O LLM faz a inferencia numerica principal ou so orquestra e sintetiza?",
        "expect_all": ["llm", "orquestra"],
        "forbid_any": ["faz a inferencia numerica principal"],
    },
    {
        "name": "mongo_role",
        "prompt": "Hoje o MongoDB esta sendo usado como persistencia ou como motor vetorial nativo?",
        "expect_all": ["persist", "vetorial"],
        "forbid_any": ["nao esta sendo usado como persistencia ou como motor vetorial nativo"],
    },
]


EVENT_CASES = [
    {
        "name": "known_fault_event",
        "event": {
            "temperature_c": 24.7,
            "rpm": 1000,
            "x_rms_velocity_mm_s": 2.0,
            "z_rms_velocity_mm_s": 1.517,
            "x_peak_acceleration_g": 0.631,
            "z_peak_acceleration_g": 0.484,
            "x_rms_acceleration_g": 0.114,
            "z_rms_acceleration_g": 0.09,
            "x_kurtosis": 2.77,
            "z_kurtosis": 2.392,
            "x_crest_factor": 4.269,
            "z_crest_factor": 3.747,
        },
    },
    {
        "name": "operational_state_event",
        "event": {
            "temperature_c": 23.5,
            "rpm": 0,
            "x_rms_velocity_mm_s": 0.05,
            "z_rms_velocity_mm_s": 0.04,
            "x_peak_acceleration_g": 0.02,
            "z_peak_acceleration_g": 0.02,
            "x_rms_acceleration_g": 0.01,
            "z_rms_acceleration_g": 0.01,
            "x_kurtosis": 2.1,
            "z_kurtosis": 2.0,
            "x_crest_factor": 1.8,
            "z_crest_factor": 1.7,
            "fault": "motor parado",
        },
        "expected_label": "motor_desligado",
        "forbid_docs": True,
    },
    {
        "name": "invalid_event",
        "event": {
            "temperature_c": 500,
            "rpm": -10,
            "x_rms_velocity_mm_s": -1,
            "z_rms_velocity_mm_s": -2,
        },
        "expected_label": "evento_invalido",
        "forbid_docs": True,
    },
]


NO_DOC_CASES = [
    {
        "name": "no_docs_known_fault_event",
        "event": {
            "temperature_c": 24.7,
            "rpm": 1000,
            "x_rms_velocity_mm_s": 2.0,
            "z_rms_velocity_mm_s": 1.517,
            "x_peak_acceleration_g": 0.631,
            "z_peak_acceleration_g": 0.484,
            "x_rms_acceleration_g": 0.114,
            "z_rms_acceleration_g": 0.09,
            "x_kurtosis": 2.77,
            "z_kurtosis": 2.392,
            "x_crest_factor": 4.269,
            "z_crest_factor": 3.747,
        },
    },
    {
        "name": "no_docs_document_query",
        "prompt": "Quais documentos existem na base e que tipo de falha cada um cobre?",
        "expect_any": ["nao encontrei documentos indexados", "sem documentos indexados"],
    },
]


def _contains_any(text: str, fragments: list[str]) -> bool:
    lowered = text.lower()
    return any(fragment.lower() in lowered for fragment in fragments)


def _contains_all(text: str, fragments: list[str]) -> bool:
    lowered = text.lower()
    return all(fragment.lower() in lowered for fragment in fragments)


@contextmanager
def llm_disabled():
    provider = AGENT._provider
    groq_client = AGENT._groq_client
    AGENT._provider = "disabled"
    AGENT._groq_client = None
    try:
        yield
    finally:
        AGENT._provider = provider
        AGENT._groq_client = groq_client


@contextmanager
def empty_document_base():
    original_list_documents = DOCUMENT_SERVICE.list_documents
    original_list_chunks = DOCUMENT_SERVICE.list_chunks
    original_search_chunks = DOCUMENT_SERVICE.search_chunks

    def _empty_docs():
        return []

    def _empty_chunks():
        return []

    def _empty_search(query_text: str, fault_family: str | None = None, top_k: int | None = None):
        return DocumentSearchResult(chunks=[], summary="Nenhum chunk indexado.")

    DOCUMENT_SERVICE.list_documents = _empty_docs
    DOCUMENT_SERVICE.list_chunks = _empty_chunks
    DOCUMENT_SERVICE.search_chunks = _empty_search
    try:
        yield
    finally:
        DOCUMENT_SERVICE.list_documents = original_list_documents
        DOCUMENT_SERVICE.list_chunks = original_list_chunks
        DOCUMENT_SERVICE.search_chunks = original_search_chunks


def run_freeform_cases() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for case in FREEFORM_CASES:
        result = AGENT.infer_event(case["prompt"], model_name=AGENT.available_models()[0])
        markdown = result["agent_response"].get("response_markdown", "")
        ok = True

        if case.get("expect_any"):
            ok = ok and _contains_any(markdown, case["expect_any"])
        if case.get("expect_all"):
            ok = ok and _contains_all(markdown, case["expect_all"])
        if case.get("forbid_any"):
            ok = ok and not _contains_any(markdown, case["forbid_any"])

        rows.append(
            {
                "kind": "freeform",
                "name": case["name"],
                "status": "PASS" if ok else "FAIL",
                "observed": markdown[:260].replace("\n", " "),
            }
        )
    return rows


def run_event_cases() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with llm_disabled():
        for case in EVENT_CASES:
            result = AGENT.infer_event(case["event"], model_name=AGENT.available_models()[0])
            response = result["agent_response"]
            observed_label = str(response.get("probable_fault"))
            cited_documents = response.get("cited_documents") or []
            expected_label = case.get("expected_label")

            ok = observed_label == expected_label if expected_label else bool(observed_label)
            if case.get("forbid_docs"):
                ok = ok and not cited_documents

            rows.append(
                {
                    "kind": "event",
                    "name": case["name"],
                    "status": "PASS" if ok else "FAIL",
                    "observed": json.dumps(
                        {
                            "probable_fault": observed_label,
                            "cited_documents": cited_documents,
                        },
                        ensure_ascii=False,
                    ),
                }
            )
    return rows


def run_label_bias_cases() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    df = HISTORY_SERVICE.load_dataset()
    target_families = ["desbalanceamento", "desalinhamento", "rolamento_inner"]

    with llm_disabled():
        for family in target_families:
            sample_rows = df[df["canonical_fault"] == family].head(1).to_dict(orient="records")
            if not sample_rows:
                rows.append({"kind": "bias", "name": f"{family}_missing_sample", "status": "SKIP", "observed": "sem amostra"})
                continue

            base_event = {
                key: sample_rows[0].get(key)
                for key in [
                    "temperature_c",
                    "rpm",
                    "x_rms_velocity_mm_s",
                    "z_rms_velocity_mm_s",
                    "x_peak_acceleration_g",
                    "z_peak_acceleration_g",
                    "x_rms_acceleration_g",
                    "z_rms_acceleration_g",
                    "x_kurtosis",
                    "z_kurtosis",
                    "x_crest_factor",
                    "z_crest_factor",
                ]
            }

            variants = {
                "sem_rotulo": dict(base_event),
                "rotulo_normal": {**base_event, "fault": "normal"},
                "rotulo_motor_parado": {**base_event, "fault": "motor parado"},
                "rotulo_errado": {**base_event, "fault": "correia" if family != "correia" else "desbalanceamento"},
            }

            predictions: dict[str, str] = {}
            for variant_name, payload in variants.items():
                result = AGENT.infer_event(payload, model_name=AGENT.available_models()[0])
                predictions[variant_name] = str(result["agent_response"].get("probable_fault"))

            stable = len(set(predictions.values())) == 1
            rows.append(
                {
                    "kind": "bias",
                    "name": f"{family}_label_bias",
                    "status": "PASS" if stable else "FAIL",
                    "observed": json.dumps(predictions, ensure_ascii=False),
                }
            )
    return rows


def run_no_doc_cases() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with empty_document_base(), llm_disabled():
        for case in NO_DOC_CASES:
            if "event" in case:
                result = AGENT.infer_event(case["event"], model_name=AGENT.available_models()[0])
                response = result["agent_response"]
                cited_documents = response.get("cited_documents") or []
                refusal_reason = str(response.get("refusal_reason", ""))
                ok = (not cited_documents) and ("document" in refusal_reason.lower() or "lastro" in refusal_reason.lower())
                rows.append(
                    {
                        "kind": "no_doc",
                        "name": case["name"],
                        "status": "PASS" if ok else "FAIL",
                        "observed": json.dumps(
                            {
                                "probable_fault": response.get("probable_fault"),
                                "cited_documents": cited_documents,
                                "refusal_reason": refusal_reason,
                            },
                            ensure_ascii=False,
                        ),
                    }
                )
            else:
                result = AGENT.infer_event(case["prompt"], model_name=AGENT.available_models()[0])
                markdown = result["agent_response"].get("response_markdown", "")
                ok = _contains_any(markdown, case["expect_any"])
                rows.append(
                    {
                        "kind": "no_doc",
                        "name": case["name"],
                        "status": "PASS" if ok else "FAIL",
                        "observed": markdown[:260].replace("\n", " "),
                    }
                )
    return rows


def main() -> None:
    all_rows = [*run_freeform_cases(), *run_event_cases(), *run_no_doc_cases(), *run_label_bias_cases()]
    print(json.dumps(all_rows, ensure_ascii=False, indent=2))

    failed = [row for row in all_rows if row["status"] == "FAIL"]
    if failed:
        print(f"\nFalhas detectadas: {len(failed)}")
        raise SystemExit(1)

    print(f"\nSuite concluida com sucesso: {len(all_rows)} verificacoes.")


if __name__ == "__main__":
    main()
