from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import json
import time

import pandas as pd

from src.agent_service import AGENT
from src.history_service import HISTORY_SERVICE
from src.observability import log_benchmark


@dataclass
class BenchmarkScenario:
    name: str
    description: str
    event: dict[str, Any]


class BenchmarkService:
    def sample_scenarios(self) -> list[BenchmarkScenario]:
        df = HISTORY_SERVICE.load_dataset()
        scenarios: list[BenchmarkScenario] = []
        targets = ["rolamento_inner", "desalinhamento", "desbalanceamento", "cocked_rotor", "correia"]
        for target in targets:
            rows = df[df["canonical_fault"] == target]
            if rows.empty:
                continue
            row = rows.iloc[0].to_dict()
            event = {
                key: row.get(key)
                for key in [
                    "id",
                    "created_at",
                    "fault",
                    "rpm",
                    "temperature_c",
                    "x_rms_velocity_mm_s",
                    "z_rms_velocity_mm_s",
                    "x_peak_acceleration_g",
                    "z_peak_acceleration_g",
                    "x_kurtosis",
                    "z_kurtosis",
                    "x_crest_factor",
                    "z_crest_factor",
                ]
            }
            scenarios.append(
                BenchmarkScenario(
                    name=f"Cenário {target}",
                    description=f"Amostra histórica de {target}",
                    event=event,
                )
            )
        return scenarios

    def run(self, models: list[str], scenario_names: list[str] | None = None) -> list[dict[str, Any]]:
        scenarios = self.sample_scenarios()
        if scenario_names:
            allowed = set(scenario_names)
            scenarios = [scenario for scenario in scenarios if scenario.name in allowed]
        results: list[dict[str, Any]] = []
        for model in models:
            for scenario in scenarios:
                started = time.perf_counter()
                inference = AGENT.infer_event(scenario.event, model_name=model)
                elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
                item = {
                    "model": model,
                    "scenario_name": scenario.name,
                    "scenario_description": scenario.description,
                    "elapsed_ms": elapsed_ms,
                    "probable_fault": inference["agent_response"].get("probable_fault"),
                    "confidence_pct": inference["agent_response"].get("confidence_pct"),
                    "documents_count": len(inference["documents"]["chunks"]),
                    "refusal_reason": inference["agent_response"].get("refusal_reason"),
                    "usage": inference["runtime"].get("usage"),
                }
                results.append(item)
                log_benchmark(item)
        return results

    def benchmark_frame(self) -> pd.DataFrame:
        records = STORE.find_all("benchmarks")
        return pd.DataFrame(records)


from src.mongo_store import STORE

BENCHMARK_SERVICE = BenchmarkService()
