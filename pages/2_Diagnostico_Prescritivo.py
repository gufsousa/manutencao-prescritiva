from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from src.agent_service import AGENT
from src.benchmark_service import BENCHMARK_SERVICE
from src.sidebar import render_shared_sidebar
from src.ui import hero, inject_theme, metric_card


inject_theme()
render_shared_sidebar(current_page="diagnostico")
hero("Diagnostico Prescritivo", "Entrada de evento, execucao do agente LLM-first e rastreabilidade de evidencias.", eyebrow="agente prescritivo")

scenarios = BENCHMARK_SERVICE.sample_scenarios()
scenario_options = {scenario.name: scenario for scenario in scenarios}
selected_scenario = st.selectbox("Cenario de exemplo", [""] + list(scenario_options.keys()))
default_payload = "{}"
if selected_scenario:
    default_payload = json.dumps(scenario_options[selected_scenario].event, ensure_ascii=False, indent=2, default=str)

models = AGENT.available_models()
model_name = st.selectbox("Modelo Groq", models, index=0 if models else None)
event_input = st.text_area("Evento JSON", value=default_payload, height=260)

if "last_inference" not in st.session_state:
    st.session_state.last_inference = None

if st.button("Executar inferencia", type="primary", width="stretch"):
    try:
        st.session_state.last_inference = AGENT.infer_event(event_input, model_name=model_name)
        st.success("Inferencia concluida.")
    except Exception as exc:
        st.error(f"Falha ao executar inferencia: {exc}")

result = st.session_state.last_inference
if result:
    response = result["agent_response"]
    runtime = result["runtime"]
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("Falha provavel", str(response.get("probable_fault", "n/a")))
    with col2:
        metric_card("Confianca", f"{response.get('confidence_pct', 0)}%", tone="amber")
    with col3:
        metric_card("Chunks recuperados", str(len(result["documents"]["chunks"])), tone="green")
    with col4:
        metric_card("Latencia", f"{runtime['elapsed_ms']} ms", tone="amber")

    st.markdown("### Resposta do agente")
    st.json(response, expanded=True)

    tabs = st.tabs(["Validacao", "Historico", "Documentos", "Runtime"])
    with tabs[0]:
        st.json(result["validation"], expanded=True)
    with tabs[1]:
        st.write(result["history"]["summary"])
        st.dataframe(pd.DataFrame(result["history"]["neighbors"]), width="stretch", hide_index=True)
        st.dataframe(pd.DataFrame(result["history"]["fault_distribution"]), width="stretch", hide_index=True)
    with tabs[2]:
        st.write(result["documents"]["summary"])
        for chunk in result["documents"]["chunks"]:
            with st.expander(f"{chunk['title']} | score={chunk['score']}"):
                st.caption(chunk["source_file"])
                st.write(chunk["chunk_text"])
    with tabs[3]:
        st.json(runtime, expanded=True)
