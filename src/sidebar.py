from __future__ import annotations

import math

import streamlit as st

from src.agent_service import AGENT
from src.conversation_store import get_conversation, list_conversations
from src.document_service import DOCUMENT_SERVICE
from src.history_service import HISTORY_SERVICE
from src.mongo_store import STORE
from src.ui import sidebar_section_title


def _ensure_core_session_state() -> None:
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    if "last_result" not in st.session_state:
        st.session_state.last_result = None
    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = None
    if "selected_model" not in st.session_state:
        models = AGENT.available_models()
        st.session_state.selected_model = models[0] if models else ""


def start_new_conversation() -> None:
    _ensure_core_session_state()
    st.session_state.chat_messages = []
    st.session_state.last_result = None
    st.session_state.conversation_id = None
    st.session_state.composer_text = ""


def load_conversation_to_session(conversation_id: str) -> bool:
    _ensure_core_session_state()
    loaded = get_conversation(conversation_id)
    if not loaded:
        return False
    st.session_state.chat_messages = loaded["messages"]
    st.session_state.conversation_id = loaded["id"]
    st.session_state.last_result = None
    return True


def render_shared_sidebar(current_page: str = "chat") -> None:
    _ensure_core_session_state()
    metrics = HISTORY_SERVICE.dataset_metrics()
    csv_rows = int(metrics["rows"])
    sample_target = math.ceil(csv_rows * 0.20)

    with st.sidebar:
        st.markdown("## Copiloto")
        if current_page == "chat":
            st.markdown(
                '<div class="sidebar-item active"><div class="sidebar-item-label">Conversa</div><div class="sidebar-item-meta">Chat principal da operacao</div></div>',
                unsafe_allow_html=True,
            )
        else:
            if st.button("Conversa", width="stretch", icon=":material/chat:"):
                st.switch_page("Home.py")

        st.page_link("pages/1_BI_de_Inferencias.py", label="Dashboard", icon=":material/insights:")
        st.page_link("pages/3_Base_Documental.py", label="Base documental", icon=":material/library_books:")
        st.page_link("pages/4_Historico_Operacional.py", label="Historico operacional", icon=":material/history:")
        st.page_link("pages/5_Benchmark_de_Modelos.py", label="Benchmark", icon=":material/bolt:")
        st.page_link("pages/6_Observabilidade.py", label="Observabilidade", icon=":material/receipt_long:")

        sidebar_section_title("Conversa")
        if st.button("Nova conversa", width="stretch", icon=":material/edit_square:"):
            start_new_conversation()
            st.switch_page("Home.py")

        sidebar_section_title("Recentes")
        conversation_search = st.text_input(
            "Pesquisar conversas",
            value="",
            placeholder="Buscar por titulo...",
            label_visibility="collapsed",
            key=f"conversation_search_{current_page}",
        )
        recent_conversations = list_conversations(limit=12)
        if conversation_search.strip():
            search_value = conversation_search.strip().lower()
            recent_conversations = [item for item in recent_conversations if search_value in str(item.get("title", "")).lower()]
        if recent_conversations:
            for conversation in recent_conversations:
                title = conversation.get("title", "Nova conversa")
                if st.button(
                    title,
                    key=f"conv_{current_page}_{conversation['id']}",
                    width="stretch",
                    icon=":material/chat_bubble:",
                ):
                    if load_conversation_to_session(conversation["id"]):
                        st.switch_page("Home.py")
        else:
            st.caption("Nenhuma conversa recente ainda.")

        with st.expander("Estado do sistema", expanded=False):
            st.write(f"Mongo: {'Configurado' if STORE.enabled() else 'Fallback local'}")
            st.write(f"Historico: {metrics['rows']:,}".replace(",", "."))
            st.write("Historico persistido: consultar pagina Historico operacional")
            st.write("Docs e chunks: consultar Base documental")
            st.write(f"Modelo base: {st.session_state.selected_model or 'n/a'}")
            st.write(
                "Camada semantica: "
                f"{metrics['fault_labels']} falhas | {metrics['state_labels']} estados"
            )
            st.caption(
                "Mongo gratis configurado com amostra representativa de 20% "
                f"(meta: {sample_target:,} registros).".replace(",", ".")
            )
            st.caption("A reingestao do historico fica disponivel apenas na pagina Historico operacional.")
            if st.button("Ingerir documentos", width="stretch", key=f"ingest_docs_{current_page}"):
                result = DOCUMENT_SERVICE.ingest_default_documents()
                st.success(f"{result['documents']} documentos | {result['chunks']} chunks.")
