from __future__ import annotations

import html
import json
import time

import streamlit as st

from src.agent_service import AGENT
from src.benchmark_service import BENCHMARK_SERVICE
from src.conversation_store import save_conversation
from src.sidebar import render_shared_sidebar
from src.ui import inject_theme


inject_theme()

EMPTY_STATE_TITLE = "Ative sempre que precisar"
EMPTY_STATE_SUBTITLE = (
    "Sou o copiloto de manutencao prescritiva. Envie um evento JSON ou descreva a situacao. "
    "Eu decido quando consultar historico operacional e quando buscar lastro documental."
)


def _init_state() -> None:
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    if "last_result" not in st.session_state:
        st.session_state.last_result = None
    if "persona" not in st.session_state:
        st.session_state.persona = "PCP"
    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = None
    if "selected_model" not in st.session_state:
        models = AGENT.available_models()
        st.session_state.selected_model = models[0] if models else ""
    if "composer_text" not in st.session_state:
        st.session_state.composer_text = ""
    if "clear_composer" not in st.session_state:
        st.session_state.clear_composer = False
    if "selected_scenario_name" not in st.session_state:
        st.session_state.selected_scenario_name = ""


def _append_message(role: str, content: str) -> None:
    st.session_state.chat_messages.append({"role": role, "content": content})
    if st.session_state.chat_messages:
        saved = save_conversation(
            messages=st.session_state.chat_messages,
            conversation_id=st.session_state.conversation_id,
        )
        st.session_state.conversation_id = saved["id"]


def _build_prompt(raw_text: str, persona: str) -> str:
    if persona == "PCP":
        prefix = "Usuario do PCP: priorize impacto operacional, urgencia, risco e recomendacao objetiva.\n\n"
    else:
        prefix = "Usuario da manutencao: priorize inspecao, hipotese de falha, procedimento e acao tecnica.\n\n"
    return f"{prefix}{raw_text}"


def _scenario_prompt(name: str) -> str:
    scenario_map = {scenario.name: scenario for scenario in BENCHMARK_SERVICE.sample_scenarios()}
    return json.dumps(scenario_map[name].event, ensure_ascii=False, indent=2, default=str)


def _stream_markdown(text: str, delay: float = 0.004):
    for chunk in text.split(" "):
        yield chunk + " "
        time.sleep(delay)


def _render_user_message(content: str) -> None:
    safe_content = html.escape(content).replace("\n", "<br>")
    st.markdown(
        f"""
        <div class="user-row">
          <div class="user-bubble">
            <div class="user-bubble-header">
              <span>Usuario</span>
              <span class="avatar-chip avatar-user">U</span>
            </div>
            <div style="white-space: normal; overflow-wrap: anywhere;">{safe_content}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_assistant_message(content: str) -> None:
    avatar_col, body_col = st.columns([0.065, 0.935], vertical_alignment="top")
    with avatar_col:
        st.markdown('<div class="assistant-avatar">AI</div>', unsafe_allow_html=True)
    with body_col:
        st.markdown('<div class="assistant-label">Copiloto prescritivo</div>', unsafe_allow_html=True)
        st.markdown(content)


def _render_streaming_assistant_message(content: str) -> None:
    avatar_col, body_col = st.columns([0.065, 0.935], vertical_alignment="top")
    with avatar_col:
        st.markdown('<div class="assistant-avatar">AI</div>', unsafe_allow_html=True)
    with body_col:
        st.markdown('<div class="assistant-label">Copiloto prescritivo</div>', unsafe_allow_html=True)
        placeholder = st.empty()
        streamed = ""
        for chunk in _stream_markdown(content):
            streamed += chunk
            placeholder.markdown(streamed)


def _run_agent_from_text(raw_text: str, status_placeholder) -> None:
    if not raw_text.strip():
        return

    st.session_state.clear_composer = True
    _render_user_message(raw_text)
    _append_message("user", raw_text)
    composed_prompt = _build_prompt(raw_text, st.session_state.persona)

    with status_placeholder.container():
        with st.status("Analisando evento, historico e documentos...", expanded=False) as status_box:
            try:
                result = AGENT.infer_event(composed_prompt, model_name=st.session_state.selected_model or None)
                st.session_state.last_result = result
                markdown_response = result["agent_response"].get("response_markdown") or result["agent_response"].get(
                    "executive_summary", "Resposta gerada."
                )
                status_box.update(label="Analise concluida", state="complete")
                _render_streaming_assistant_message(markdown_response)
                _append_message("assistant", markdown_response)
            except Exception as exc:
                error_text = f"Falha ao executar a analise: {exc}"
                st.error(error_text)
                status_box.update(label="Falha na analise", state="error")
                _append_message("assistant", error_text)
    status_placeholder.empty()


def _render_last_result() -> None:
    result = st.session_state.last_result
    if not result:
        return

    with st.expander("Evidencias da ultima resposta", expanded=False):
        tabs = st.tabs(["Resposta estruturada", "Historico", "Documentos", "Validacao"])
        with tabs[0]:
            st.json(result["agent_response"], expanded=True)
        with tabs[1]:
            st.write(result["history"]["summary"])
            st.dataframe(result["history"]["neighbors"], width="stretch", hide_index=True)
            st.dataframe(result["history"]["fault_distribution"], width="stretch", hide_index=True)
        with tabs[2]:
            st.write(result["documents"]["summary"])
            for chunk in result["documents"]["chunks"]:
                with st.expander(f"{chunk['title']} | score={chunk['score']}"):
                    st.caption(chunk["source_file"])
                    st.write(chunk["chunk_text"])
        with tabs[3]:
            st.json(result["validation"], expanded=True)
            st.json(result["runtime"], expanded=False)


def _render_empty_state() -> None:
    st.markdown(
        f"""
        <div class="chat-empty-state">
          <div class="chat-empty-title">{EMPTY_STATE_TITLE}</div>
          <div class="chat-empty-subtitle">{EMPTY_STATE_SUBTITLE}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


_init_state()
render_shared_sidebar(current_page="chat")

st.markdown('<div class="chat-shell">', unsafe_allow_html=True)
if not st.session_state.chat_messages:
    _render_empty_state()
else:
    for message in st.session_state.chat_messages:
        if message["role"] == "user":
            _render_user_message(message["content"])
        else:
            _render_assistant_message(message["content"])

    _render_last_result()
status_placeholder = st.empty()
st.markdown("</div>", unsafe_allow_html=True)

with st.bottom:
    composer_left, composer_mid, composer_right = st.columns([0.08, 0.78, 0.14], vertical_alignment="bottom")
    with composer_left:
        with st.popover("", icon=":material/add_circle:", width="content"):
            st.markdown("#### Contexto da conversa")
            models = AGENT.available_models()
            st.session_state.selected_model = st.selectbox(
                "Modelo",
                models,
                index=models.index(st.session_state.selected_model) if st.session_state.selected_model in models else 0,
            )
            scenarios = BENCHMARK_SERVICE.sample_scenarios()
            scenario_names = [""] + [scenario.name for scenario in scenarios]
            st.session_state.selected_scenario_name = st.selectbox("Carregar cenario", scenario_names)
            if st.session_state.selected_scenario_name and st.button("Inserir cenario no composer", width="stretch"):
                st.session_state.composer_text = _scenario_prompt(st.session_state.selected_scenario_name)
                st.rerun()
            st.markdown("#### Atalhos")
            if st.button("Prompt PCP", width="stretch"):
                st.session_state.composer_text = "Recebi uma anomalia. Quero impacto operacional, prioridade e risco."
                st.rerun()
            if st.button("Prompt Manutencao", width="stretch"):
                st.session_state.composer_text = "Recebi uma anomalia. Quero hipotese de falha, inspecao e procedimento rastreavel."
                st.rerun()
    with composer_mid:
        if st.session_state.clear_composer:
            st.session_state.composer_text = ""
            st.session_state.clear_composer = False
        st.text_input(
            "Mensagem",
            placeholder="Envie um evento JSON ou descreva a situacao",
            label_visibility="collapsed",
            key="composer_text",
        )
    with composer_right:
        if st.button("", icon=":material/arrow_upward:", width="stretch"):
            _run_agent_from_text(st.session_state.composer_text, status_placeholder)
            st.rerun()
