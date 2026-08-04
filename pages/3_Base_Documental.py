from __future__ import annotations

import pandas as pd
import streamlit as st

from src.document_service import DOCUMENT_SERVICE
from src.fault_semantics import get_fault_catalog
from src.mongo_store import STORE
from src.sidebar import render_shared_sidebar
from src.ui import hero, inject_theme, metric_card


inject_theme()
render_shared_sidebar(current_page="documental")
hero("Base Documental", "Ingestao, chunking, vetorizacao e busca nos procedimentos tecnicos.", eyebrow="rag documental")

counts = STORE.get_counts()
col1, col2, col3 = st.columns(3)
with col1:
    metric_card("Documentos", str(counts["documents"]))
with col2:
    metric_card("Chunks", str(counts["document_chunks"]), tone="green")
with col3:
    metric_card("Colecao ativa", "Mongo/local", tone="amber")

left, right = st.columns((0.9, 1.1))
with left:
    if st.button("Ingerir PDFs tecnicos padrao", width="stretch"):
        result = DOCUMENT_SERVICE.ingest_default_documents()
        st.success(f"Ingestao concluida: {result['documents']} documentos e {result['chunks']} chunks.")

    with st.form("manual_doc_form"):
        st.subheader("Adicionar documento manual")
        title = st.text_input("Titulo")
        fault_family = st.selectbox("Familia de falha", [item["key"] for item in get_fault_catalog(include_other=False)])
        content = st.text_area("Conteudo", height=200)
        submitted = st.form_submit_button("Adicionar manual", width="stretch")
        if submitted:
            result = DOCUMENT_SERVICE.add_manual_document(title=title, fault_family=fault_family, content=content)
            st.success(f"Documento adicionado com {result['chunks_created']} chunk(s).")

with right:
    st.subheader("Busca vetorial")
    query_text = st.text_input("Consulta", value="como corrigir desalinhamento de motor")
    family_filter = st.selectbox("Filtro de familia", [""] + [item["key"] for item in get_fault_catalog()])
    if st.button("Buscar chunks", width="stretch"):
        search = DOCUMENT_SERVICE.search_chunks(query_text=query_text, fault_family=family_filter or None)
        st.info(search.summary)
        for item in search.chunks:
            with st.expander(f"{item['title']} | {item['fault_family']} | score={item['score']}"):
                st.caption(item["source_file"])
                st.write(item["chunk_text"])

st.markdown("### Biblioteca documental")
documents_df = pd.DataFrame(DOCUMENT_SERVICE.list_documents())
if not documents_df.empty:
    st.dataframe(documents_df[["title", "fault_family", "source_file", "source_type"]], width="stretch", hide_index=True)
else:
    st.info("Nenhum documento indexado ainda.")
