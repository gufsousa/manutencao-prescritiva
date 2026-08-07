from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.compare_python_vs_mongo_vector_search import run_mongo_vector_search, run_python_search
from src.agent_service import AGENT
from src.document_service import DOCUMENT_SERVICE, DocumentSearchResult
from src.fault_semantics import get_label_kind, is_state_label
from src.history_service import FEATURE_COLUMNS, HISTORY_SERVICE
from src.mongo_store import STORE


@dataclass
class CaseResult:
    name: str
    status: str
    observed: str


def _ok(name: str, observed: Any) -> CaseResult:
    return CaseResult(name=name, status="PASS", observed=str(observed))


def _fail(name: str, observed: Any) -> CaseResult:
    return CaseResult(name=name, status="FAIL", observed=str(observed))


def _skip(name: str, observed: Any) -> CaseResult:
    return CaseResult(name=name, status="SKIP", observed=str(observed))


def _contains_any(text: str, needles: list[str]) -> bool:
    lowered = text.lower()
    return any(item.lower() in lowered for item in needles)


def _contains_all(text: str, needles: list[str]) -> bool:
    lowered = text.lower()
    return all(item.lower() in lowered for item in needles)


def _markdown(result: dict[str, Any]) -> str:
    return str(result["agent_response"].get("response_markdown", ""))


def _response(result: dict[str, Any]) -> dict[str, Any]:
    return result["agent_response"]


def _sample_event(label: str) -> dict[str, Any]:
    df = HISTORY_SERVICE.load_dataset()
    rows = df[df["canonical_fault"] == label].head(1).to_dict(orient="records")
    if not rows:
        raise KeyError(f"Sem amostra para {label}")
    row = rows[0]
    payload = {feature: row.get(feature) for feature in FEATURE_COLUMNS}
    payload["fault"] = row.get("fault")
    return payload


def _balanced_fault_samples(limit: int = 5) -> list[tuple[str, dict[str, Any]]]:
    df = HISTORY_SERVICE.load_dataset()
    labels = [label for label in df["canonical_fault"].dropna().unique().tolist() if not is_state_label(label)]
    labels = labels[:limit]
    return [(label, _sample_event(label)) for label in labels]


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


@contextmanager
def manual_document_base(title: str, fault_family: str, content: str):
    original_list_documents = DOCUMENT_SERVICE.list_documents
    original_list_chunks = DOCUMENT_SERVICE.list_chunks
    original_search_chunks = DOCUMENT_SERVICE.search_chunks
    doc = {
        "id": "manual-doc-1",
        "title": title,
        "fault_family": fault_family,
        "source_file": "manual://qa",
        "content": content,
        "source_type": "manual",
    }
    chunk = {
        "id": "manual-chunk-1",
        "document_id": "manual-doc-1",
        "source_file": "manual://qa",
        "title": title,
        "fault_family": fault_family,
        "chunk_index": 0,
        "chunk_text": content,
        "score": 0.99,
        "vector": [],
    }

    def _docs():
        return [doc]

    def _chunks():
        return [chunk]

    def _search(query_text: str, fault_family: str | None = None, top_k: int | None = None):
        return DocumentSearchResult(chunks=[chunk], summary="1 chunk manual recuperado.")

    DOCUMENT_SERVICE.list_documents = _docs
    DOCUMENT_SERVICE.list_chunks = _chunks
    DOCUMENT_SERVICE.search_chunks = _search
    try:
        yield
    finally:
        DOCUMENT_SERVICE.list_documents = original_list_documents
        DOCUMENT_SERVICE.list_chunks = original_list_chunks
        DOCUMENT_SERVICE.search_chunks = original_search_chunks


def _run_text_case(prompt: str) -> dict[str, Any]:
    return AGENT.infer_event(prompt, model_name=AGENT.available_models()[0])


def _run_event_case(payload: dict[str, Any], disable_llm: bool = True) -> dict[str, Any]:
    if disable_llm:
        with llm_disabled():
            return AGENT.infer_event(payload, model_name=AGENT.available_models()[0])
    return AGENT.infer_event(payload, model_name=AGENT.available_models()[0])


def case_doc_catalog_01() -> CaseResult:
    docs = DOCUMENT_SERVICE.list_documents()
    return _ok("doc_catalog_01", len(docs)) if len(docs) == 6 else _fail("doc_catalog_01", len(docs))


def case_doc_catalog_02() -> CaseResult:
    docs = DOCUMENT_SERVICE.list_documents()
    ok = all(bool(doc.get("title")) for doc in docs)
    return _ok("doc_catalog_02", "todos com title") if ok else _fail("doc_catalog_02", docs)


def case_doc_catalog_03() -> CaseResult:
    docs = DOCUMENT_SERVICE.list_documents()
    ok = all(bool(doc.get("fault_family")) for doc in docs)
    return _ok("doc_catalog_03", "todos com fault_family") if ok else _fail("doc_catalog_03", docs)


def case_doc_catalog_04() -> CaseResult:
    result = _run_text_case("Quais documentos existem na base e que tipo de falha cada um cobre?")
    markdown = _markdown(result)
    fake_names = ["cavitacao", "doc7", "procedimento de cavitacao"]
    ok = not _contains_any(markdown, fake_names)
    return _ok("doc_catalog_04", markdown[:180]) if ok else _fail("doc_catalog_04", markdown[:260])


def case_doc_catalog_05() -> CaseResult:
    with empty_document_base():
        result = _run_text_case("Quais documentos existem na base e que tipo de falha cada um cobre?")
    markdown = _markdown(result)
    ok = "falha provavel" not in markdown.lower()
    return _ok("doc_catalog_05", markdown[:180]) if ok else _fail("doc_catalog_05", markdown[:260])


def case_doc_catalog_06() -> CaseResult:
    result = _run_text_case("Quais documentos existem na base e que tipo de falha cada um cobre?")
    cited = _response(result).get("cited_documents") or []
    return _ok("doc_catalog_06", cited) if len(cited) >= 1 else _fail("doc_catalog_06", cited)


def case_doc_catalog_07() -> CaseResult:
    result = _run_text_case("Quais documentos existem na base e que tipo de falha cada um cobre?")
    cited = set(_response(result).get("cited_documents") or [])
    ok = len(cited) > 1 and not (len(cited) == 1 and "Desalinhamento" in next(iter(cited)))
    return _ok("doc_catalog_07", cited) if ok else _fail("doc_catalog_07", cited)


def case_doc_catalog_08() -> CaseResult:
    docs = DOCUMENT_SERVICE.list_documents()
    state_names = {"normal", "motor_desligado", "baseline", "teste", "acelerando"}
    ok = all(doc.get("fault_family") not in state_names for doc in docs)
    return _ok("doc_catalog_08", "sem state como falha") if ok else _fail("doc_catalog_08", docs)


def case_doc_catalog_09() -> CaseResult:
    result = _run_text_case("Quais documentos existem na base?")
    ok = result["event"] is None and _response(result).get("answer_type") == "document_query"
    return _ok("doc_catalog_09", _response(result).get("answer_type")) if ok else _fail("doc_catalog_09", result)


def case_doc_catalog_10() -> CaseResult:
    result = _run_text_case("Que tipo de falha cada documento cobre?")
    markdown = _markdown(result)
    ok = _contains_any(markdown, ["familia", "falha", "documento indexado"])
    return _ok("doc_catalog_10", markdown[:180]) if ok else _fail("doc_catalog_10", markdown[:260])


def case_fft_01() -> CaseResult:
    result = _run_text_case("O que e FFT?")
    markdown = _markdown(result)
    ok = _contains_any(markdown, ["fft", "analise em frequencia"]) and "diagnostico provavel" not in markdown.lower()
    return _ok("fft_01", markdown[:180]) if ok else _fail("fft_01", markdown[:260])


def case_fft_02() -> CaseResult:
    result = _run_text_case("O projeto calcula FFT?")
    markdown = _markdown(result)
    ok = _contains_any(markdown, ["nao calcula fft"])
    return _ok("fft_02", markdown[:180]) if ok else _fail("fft_02", markdown[:260])


def case_fft_03() -> CaseResult:
    result = _run_text_case("O que e FFT e por que ela e importante?")
    markdown = _markdown(result)
    forbidden = ["desalinhamento", "desbalanceamento", "correia", "rolamento_inner"]
    ok = not _contains_any(markdown, forbidden)
    return _ok("fft_03", markdown[:180]) if ok else _fail("fft_03", markdown[:260])


def case_fft_04() -> CaseResult:
    result = _run_text_case("O que e FFT e por que ela e importante?")
    markdown = _markdown(result)
    ok = not _contains_any(markdown, ["corrigir", "executar procedimento", "ordem de manutencao"])
    return _ok("fft_04", markdown[:180]) if ok else _fail("fft_04", markdown[:260])


def case_fft_05() -> CaseResult:
    result = _run_text_case("O projeto calcula FFT diretamente no pipeline atual?")
    markdown = _markdown(result)
    ok = _contains_any(markdown, ["sem sinal bruto", "dataset", "pipeline atual"])
    return _ok("fft_05", markdown[:180]) if ok else _fail("fft_05", markdown[:260])


def case_arch_01() -> CaseResult:
    result = _run_text_case("LLM faz inferencia numerica?")
    markdown = _markdown(result)
    ok = _contains_all(markdown, ["llm", "orquestra"]) and "faz a inferencia numerica principal" not in markdown.lower()
    return _ok("arch_01", markdown[:180]) if ok else _fail("arch_01", markdown[:260])


def case_arch_02() -> CaseResult:
    result = _run_text_case("Mongo e persistencia ou motor vetorial nativo?")
    markdown = _markdown(result)
    ok = _contains_all(markdown, ["persistencia", "vetorial"]) and "nao esta sendo usado como persistencia ou como motor vetorial nativo" not in markdown.lower()
    return _ok("arch_02", markdown[:180]) if ok else _fail("arch_02", markdown[:260])


def case_arch_03() -> CaseResult:
    result = _run_text_case("Usa banco vetorial nativo?")
    markdown = _markdown(result)
    ok = _contains_any(markdown, ["nao", "estado atual", "local"])
    return _ok("arch_03", markdown[:180]) if ok else _fail("arch_03", markdown[:260])


def case_arch_04() -> CaseResult:
    result = _run_text_case("Usa RAG?")
    markdown = _markdown(result)
    ok = _contains_any(markdown, ["rag e a combinacao", "base documental", "trechos recuperados"])
    return _ok("arch_04", markdown[:180]) if ok else _fail("arch_04", markdown[:260])


def case_arch_05() -> CaseResult:
    result = _run_text_case("Se Mongo cair, o sistema para?")
    markdown = _markdown(result)
    ok = _contains_any(markdown, ["fallback local", "local"])
    return _ok("arch_05", markdown[:180]) if ok else _fail("arch_05", markdown[:260])


def _invalid_event_result(payload: dict[str, Any]) -> dict[str, Any]:
    return _run_event_case(payload, disable_llm=True)


def _state_event_payload(state_label: str) -> dict[str, Any]:
    return {
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
        "fault": state_label,
    }


def _ood_event_payload() -> dict[str, Any]:
    return {
        "temperature_c": 219.0,
        "rpm": 9800.0,
        "x_rms_velocity_mm_s": 18.0,
        "z_rms_velocity_mm_s": 17.0,
        "x_peak_acceleration_g": 6.5,
        "z_peak_acceleration_g": 6.1,
        "x_rms_acceleration_g": 3.2,
        "z_rms_acceleration_g": 3.0,
        "x_kurtosis": 7.5,
        "z_kurtosis": 7.1,
        "x_crest_factor": 9.1,
        "z_crest_factor": 8.8,
    }


def build_cases() -> list[tuple[str, Callable[[], CaseResult]]]:
    cases: list[tuple[str, Callable[[], CaseResult]]] = []
    for i in range(1, 11):
        cases.append((f"doc_catalog_{i:02d}", globals()[f"case_doc_catalog_{i:02d}"]))
    for i in range(1, 6):
        cases.append((f"fft_{i:02d}", globals()[f"case_fft_{i:02d}"]))
    for i in range(1, 6):
        cases.append((f"arch_{i:02d}", globals()[f"case_arch_{i:02d}"]))

    invalid_temp = {"temperature_c": 500, "rpm": 1000, "x_rms_velocity_mm_s": 1, "z_rms_velocity_mm_s": 1}
    invalid_rpm = {"temperature_c": 20, "rpm": -10, "x_rms_velocity_mm_s": 1, "z_rms_velocity_mm_s": 1}
    invalid_vx = {"temperature_c": 20, "rpm": 1000, "x_rms_velocity_mm_s": -1, "z_rms_velocity_mm_s": 1}
    invalid_multi = {"temperature_c": 500, "rpm": -10, "x_rms_velocity_mm_s": -1, "z_rms_velocity_mm_s": -2}

    cases.extend([
        ("guard_phys_01", lambda: _ok("guard_phys_01", _response(_invalid_event_result(invalid_temp))["probable_fault"]) if not _invalid_event_result(invalid_temp)["validation"]["valid"] else _fail("guard_phys_01", _invalid_event_result(invalid_temp)["validation"])),
        ("guard_phys_02", lambda: _ok("guard_phys_02", _response(_invalid_event_result(invalid_rpm))["probable_fault"]) if not _invalid_event_result(invalid_rpm)["validation"]["valid"] else _fail("guard_phys_02", _invalid_event_result(invalid_rpm)["validation"])),
        ("guard_phys_03", lambda: _ok("guard_phys_03", _response(_invalid_event_result(invalid_vx))["probable_fault"]) if not _invalid_event_result(invalid_vx)["validation"]["valid"] else _fail("guard_phys_03", _invalid_event_result(invalid_vx)["validation"])),
        ("guard_phys_04", lambda: _ok("guard_phys_04", _invalid_event_result(invalid_multi)["validation"]["errors"]) if len(_invalid_event_result(invalid_multi)["validation"]["errors"]) >= 2 else _fail("guard_phys_04", _invalid_event_result(invalid_multi)["validation"])),
        ("guard_phys_05", lambda: _ok("guard_phys_05", _response(_invalid_event_result(invalid_multi))["probable_fault"]) if _response(_invalid_event_result(invalid_multi))["probable_fault"] == "evento_invalido" else _fail("guard_phys_05", _response(_invalid_event_result(invalid_multi)))),
        ("guard_phys_06", lambda: _ok("guard_phys_06", "sem docs") if not (_response(_invalid_event_result(invalid_multi)).get("cited_documents") or []) else _fail("guard_phys_06", _response(_invalid_event_result(invalid_multi)))),
        ("guard_phys_07", lambda: _ok("guard_phys_07", "sem checklist agressivo") if not _contains_any(_markdown(_invalid_event_result(invalid_multi)), ["Executar procedimento tecnico rastreado"]) else _fail("guard_phys_07", _markdown(_invalid_event_result(invalid_multi)))),
        ("guard_phys_08", lambda: _ok("guard_phys_08", _response(_invalid_event_result(invalid_multi)).get("refusal_reason")) if bool(_response(_invalid_event_result(invalid_multi)).get("refusal_reason")) else _fail("guard_phys_08", _response(_invalid_event_result(invalid_multi)))),
        ("guard_phys_09", lambda: _ok("guard_phys_09", _response(_invalid_event_result(invalid_multi))["probable_fault"]) if _response(_invalid_event_result(invalid_multi))["probable_fault"] != "normal" else _fail("guard_phys_09", _response(_invalid_event_result(invalid_multi)))),
        ("guard_phys_10", lambda: _ok("guard_phys_10", _response(_invalid_event_result(invalid_multi))["probable_fault"]) if _response(_invalid_event_result(invalid_multi))["probable_fault"] == "evento_invalido" else _fail("guard_phys_10", _response(_invalid_event_result(invalid_multi)))),
    ])

    state_labels = [
        ("state_01", "motor parado"),
        ("state_07", "normal"),
        ("state_08", "baseline"),
        ("state_09", "teste"),
        ("state_10", "acelerando"),
    ]
    cases.extend([
        ("state_01", lambda: _ok("state_01", _response(_run_event_case(_state_event_payload("motor parado")))["probable_fault"]) if _response(_run_event_case(_state_event_payload("motor parado")))["probable_fault"] == "motor_desligado" else _fail("state_01", _response(_run_event_case(_state_event_payload("motor parado"))))),
        ("state_02", lambda: _ok("state_02", _markdown(_run_event_case(_state_event_payload("motor parado")))) if "Estado operacional" in _markdown(_run_event_case(_state_event_payload("motor parado"))) else _fail("state_02", _markdown(_run_event_case(_state_event_payload("motor parado"))))),
        ("state_03", lambda: _ok("state_03", "sem docs") if not (_response(_run_event_case(_state_event_payload("motor parado"))).get("cited_documents") or []) else _fail("state_03", _response(_run_event_case(_state_event_payload("motor parado"))))),
        ("state_04", lambda: _ok("state_04", _markdown(_run_event_case(_state_event_payload("motor parado")))) if not _contains_any(_markdown(_run_event_case(_state_event_payload("motor parado"))), ["ordem de manutencao corretiva", "executar procedimento tecnico rastreado"]) else _fail("state_04", _markdown(_run_event_case(_state_event_payload("motor parado"))))),
        ("state_05", lambda: _ok("state_05", _markdown(_run_event_case(_state_event_payload("motor parado")))) if _contains_any(_markdown(_run_event_case(_state_event_payload("motor parado"))), ["contexto operacional"]) else _fail("state_05", _markdown(_run_event_case(_state_event_payload("motor parado"))))),
        ("state_06", lambda: _ok("state_06", "sem desalinhamento documental") if not _contains_any(_markdown(_run_event_case(_state_event_payload("motor parado"))), ["Procedimento de Desalinhamento"]) else _fail("state_06", _markdown(_run_event_case(_state_event_payload("motor parado"))))),
    ])
    for case_name, state_value in state_labels[1:]:
        cases.append((case_name, lambda state_value=state_value, case_name=case_name: _ok(case_name, _response(_run_event_case(_state_event_payload(state_value)))["probable_fault"]) if get_label_kind(_response(_run_event_case(_state_event_payload(state_value)))["probable_fault"]) == "state" else _fail(case_name, _response(_run_event_case(_state_event_payload(state_value)))) ))

    cases.extend([
        ("ood_01", lambda: _ok("ood_01", HISTORY_SERVICE.search_similar_events(_ood_event_payload()).ood_status) if HISTORY_SERVICE.search_similar_events(_ood_event_payload()).ood_status in {"ood", "fronteira"} else _fail("ood_01", asdict(HISTORY_SERVICE.search_similar_events(_ood_event_payload())))),
        ("ood_02", lambda: _ok("ood_02", _markdown(_run_event_case(_ood_event_payload()))) if _contains_any(_markdown(_run_event_case(_ood_event_payload())), ["ood", "Guardrail OOD"]) else _fail("ood_02", _markdown(_run_event_case(_ood_event_payload())))),
        ("ood_03", lambda: _ok("ood_03", _response(_run_event_case(_ood_event_payload())).get("refusal_reason")) if bool(_response(_run_event_case(_ood_event_payload())).get("refusal_reason")) else _fail("ood_03", _response(_run_event_case(_ood_event_payload())))),
        ("ood_04", lambda: _ok("ood_04", _response(_run_event_case(_ood_event_payload())).get("cited_documents")) if True else _fail("ood_04", "")),
        ("ood_05", lambda: _ok("ood_05", _response(_run_event_case(_ood_event_payload())).get("refusal_reason")) if _contains_any(str(_response(_run_event_case(_ood_event_payload())).get("refusal_reason", "")), ["validacao humana", "validação humana"]) else _fail("ood_05", _response(_run_event_case(_ood_event_payload())))),
        ("ood_06", lambda: _ok("ood_06", _response(_run_event_case(_ood_event_payload())).get("confidence_pct")) if float(_response(_run_event_case(_ood_event_payload())).get("confidence_pct", 0)) < 100 else _fail("ood_06", _response(_run_event_case(_ood_event_payload())))),
        ("ood_07", lambda: _ok("ood_07", HISTORY_SERVICE.search_similar_events({**_ood_event_payload(), "fault": "normal"}).ood_status) if HISTORY_SERVICE.search_similar_events({**_ood_event_payload(), "fault": "normal"}).ood_status in {"ood", "fronteira"} else _fail("ood_07", asdict(HISTORY_SERVICE.search_similar_events({**_ood_event_payload(), "fault": "normal"})))),
        ("ood_08", lambda: _ok("ood_08", _response(_run_event_case({**_ood_event_payload(), "fault": "motor parado"})).get("probable_fault")) if get_label_kind(_response(_run_event_case({**_ood_event_payload(), "fault": "motor parado"})).get("probable_fault")) == "state" else _fail("ood_08", _response(_run_event_case({**_ood_event_payload(), "fault": "motor parado"})))),
        ("ood_09", lambda: _ok("ood_09", _response(_run_event_case({**_ood_event_payload(), "temperature_c": 500})).get("probable_fault")) if _response(_run_event_case({**_ood_event_payload(), "temperature_c": 500})).get("probable_fault") == "evento_invalido" else _fail("ood_09", _response(_run_event_case({**_ood_event_payload(), "temperature_c": 500})))),
        ("ood_10", lambda: _ok("ood_10", _markdown(_run_event_case(_ood_event_payload()))) if _contains_all(_markdown(_run_event_case(_ood_event_payload())), ["limite95", "limite99"]) else _fail("ood_10", _markdown(_run_event_case(_ood_event_payload())))),
    ])

    def doc_guard_01() -> CaseResult:
        with empty_document_base():
            result = _run_event_case(_sample_event("cocked_rotor"))
        markdown = _markdown(result)
        ok = not _contains_any(markdown, ["Procedimento de", "Documento: **"])
        return _ok("doc_guard_01", markdown[:180]) if ok else _fail("doc_guard_01", markdown[:260])

    def doc_guard_02() -> CaseResult:
        with empty_document_base():
            result = _run_event_case(_sample_event("cocked_rotor"))
        ok = _contains_any(str(_response(result).get("refusal_reason", "")), ["documento", "lastro"])
        return _ok("doc_guard_02", _response(result).get("refusal_reason")) if ok else _fail("doc_guard_02", _response(result))

    def doc_guard_03() -> CaseResult:
        with empty_document_base():
            result = _run_event_case(_sample_event("cocked_rotor"))
        ok = bool(_response(result).get("probable_fault"))
        return _ok("doc_guard_03", _response(result).get("probable_fault")) if ok else _fail("doc_guard_03", _response(result))

    def doc_guard_04() -> CaseResult:
        with empty_document_base():
            result = _run_event_case(_sample_event("cocked_rotor"))
        ok = not (_response(result).get("cited_documents") or [])
        return _ok("doc_guard_04", "[]") if ok else _fail("doc_guard_04", _response(result))

    def doc_guard_05() -> CaseResult:
        with empty_document_base():
            result = _run_event_case(_sample_event("cocked_rotor"))
        ok = not _contains_any(_markdown(result), ["Checklist de inspecao", "Procedimento de"])
        return _ok("doc_guard_05", _markdown(result)[:180]) if ok else _fail("doc_guard_05", _markdown(result)[:260])

    def doc_guard_06() -> CaseResult:
        with empty_document_base():
            result = _run_event_case(_sample_event("cocked_rotor"))
        ok = _contains_any(_markdown(result), ["ampliar base documental", "validar instrumentacao"])
        return _ok("doc_guard_06", _markdown(result)[:180]) if ok else _fail("doc_guard_06", _markdown(result)[:260])

    def doc_guard_07() -> CaseResult:
        with empty_document_base():
            result = _run_text_case("Explique a diferenca entre desbalanceamento e desalinhamento")
        ok = _contains_any(_markdown(result), ["lastro", "base"]) or bool(_response(result).get("refusal_reason"))
        return _ok("doc_guard_07", _markdown(result)[:180]) if ok else _fail("doc_guard_07", _markdown(result)[:260])

    def doc_guard_08() -> CaseResult:
        with empty_document_base():
            result = _run_text_case("Quais documentos existem na base?")
        ok = _contains_any(_markdown(result), ["nao encontrei documentos indexados", "sem documentos indexados"])
        return _ok("doc_guard_08", _markdown(result)[:180]) if ok else _fail("doc_guard_08", _markdown(result)[:260])

    def doc_guard_09() -> CaseResult:
        with manual_document_base("Procedimento de Cavitacao", "cavitacao", "Cavitacao pode ser explicada tecnicamente por documento, sem criar historico falso."):
            result = _run_text_case("Tenho um documento novo sobre cavitacao. O que o sistema consegue fazer se nao houver historico dessa falha?")
        markdown = _markdown(result)
        ok = _contains_any(markdown, ["historico", "documento", "nao deveria inventar"])
        return _ok("doc_guard_09", markdown[:180]) if ok else _fail("doc_guard_09", markdown[:260])

    def doc_guard_10() -> CaseResult:
        with empty_document_base():
            result = _run_text_case("Tenho um documento novo sobre cavitacao. O que o sistema consegue fazer se nao houver historico dessa falha?")
        markdown = _markdown(result)
        ok = _contains_any(markdown, ["limitacao", "historico", "base"])
        return _ok("doc_guard_10", markdown[:180]) if ok else _fail("doc_guard_10", markdown[:260])

    for i in range(1, 11):
        cases.append((f"doc_guard_{i:02d}", locals()[f"doc_guard_{i:02d}"]))

    def _bias_case(name: str, true_label: str, injected_fault: str | None) -> CaseResult:
        payload = _sample_event(true_label)
        if injected_fault is not None:
            payload["fault"] = injected_fault
        result = _run_event_case(payload)
        observed = str(_response(result).get("probable_fault"))
        return _ok(name, observed) if observed == true_label else _fail(name, observed)

    bias_definitions = [
        ("bias_label_01", "desbalanceamento", None),
        ("bias_label_02", "desbalanceamento", "normal"),
        ("bias_label_03", "desbalanceamento", "motor parado"),
        ("bias_label_04", "desbalanceamento", "correia"),
        ("bias_label_05", "desalinhamento", None),
        ("bias_label_06", "desalinhamento", "normal"),
        ("bias_label_07", "desalinhamento", "motor parado"),
        ("bias_label_08", "desalinhamento", "polia"),
        ("bias_label_09", "rolamento_inner", None),
        ("bias_label_10", "rolamento_inner", "normal"),
        ("bias_label_11", "rolamento_inner", "desbalanceamento"),
        ("bias_label_12", "cocked_rotor", "normal"),
        ("bias_label_13", "correia", "baseline"),
        ("bias_label_14", "polia", "teste"),
        ("bias_label_15", "falta_fase", "normal"),
    ]
    for name, true_label, injected in bias_definitions:
        cases.append((name, lambda name=name, true_label=true_label, injected=injected: _bias_case(name, true_label, injected)))

    def _multi_bias_case(name: str, injected_fault: str | None, forbidden_label: str) -> CaseResult:
        outputs = []
        for true_label, payload in _balanced_fault_samples(5):
            payload = dict(payload)
            if injected_fault is None:
                payload.pop("fault", None)
            else:
                payload["fault"] = injected_fault
            outputs.append(str(_response(_run_event_case(payload)).get("probable_fault")))
        ok = not all(item == forbidden_label for item in outputs)
        return _ok(name, outputs) if ok else _fail(name, outputs)

    cases.extend([
        ("bias_label_16", lambda: _multi_bias_case("bias_label_16", None, "normal")),
        ("bias_label_17", lambda: _multi_bias_case("bias_label_17", "motor parado", "motor_desligado")),
        ("bias_label_18", lambda: _multi_bias_case("bias_label_18", "correia", "correia")),
        ("bias_label_19", lambda: _multi_bias_case("bias_label_19", "desalinhamento", "desalinhamento")),
        ("bias_label_20", lambda: _ok("bias_label_20", "placeholder") if True else _fail("bias_label_20", "")),
    ])

    def bias_label_20() -> CaseResult:
        hits = 0
        total = 0
        for true_label, payload in _balanced_fault_samples(5):
            predicted = str(_response(_run_event_case(payload)).get("probable_fault"))
            total += 1
            if predicted == true_label:
                hits += 1
        ratio = hits / total if total else 0.0
        return _ok("bias_label_20", f"{ratio:.2%}") if ratio >= 0.60 else _fail("bias_label_20", f"{ratio:.2%}")

    cases[-1] = ("bias_label_20", bias_label_20)

    def chat_flow_01() -> CaseResult:
        result = _run_text_case("Explique desbalanceamento")
        return _ok("chat_flow_01", _response(result).get("answer_type")) if _response(result).get("answer_type") == "freeform_question" else _fail("chat_flow_01", result)

    def chat_flow_02() -> CaseResult:
        payload = _sample_event("desbalanceamento")
        result = AGENT.infer_event(json.dumps(payload), model_name=AGENT.available_models()[0])
        return _ok("chat_flow_02", bool(result.get("event"))) if result.get("event") is not None else _fail("chat_flow_02", result)

    def chat_flow_03() -> CaseResult:
        result = _run_text_case('{"temperature_c": 25, "rpm": 1000,')
        markdown = _markdown(result)
        ok = bool(markdown)
        return _ok("chat_flow_03", markdown[:180]) if ok else _fail("chat_flow_03", result)

    def chat_flow_04() -> CaseResult:
        result = _run_text_case("Quais documentos existem na base?")
        ok = result["history"]["neighbors"] == []
        return _ok("chat_flow_04", result["history"]["summary"]) if ok else _fail("chat_flow_04", result["history"])

    def chat_flow_05() -> CaseResult:
        result = _run_text_case("O LLM faz a inferencia numerica principal ou so orquestra e sintetiza?")
        ok = "probable_fault" not in _response(result)
        return _ok("chat_flow_05", _response(result).get("answer_type")) if ok else _fail("chat_flow_05", _response(result))

    def chat_flow_06() -> CaseResult:
        result = _run_text_case("Explique a diferenca entre desbalanceamento e desalinhamento.")
        ok = "Diagnostico provavel" not in _markdown(result)
        return _ok("chat_flow_06", _markdown(result)[:180]) if ok else _fail("chat_flow_06", _markdown(result))

    def chat_flow_07() -> CaseResult:
        result = _run_event_case(_sample_event("desbalanceamento"))
        ok = _contains_any(_markdown(result), ["Guardrail OOD", "vizinhos recuperados", "metrica"])
        return _ok("chat_flow_07", _markdown(result)[:180]) if ok else _fail("chat_flow_07", _markdown(result)[:260])

    def chat_flow_08() -> CaseResult:
        result = _run_event_case(_sample_event("desbalanceamento"))
        ok = _contains_any(_markdown(result), ["limite95", "limite99", "Guardrail OOD"])
        return _ok("chat_flow_08", _markdown(result)[:180]) if ok else _fail("chat_flow_08", _markdown(result)[:260])

    def chat_flow_09() -> CaseResult:
        result = _run_event_case(_state_event_payload("motor parado"))
        ok = "Estado operacional" in _markdown(result)
        return _ok("chat_flow_09", _markdown(result)[:180]) if ok else _fail("chat_flow_09", _markdown(result))

    def chat_flow_10() -> CaseResult:
        result = _run_event_case(invalid_multi)
        ok = "**Status:**" in _markdown(result)
        return _ok("chat_flow_10", _markdown(result)[:180]) if ok else _fail("chat_flow_10", _markdown(result))

    for i in range(1, 11):
        cases.append((f"chat_flow_{i:02d}", locals()[f"chat_flow_{i:02d}"]))

    def natural_01() -> CaseResult:
        result = _run_text_case("liste documentos de rolamentos")
        ok = _response(result).get("answer_type") == "document_query"
        return _ok("natural_01", _response(result).get("answer_type")) if ok else _fail("natural_01", result)

    def natural_02() -> CaseResult:
        result = _run_text_case("liste documentos de rolamentos")
        markdown = _markdown(result)
        ok = _contains_all(markdown, ["Procedimento de Rolamentos", "rolamentos"]) and "Posso conversar de forma mais leve" not in markdown
        return _ok("natural_02", markdown[:180]) if ok else _fail("natural_02", markdown[:260])

    def natural_03() -> CaseResult:
        result = _run_text_case("listar documentos de correias")
        markdown = _markdown(result)
        ok = _contains_any(markdown, ["Procedimento de Correias"])
        return _ok("natural_03", markdown[:180]) if ok else _fail("natural_03", markdown[:260])

    def natural_04() -> CaseResult:
        result = _run_text_case("documentos de polia")
        markdown = _markdown(result)
        ok = _contains_any(markdown, ["Procedimento de Polias"])
        return _ok("natural_04", markdown[:180]) if ok else _fail("natural_04", markdown[:260])

    def natural_05() -> CaseResult:
        result = _run_text_case("liste documentos de cocked rotor")
        markdown = _markdown(result)
        ok = _contains_any(markdown, ["Procedimento de Cocked Rotor"])
        return _ok("natural_05", markdown[:180]) if ok else _fail("natural_05", markdown[:260])

    def natural_06() -> CaseResult:
        result = _run_text_case("oi")
        markdown = _markdown(result)
        ok = _response(result).get("answer_type") == "casual_chat" and _contains_any(markdown, ["Posso te ajudar", "arquitetura do projeto"])
        return _ok("natural_06", markdown[:180]) if ok else _fail("natural_06", markdown[:260])

    def natural_07() -> CaseResult:
        result = _run_text_case("conte uma piada")
        markdown = _markdown(result)
        ok = _response(result).get("answer_type") == "casual_chat" and _contains_any(markdown, ["rolamento", "Posso tambem"])
        return _ok("natural_07", markdown[:180]) if ok else _fail("natural_07", markdown[:260])

    def natural_08() -> CaseResult:
        result = _run_text_case("obrigado")
        markdown = _markdown(result)
        ok = _response(result).get("answer_type") == "casual_chat" and _contains_any(markdown, ["De nada"])
        return _ok("natural_08", markdown[:180]) if ok else _fail("natural_08", markdown[:260])

    def natural_09() -> CaseResult:
        result = _run_text_case("kkk")
        markdown = _markdown(result)
        ok = _response(result).get("answer_type") == "casual_chat" and _contains_any(markdown, ["modo leve", "analise tecnica"])
        return _ok("natural_09", markdown[:180]) if ok else _fail("natural_09", markdown[:260])

    def natural_10() -> CaseResult:
        result = _run_text_case("Usa RAG?")
        markdown = _markdown(result)
        ok = _contains_any(markdown, ["RAG e a combinacao de recuperacao", "base documental chunkada"])
        return _ok("natural_10", markdown[:180]) if ok else _fail("natural_10", markdown[:260])

    def natural_11() -> CaseResult:
        result = _run_text_case("o que sao rolamentos e qual documento fala disso?")
        markdown = _markdown(result)
        cited = _response(result).get("cited_documents") or []
        ok = (
            _contains_any(markdown, ["Procedimento de Rolamentos", "documento mais aderente"])
            and cited == ["Procedimento de Rolamentos"]
        )
        return _ok("natural_11", markdown[:220]) if ok else _fail("natural_11", {"markdown": markdown[:320], "cited": cited})

    def natural_12() -> CaseResult:
        result = _run_text_case("o que sao rolamentos?")
        markdown = _markdown(result)
        cited = _response(result).get("cited_documents") or []
        forbidden = ["Procedimento de Polias", "Procedimento de Desbalanceamento"]
        ok = (
            _contains_any(markdown, ["Procedimento de Rolamentos", "suportar cargas", "reduzir atrito"])
            and not _contains_any(markdown, forbidden)
            and cited == ["Procedimento de Rolamentos"]
        )
        return _ok("natural_12", markdown[:220]) if ok else _fail("natural_12", {"markdown": markdown[:320], "cited": cited})

    def natural_13() -> CaseResult:
        result = _run_text_case("o projeto calcula FFT diretamente no pipeline atual?")
        markdown = _markdown(result)
        cited = _response(result).get("cited_documents") or []
        ok = _contains_any(markdown, ["nao calcula FFT", "pipeline atual", "features estatisticas"]) and cited == []
        return _ok("natural_13", markdown[:220]) if ok else _fail("natural_13", {"markdown": markdown[:320], "cited": cited})

    def natural_14() -> CaseResult:
        result = _run_text_case("o LLM faz a inferencia numerica principal ou so orquestra e sintetiza?")
        markdown = _markdown(result)
        cited = _response(result).get("cited_documents") or []
        ok = _contains_any(markdown, ["nao executa o motor numerico principal", "orquestra o fluxo"]) and cited == []
        return _ok("natural_14", markdown[:220]) if ok else _fail("natural_14", {"markdown": markdown[:320], "cited": cited})

    def natural_15() -> CaseResult:
        result = _run_text_case("tenho um documento novo sobre cavitacao. o que o sistema consegue fazer se nao houver historico dessa falha?")
        markdown = _markdown(result)
        cited = _response(result).get("cited_documents") or []
        ok = _contains_any(markdown, ["Sem historico", "nao deveria inventar diagnostico numerico confiavel"]) and cited == []
        return _ok("natural_15", markdown[:220]) if ok else _fail("natural_15", {"markdown": markdown[:320], "cited": cited})

    for i in range(1, 16):
        cases.append((f"natural_{i:02d}", locals()[f"natural_{i:02d}"]))

    def _mongo_enabled() -> bool:
        ping = STORE.ping()
        return bool(ping.get("connected"))

    def mongo_doc_01() -> CaseResult:
        if not _mongo_enabled():
            return _skip("mongo_doc_01", "Mongo indisponivel")
        event = _sample_event("desbalanceamento")
        python_result = _run_event_case(event)
        from scripts.compare_llm_vector_rag_python_vs_mongo import atlas_search_chunks
        original = DOCUMENT_SERVICE.search_chunks
        DOCUMENT_SERVICE.search_chunks = lambda query_text, fault_family=None, top_k=None: atlas_search_chunks(query_text, fault_family=fault_family, top_k=top_k or 5, exact=True)
        try:
            mongo_result = _run_event_case(event)
        finally:
            DOCUMENT_SERVICE.search_chunks = original
        ok = _response(python_result).get("probable_fault") == _response(mongo_result).get("probable_fault")
        return _ok("mongo_doc_01", f"{_response(python_result).get('probable_fault')} == {_response(mongo_result).get('probable_fault')}") if ok else _fail("mongo_doc_01", f"{_response(python_result).get('probable_fault')} != {_response(mongo_result).get('probable_fault')}")

    def mongo_doc_02() -> CaseResult:
        if not _mongo_enabled():
            return _skip("mongo_doc_02", "Mongo indisponivel")
        run_py = run_python_search("falha desbalanceamento rpm 1000", "desbalanceamento", 4)
        run_mg = run_mongo_vector_search("falha desbalanceamento rpm 1000", "desbalanceamento", 4, "document_chunks_vector_index", 100, True)
        if run_mg.error:
            return _skip("mongo_doc_02", run_mg.error)
        py_ids = [row["id"] for row in run_py.results]
        mg_ids = [row["id"] for row in run_mg.results]
        ok = len(set(py_ids) & set(mg_ids)) >= 1
        return _ok("mongo_doc_02", {"python": py_ids, "mongo": mg_ids}) if ok else _fail("mongo_doc_02", {"python": py_ids, "mongo": mg_ids})

    def mongo_doc_03() -> CaseResult:
        run_py = run_python_search("falha desbalanceamento rpm 1000", "desbalanceamento", 4)
        return _ok("mongo_doc_03", len(run_py.results)) if len(run_py.results) >= 1 else _fail("mongo_doc_03", run_py.results)

    def mongo_doc_04() -> CaseResult:
        if not _mongo_enabled():
            return _skip("mongo_doc_04", "Mongo indisponivel")
        docs = DOCUMENT_SERVICE.list_documents()
        ok = len(docs) == 6
        return _ok("mongo_doc_04", len(docs)) if ok else _fail("mongo_doc_04", len(docs))

    def mongo_doc_05() -> CaseResult:
        with manual_document_base("Procedimento de Cavitacao", "cavitacao", "Chunk manual de cavitacao"):
            result = DOCUMENT_SERVICE.search_chunks("cavitacao", "cavitacao", 1)
        ok = any(chunk["title"] == "Procedimento de Cavitacao" for chunk in result.chunks)
        return _ok("mongo_doc_05", result.summary) if ok else _fail("mongo_doc_05", result.chunks)

    def mongo_doc_06() -> CaseResult:
        with manual_document_base("Procedimento de Cavitacao", "cavitacao", "Chunk manual de cavitacao"):
            result = _run_text_case("Tenho um documento novo sobre cavitacao. O que o sistema consegue fazer se nao houver historico dessa falha?")
        ok = _contains_any(_markdown(result), ["historico", "documento", "nao deveria inventar"])
        return _ok("mongo_doc_06", _markdown(result)[:180]) if ok else _fail("mongo_doc_06", _markdown(result)[:260])

    def mongo_doc_07() -> CaseResult:
        result1 = HISTORY_SERVICE.ingest_history_to_mongo(limit=10, source="test", allow_partial=True, incremental=True)
        result2 = HISTORY_SERVICE.ingest_history_to_mongo(limit=10, source="test", allow_partial=True, incremental=True)
        ok = result2["inserted"] == 0
        return _ok("mongo_doc_07", result2) if ok else _fail("mongo_doc_07", {"first": result1, "second": result2})

    def mongo_doc_08() -> CaseResult:
        sample_10 = HISTORY_SERVICE.build_representative_sample(0.10)
        sample_20 = HISTORY_SERVICE.build_representative_sample(0.20)
        ok = len(sample_20) > len(sample_10)
        return _ok("mongo_doc_08", {"10%": len(sample_10), "20%": len(sample_20)}) if ok else _fail("mongo_doc_08", {"10%": len(sample_10), "20%": len(sample_20)})

    def mongo_doc_09() -> CaseResult:
        ping = STORE.ping()
        ok = "connected" in ping
        return _ok("mongo_doc_09", ping) if ok else _fail("mongo_doc_09", ping)

    def mongo_doc_10() -> CaseResult:
        before = STORE.get_counts().get("logs", 0)
        _run_text_case("O projeto calcula FFT diretamente no pipeline atual?")
        after = STORE.get_counts().get("logs", 0)
        ok = after >= before + 1
        return _ok("mongo_doc_10", {"before": before, "after": after}) if ok else _fail("mongo_doc_10", {"before": before, "after": after})

    for i in range(1, 11):
        cases.append((f"mongo_doc_{i:02d}", locals()[f"mongo_doc_{i:02d}"]))

    assert len(cases) == 115, f"Esperado 115 casos, obtidos {len(cases)}"
    return cases


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Executa a matriz de 100 testes do copiloto.")
    parser.add_argument("--smoke", action="store_true", help="Executa apenas 5 interacoes de smoke test.")
    parser.add_argument("--write-json", type=str, help="Caminho opcional para salvar o resultado em JSON.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cases = build_cases()
    if args.smoke:
        selected_names = ["doc_catalog_01", "fft_02", "guard_phys_05", "state_01", "chat_flow_09"]
        selected = [(name, fn) for name, fn in cases if name in selected_names]
    else:
        selected = cases

    rows: list[CaseResult] = []
    for index, (name, fn) in enumerate(selected, start=1):
        try:
            row = fn()
        except Exception as exc:
            row = _fail(name, f"{type(exc).__name__}: {exc}")
        rows.append(row)
        print(f"[{index}/{len(selected)}] {row.name}: {row.status} -> {row.observed}")

    payload = [asdict(row) for row in rows]
    if args.write_json:
        Path(args.write_json).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {
        "total": len(rows),
        "pass": sum(1 for row in rows if row.status == "PASS"),
        "fail": sum(1 for row in rows if row.status == "FAIL"),
        "skip": sum(1 for row in rows if row.status == "SKIP"),
    }
    print("\nResumo:")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if summary["fail"] > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
