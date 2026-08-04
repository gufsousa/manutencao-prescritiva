from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT_DIR / "config"
DATA_DIR = ROOT_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
APP_DATA_DIR = DATA_DIR / "app_state"
LOGS_DIR = APP_DATA_DIR / "logs"

load_dotenv(ROOT_DIR / ".env")


def _env_flag(name: str, default: bool = False) -> bool:
    value = str(os.getenv(name, str(default))).strip().lower()
    return value in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class AppSettings:
    llm_provider: str
    groq_api_key: str
    ollama_base_url: str
    default_llm_model: str
    fallback_llm_models: tuple[str, ...]
    mongo_connection_string: str
    mongo_database: str
    mongo_history_collection: str
    mongo_documents_collection: str
    mongo_document_chunks_collection: str
    mongo_logs_collection: str
    mongo_benchmarks_collection: str
    mongo_conversations_collection: str
    mongo_enabled: bool
    benchmark_enabled: bool
    streamlit_server_port: int
    top_k_documents: int
    top_k_history: int
    vector_dimensions: int


def get_settings() -> AppSettings:
    fallback_models = tuple(
        item.strip()
        for item in os.getenv("FALLBACK_LLM_MODELS", "llama-3.1-8b-instant,llama-3.3-70b-versatile").split(",")
        if item.strip()
    )
    return AppSettings(
        llm_provider=os.getenv("LLM_PROVIDER", "groq").strip().lower(),
        groq_api_key=os.getenv("GROQ_API_KEY", "").strip(),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip().rstrip("/"),
        default_llm_model=os.getenv("DEFAULT_LLM_MODEL", "llama-3.1-8b-instant").strip(),
        fallback_llm_models=fallback_models,
        mongo_connection_string=os.getenv("MONGO_CONNECTION_STRING", "").strip(),
        mongo_database=os.getenv("MONGO_DATABASE", "manutencao_prescritiva").strip(),
        mongo_history_collection=os.getenv("MONGO_HISTORY_COLLECTION", "historical_events").strip(),
        mongo_documents_collection=os.getenv("MONGO_DOCUMENTS_COLLECTION", "documents").strip(),
        mongo_document_chunks_collection=os.getenv("MONGO_DOCUMENT_CHUNKS_COLLECTION", "document_chunks").strip(),
        mongo_logs_collection=os.getenv("MONGO_LOGS_COLLECTION", "inference_logs").strip(),
        mongo_benchmarks_collection=os.getenv("MONGO_BENCHMARKS_COLLECTION", "benchmark_runs").strip(),
        mongo_conversations_collection=os.getenv("MONGO_CONVERSATIONS_COLLECTION", "conversations").strip(),
        mongo_enabled=_env_flag("MONGO_ENABLED", False),
        benchmark_enabled=_env_flag("BENCHMARK_ENABLED", True),
        streamlit_server_port=int(os.getenv("STREAMLIT_SERVER_PORT", "8501")),
        top_k_documents=int(os.getenv("TOP_K_DOCUMENTS", "5")),
        top_k_history=int(os.getenv("TOP_K_HISTORY", "5")),
        vector_dimensions=int(os.getenv("VECTOR_DIMENSIONS", "256")),
    )


SETTINGS = get_settings()
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
