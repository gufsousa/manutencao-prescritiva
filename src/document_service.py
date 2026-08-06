from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import hashlib
import re
import uuid

from pypdf import PdfReader

from src.fault_semantics import canonicalize_fault_label, format_fault_label_pt
from src.mongo_store import STORE
from src.settings import RAW_DATA_DIR, SETTINGS
from src.vectorization import cosine_similarity, embed_many, embed_text


DOC_SOURCES = [
    {"path": RAW_DATA_DIR / "Doc1.pdf", "fault_family": "rolamento_inner", "title": "Procedimento de Rolamentos"},
    {"path": RAW_DATA_DIR / "Doc2.pdf", "fault_family": "desalinhamento", "title": "Procedimento de Desalinhamento"},
    {"path": RAW_DATA_DIR / "Doc3.pdf", "fault_family": "desbalanceamento", "title": "Procedimento de Desbalanceamento"},
    {"path": RAW_DATA_DIR / "Doc4.pdf", "fault_family": "correia", "title": "Procedimento de Correias"},
    {"path": RAW_DATA_DIR / "Doc5.pdf", "fault_family": "polia", "title": "Procedimento de Polias"},
    {"path": RAW_DATA_DIR / "Doc6.pdf", "fault_family": "cocked_rotor", "title": "Procedimento de Cocked Rotor"},
]

FALLBACK_DOC_TEXT = {
    "Doc1.pdf": (
        "Procedimento para diagnóstico e correção de problemas em rolamentos. "
        "Abrange identificação, diagnóstico, correção e validação de falhas em rolamentos de máquinas rotativas, "
        "incluindo componentes como anel interno, anel externo, elementos rolantes, gaiola, vedação e lubrificação."
    ),
}


@dataclass
class DocumentSearchResult:
    chunks: list[dict[str, Any]]
    summary: str


class DocumentService:
    def extract_text(self, pdf_path: Path) -> str:
        reader = PdfReader(pdf_path.open("rb"))
        pages: list[str] = []
        for page in reader.pages:
            try:
                pages.append(page.extract_text() or "")
            except Exception:
                continue
        text = "\n".join(pages).strip()
        if len(text) < 60:
            text = FALLBACK_DOC_TEXT.get(pdf_path.name, text)
        return re.sub(r"\s+", " ", text).strip()

    def chunk_text(self, text: str, max_chars: int = 900, overlap: int = 120) -> list[str]:
        if len(text) <= max_chars:
            return [text]
        sentences = re.split(r"(?<=[\.\!\?])\s+", text)
        chunks: list[str] = []
        current = ""
        for sentence in sentences:
            if not sentence.strip():
                continue
            candidate = f"{current} {sentence}".strip()
            if len(candidate) <= max_chars:
                current = candidate
                continue
            if current:
                chunks.append(current)
            current = sentence[-overlap:] if len(sentence) > max_chars else sentence
        if current:
            chunks.append(current)
        deduped = []
        seen = set()
        for chunk in chunks:
            digest = hashlib.md5(chunk.encode("utf-8")).hexdigest()
            if digest not in seen:
                seen.add(digest)
                deduped.append(chunk)
        return deduped

    def build_documents_payload(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        documents: list[dict[str, Any]] = []
        chunks_payload: list[dict[str, Any]] = []
        for item in DOC_SOURCES:
            text = self.extract_text(item["path"])
            doc_id = str(uuid.uuid4())
            documents.append(
                {
                    "id": doc_id,
                    "title": item["title"],
                    "fault_family": canonicalize_fault_label(item["fault_family"]),
                    "source_file": str(item["path"]),
                    "content": text,
                    "source_type": "pdf",
                }
            )
            chunks = self.chunk_text(text)
            vectors = embed_many(chunks)
            for index, (chunk_text, vector) in enumerate(zip(chunks, vectors, strict=False)):
                chunks_payload.append(
                    {
                        "id": str(uuid.uuid4()),
                        "document_id": doc_id,
                        "source_file": str(item["path"]),
                        "title": item["title"],
                        "fault_family": canonicalize_fault_label(item["fault_family"]),
                        "chunk_index": index,
                        "chunk_text": chunk_text,
                        "vector": vector,
                    }
                )
        return documents, chunks_payload

    def ingest_default_documents(self) -> dict[str, Any]:
        documents, chunks_payload = self.build_documents_payload()
        STORE.replace_many("documents", documents)
        STORE.replace_many("document_chunks", chunks_payload)
        return {"documents": len(documents), "chunks": len(chunks_payload)}

    def add_manual_document(self, title: str, fault_family: str, content: str, source_file: str = "manual_input") -> dict[str, Any]:
        doc_id = str(uuid.uuid4())
        document = {
            "id": doc_id,
            "title": title,
            "fault_family": canonicalize_fault_label(fault_family),
            "source_file": source_file,
            "content": content,
            "source_type": "manual",
        }
        chunks = self.chunk_text(content)
        vectors = embed_many(chunks)
        chunk_docs = [
            {
                "id": str(uuid.uuid4()),
                "document_id": doc_id,
                "source_file": source_file,
                "title": title,
                "fault_family": canonicalize_fault_label(fault_family),
                "chunk_index": index,
                "chunk_text": chunk,
                "vector": vector,
            }
            for index, (chunk, vector) in enumerate(zip(chunks, vectors, strict=False))
        ]
        docs = STORE.find_all("documents")
        docs.append(document)
        STORE.replace_many("documents", docs)
        current_chunks = STORE.find_all("document_chunks")
        current_chunks.extend(chunk_docs)
        STORE.replace_many("document_chunks", current_chunks)
        return {"document": document, "chunks_created": len(chunk_docs)}

    def list_documents(self) -> list[dict[str, Any]]:
        return STORE.find_all("documents")

    def list_chunks(self) -> list[dict[str, Any]]:
        return STORE.find_all("document_chunks")

    def search_chunks(self, query_text: str, fault_family: str | None = None, top_k: int | None = None) -> DocumentSearchResult:
        top_k = SETTINGS.top_k_documents if top_k is None else max(int(top_k), 0)
        chunks = self.list_chunks()
        if fault_family:
            canonical_fault = canonicalize_fault_label(fault_family)
            filtered = [chunk for chunk in chunks if chunk.get("fault_family") == canonical_fault]
            chunks = filtered or chunks
        if not chunks:
            return DocumentSearchResult(chunks=[], summary="Nenhum chunk indexado.")
        if top_k == 0:
            return DocumentSearchResult(chunks=[], summary="Busca documental nao executada para esta consulta.")

        query_vector = embed_text(query_text)
        ranked = []
        for chunk in chunks:
            similarity = cosine_similarity(query_vector, chunk.get("vector", []))
            if fault_family and chunk.get("fault_family") == canonicalize_fault_label(fault_family):
                similarity += 0.12
            ranked.append({**chunk, "score": round(similarity, 4)})
        ranked = sorted(ranked, key=lambda item: item["score"], reverse=True)[:top_k]
        summary = f"{len(ranked)} chunk(s) recuperados para {format_fault_label_pt(fault_family) if fault_family else 'consulta livre'}."
        return DocumentSearchResult(chunks=ranked, summary=summary)


DOCUMENT_SERVICE = DocumentService()
