from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def _disable_mongo_for_test() -> None:
    os.environ["MONGO_ENABLED"] = "false"


_disable_mongo_for_test()

from src.agent_service import AGENT  # noqa: E402
from src.document_service import DOCUMENT_SERVICE  # noqa: E402
from src.fault_semantics import is_fault_label  # noqa: E402
from src.history_service import HISTORY_SERVICE  # noqa: E402


FEATURE_KEYS = [
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


@dataclass
class FaultCoverageResult:
    dataset_fault: str
    has_mapped_doc: bool
    predicted_fault: str
    confidence_pct: float | None
    refusal_reason: str
    cited_documents: list[str]
    recommended_actions: list[str]
    document_summary: str
    passed: bool


def build_payload(row: dict[str, Any]) -> dict[str, Any]:
    payload = {key: row.get(key) for key in FEATURE_KEYS if key in row}
    if "fault" in row:
        payload["fault"] = row.get("fault")
    return payload


def run_check() -> list[FaultCoverageResult]:
    df = HISTORY_SERVICE.load_dataset()
    model = AGENT.available_models()[0]
    doc_families = {
        str(doc.get("fault_family"))
        for doc in DOCUMENT_SERVICE.list_documents()
        if doc.get("fault_family")
    }
    real_faults = sorted(
        {
            label
            for label in df["canonical_fault"].dropna().unique().tolist()
            if is_fault_label(label)
        }
    )

    results: list[FaultCoverageResult] = []
    for fault in real_faults:
        row = df[df["canonical_fault"] == fault].head(1).to_dict(orient="records")[0]
        result = AGENT.infer_event(build_payload(row), model_name=model)
        response = result["agent_response"]
        has_mapped_doc = fault in doc_families
        cited_documents = list(response.get("cited_documents") or [])
        refusal_reason = str(response.get("refusal_reason") or "")
        recommended_actions = list(response.get("recommended_actions") or [])
        if has_mapped_doc:
            passed = bool(cited_documents)
        else:
            passed = (
                not cited_documents
                and "Nao ha documento tecnico suficiente" in refusal_reason
                and recommended_actions == ["Validar instrumentacao e ampliar base documental antes de automatizar a prescricao."]
            )
        results.append(
            FaultCoverageResult(
                dataset_fault=fault,
                has_mapped_doc=has_mapped_doc,
                predicted_fault=str(response.get("probable_fault") or ""),
                confidence_pct=response.get("confidence_pct"),
                refusal_reason=refusal_reason,
                cited_documents=cited_documents,
                recommended_actions=recommended_actions,
                document_summary=str(result.get("documents", {}).get("summary", "")),
                passed=passed,
            )
        )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Valida cobertura documental por falha no fluxo prescritivo.")
    parser.add_argument(
        "--output",
        default="docs/analise_markdown/fault_document_coverage_2026-08-07.json",
        help="Arquivo JSON de saida.",
    )
    args = parser.parse_args()

    results = run_check()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "summary": {
            "total_faults": len(results),
            "passed": sum(1 for item in results if item.passed),
            "failed": sum(1 for item in results if not item.passed),
            "mapped_docs": sum(1 for item in results if item.has_mapped_doc),
            "unmapped_docs": sum(1 for item in results if not item.has_mapped_doc),
        },
        "results": [asdict(item) for item in results],
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
