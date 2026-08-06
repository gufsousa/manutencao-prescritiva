from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agent_service import AGENT


@dataclass
class IntentCase:
    name: str
    prompt: str
    expected_route: str
    expected_answer_type: str | None = None


@dataclass
class IntentResult:
    name: str
    prompt: str
    expected_route: str
    observed_route: str
    expected_answer_type: str | None
    observed_answer_type: str | None
    status: str
    markdown_preview: str


def build_cases() -> list[IntentCase]:
    return [
        IntentCase("casual_01", "oi", "freeform_question", "casual_chat"),
        IntentCase("casual_02", "boa tarde", "freeform_question", "casual_chat"),
        IntentCase("casual_03", "obrigado", "freeform_question", "casual_chat"),
        IntentCase("casual_04", "kkk", "freeform_question", "casual_chat"),
        IntentCase("casual_05", "conte uma piada", "freeform_question", "casual_chat"),
        IntentCase("doc_01", "Quais documentos existem na base?", "document_query", "document_query"),
        IntentCase("doc_02", "quais documento tem sobre rolamento", "document_query", "document_query"),
        IntentCase("doc_03", "liste documentos de rolamento", "document_query", "document_query"),
        IntentCase("doc_04", "listar documentos de correias", "document_query", "document_query"),
        IntentCase("doc_05", "documentos de polia", "document_query", "document_query"),
        IntentCase("doc_06", "quais arquivos cobrem cocked rotor", "document_query", "document_query"),
        IntentCase("doc_07", "me diga os documentos da base documental", "document_query", "document_query"),
        IntentCase("doc_08", "tem procedimento sobre desalinhamento?", "document_query", "document_query"),
        IntentCase("doc_09", "tem documento de desbalanceamento", "document_query", "document_query"),
        IntentCase("free_01", "o que sao rolamentos?", "freeform_question", "freeform_question"),
        IntentCase("free_02", "Explique a diferenca entre desbalanceamento e desalinhamento.", "freeform_question", "freeform_question"),
        IntentCase("free_03", "O que e FFT e por que ela importa?", "freeform_question", "freeform_question"),
        IntentCase("free_04", "Usa RAG?", "freeform_question", "freeform_question"),
        IntentCase("free_05", "O Mongo esta como persistencia ou motor vetorial?", "freeform_question", "freeform_question"),
        IntentCase("free_06", "se eu adicionar uma falha nova sem historico o sistema inventa?", "freeform_question", "freeform_question"),
        IntentCase("free_07", "o LLM faz a inferencia numerica principal?", "freeform_question", "freeform_question"),
        IntentCase("free_08", "o projeto calcula FFT no pipeline atual?", "freeform_question", "freeform_question"),
        IntentCase("free_09", "me explique a arquitetura em 30 segundos", "freeform_question", "freeform_question"),
        IntentCase("free_10", "o que sao rolamentos e qual documento fala disso?", "freeform_question", "freeform_question"),
        IntentCase("event_01", '{"temperature_c": 24.7, "rpm": 1000, "x_rms_velocity_mm_s": 2.0, "z_rms_velocity_mm_s": 1.517, "x_peak_acceleration_g": 0.631, "z_peak_acceleration_g": 0.484, "x_rms_acceleration_g": 0.114, "z_rms_acceleration_g": 0.09, "x_kurtosis": 2.77, "z_kurtosis": 2.392, "x_crest_factor": 4.269, "z_crest_factor": 3.747}', "event_json", None),
        IntentCase("event_02", '{"temperature_c": 23.5, "rpm": 0, "x_rms_velocity_mm_s": 0.05, "z_rms_velocity_mm_s": 0.04, "x_peak_acceleration_g": 0.02, "z_peak_acceleration_g": 0.02, "x_rms_acceleration_g": 0.01, "z_rms_acceleration_g": 0.01, "x_kurtosis": 2.1, "z_kurtosis": 2.0, "x_crest_factor": 1.8, "z_crest_factor": 1.7, "fault": "motor parado"}', "event_json", None),
        IntentCase("event_03", "{'temperature_c': 30, 'rpm': 1800, 'x_rms_velocity_mm_s': 6.2, 'z_rms_velocity_mm_s': 4.9}", "event_json", None),
        IntentCase("event_04", '{"temperature_c": 500, "rpm": -10, "x_rms_velocity_mm_s": -1, "z_rms_velocity_mm_s": -2}', "event_json", None),
        IntentCase("hybrid_01", "Tenho um documento novo sobre cavitacao. O que o sistema faz se nao houver historico?", "freeform_question", "freeform_question"),
        IntentCase("hybrid_02", "Tem documentos de rolamento e o que sao rolamentos?", "freeform_question", "freeform_question"),
        IntentCase("hybrid_03", "Liste documentos de rolamento e resuma o procedimento.", "document_query", "document_query"),
        IntentCase("hybrid_04", "Quais documentos existem na base e qual deles fala de polia?", "document_query", "document_query"),
        IntentCase("hybrid_05", "me mande um json de exemplo de evento", "freeform_question", "example_event"),
        IntentCase("edge_01", "rolamento", "freeform_question", "freeform_question"),
        IntentCase("edge_02", "documento rolamento", "document_query", "document_query"),
        IntentCase("edge_03", "sobre rolamento", "document_query", "document_query"),
        IntentCase("edge_04", "sobre rolamentos", "document_query", "document_query"),
        IntentCase("edge_05", "desalinhamento", "freeform_question", "freeform_question"),
        IntentCase("edge_06", "tem doc de polia?", "document_query", "document_query"),
        IntentCase("edge_07", "quais arquivos de correia", "document_query", "document_query"),
        IntentCase("edge_08", "o que é rolamento", "freeform_question", "freeform_question"),
    ]


def run_case(case: IntentCase) -> IntentResult:
    observed_route = AGENT._classify_input(case.prompt)
    result = AGENT.infer_event(case.prompt, model_name=AGENT.available_models()[0])
    observed_answer_type = result["agent_response"].get("answer_type")
    markdown_preview = str(result["agent_response"].get("response_markdown", ""))[:220]
    route_ok = observed_route == case.expected_route
    answer_ok = case.expected_answer_type is None or observed_answer_type == case.expected_answer_type
    status = "PASS" if route_ok and answer_ok else "FAIL"
    return IntentResult(
        name=case.name,
        prompt=case.prompt,
        expected_route=case.expected_route,
        observed_route=observed_route,
        expected_answer_type=case.expected_answer_type,
        observed_answer_type=observed_answer_type,
        status=status,
        markdown_preview=markdown_preview,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Avalia o roteamento de intencao do copiloto.")
    parser.add_argument("--write-json", type=str, help="Caminho opcional para salvar o resultado em JSON.")
    args = parser.parse_args()

    cases = build_cases()
    rows = [run_case(case) for case in cases]
    passed = sum(1 for row in rows if row.status == "PASS")
    failed = len(rows) - passed

    for index, row in enumerate(rows, start=1):
        print(
            f"[{index}/{len(rows)}] {row.name}: {row.status} | "
            f"route={row.observed_route} | answer={row.observed_answer_type}"
        )

    summary = {
        "date": "2026-08-06",
        "total": len(rows),
        "pass": passed,
        "fail": failed,
        "results": [asdict(row) for row in rows],
    }

    if args.write_json:
        output_path = Path(args.write_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nResumo:")
    print(json.dumps({k: v for k, v in summary.items() if k != "results"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
