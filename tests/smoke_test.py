from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agent_service import AGENT
from src.document_service import DOCUMENT_SERVICE
from src.history_service import HISTORY_SERVICE
from src.mongo_store import STORE


def main() -> None:
    history_result = HISTORY_SERVICE.ingest_history_to_mongo(limit=5000)
    assert history_result["inserted"] > 0, "Histórico não foi ingerido."

    document_result = DOCUMENT_SERVICE.ingest_default_documents()
    assert document_result["documents"] >= 6, "Documentos padrão não foram ingeridos."
    assert document_result["chunks"] > 0, "Chunks documentais não foram gerados."

    df = HISTORY_SERVICE.load_history_frame()
    candidate_families = ["desalinhamento", "rolamento_inner", "desbalanceamento", "cocked_rotor", "correia"]
    sample_event = []
    for family in candidate_families:
        sample_event = df[df["canonical_fault"] == family].head(1).to_dict(orient="records")
        if sample_event:
            break
    assert sample_event, "Não foi possível obter evento de teste."

    similarity = HISTORY_SERVICE.search_similar_events(sample_event[0], top_k=5)
    assert similarity.neighbors, "Busca histórica não retornou vizinhos."

    search = DOCUMENT_SERVICE.search_chunks("como corrigir desalinhamento de motor", fault_family="desalinhamento")
    assert search.chunks, "Busca documental não retornou chunks."

    inference = AGENT.infer_event(sample_event[0], model_name=AGENT.available_models()[0])
    assert inference["agent_response"].get("probable_fault"), "Agente não retornou falha provável."
    assert "documents" in inference and "chunks" in inference["documents"], "Agente não retornou lastro documental."

    counts = STORE.get_counts()
    assert counts["logs"] >= 1, "Observabilidade não registrou logs."
    print("Smoke test concluído com sucesso.")


if __name__ == "__main__":
    main()
