from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
import json
import re
import time
from urllib import error, request

from groq import Groq

from src.document_service import DOCUMENT_SERVICE
from src.fault_semantics import canonicalize_fault_label, format_fault_label_pt, get_fault_catalog, get_label_kind, is_state_label
from src.history_service import HISTORY_SERVICE
from src.observability import log_inference
from src.prompt_loader import load_prompt
from src.settings import SETTINGS


SYSTEM_PROMPT = load_prompt("maintenance_event_system.md")
FREEFORM_SYSTEM_PROMPT = load_prompt("freeform_system.md")
INPUT_ROUTER_PROMPT = load_prompt("input_router.md")
FEW_SHOT_PROMPT = load_prompt("prescriptive_response_few_shot.md")


class PrescriptiveAgent:
    def __init__(self) -> None:
        self._provider = SETTINGS.llm_provider
        self._groq_client = Groq(api_key=SETTINGS.groq_api_key) if SETTINGS.groq_api_key else None

    def available_models(self) -> list[str]:
        if self._provider == "ollama":
            local_models = self._ollama_model_names()
            if local_models:
                return local_models
        models = [SETTINGS.default_llm_model, *SETTINGS.fallback_llm_models]
        seen: list[str] = []
        for model in models:
            if model and model not in seen:
                seen.append(model)
        return seen

    def _ollama_request(self, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{SETTINGS.ollama_base_url}{path}"
        data = None
        headers = {}
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = request.Request(url=url, data=data, headers=headers, method="POST" if payload is not None else "GET")
        with request.urlopen(req, timeout=90) as response:
            return json.loads(response.read().decode("utf-8"))

    def _ollama_model_names(self) -> list[str]:
        try:
            payload = self._ollama_request("/api/tags")
            names = [str(item.get("name", "")).strip() for item in payload.get("models", [])]
            return [name for name in names if name]
        except Exception:
            return []

    def _chat_complete(self, messages: list[dict[str, str]], model: str, temperature: float = 0.1) -> tuple[str, dict[str, Any]]:
        if self._provider == "ollama":
            payload = {
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                },
            }
            response = self._ollama_request("/api/chat", payload)
            content = ((response.get("message") or {}).get("content") or "").strip()
            usage = {
                "prompt_tokens": response.get("prompt_eval_count"),
                "completion_tokens": response.get("eval_count"),
                "total_tokens": (response.get("prompt_eval_count") or 0) + (response.get("eval_count") or 0),
                "provider": "ollama",
            }
            return content, usage

        if self._groq_client is None:
            raise RuntimeError("Nenhum backend de LLM disponivel.")
        completion = self._groq_client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=messages,
        )
        content = completion.choices[0].message.content or ""
        usage = {
            "prompt_tokens": getattr(completion.usage, "prompt_tokens", None),
            "completion_tokens": getattr(completion.usage, "completion_tokens", None),
            "total_tokens": getattr(completion.usage, "total_tokens", None),
            "provider": "groq",
        }
        return content, usage

    def _extract_json(self, text: str) -> dict[str, Any]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if not match:
                return {}
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return {}

    def _classify_input(self, raw_input: str | dict[str, Any]) -> str:
        if isinstance(raw_input, dict):
            return "event_json"

        text = str(raw_input or "").strip()
        if not text:
            return "freeform_question"
        if self._extract_json(text):
            return "event_json"

        lowered = text.lower()
        document_patterns = [
            "quais documentos",
            "liste documentos",
            "listar documentos",
            "que documentos",
            "documentos tem",
            "documentos de",
            "documento de",
            "lista de documentos",
            "base documental",
            "base de dados",
            "na base",
            "quais arquivos",
        ]
        if any(pattern in lowered for pattern in document_patterns):
            return "document_query"

        if self._provider in {"groq", "ollama"} and (self._provider != "groq" or self._groq_client is not None):
            try:
                routed, _ = self._chat_complete(
                    model=SETTINGS.default_llm_model,
                    temperature=0,
                    messages=[
                        {"role": "system", "content": INPUT_ROUTER_PROMPT},
                        {"role": "user", "content": text},
                    ],
                )
                routed = routed.strip().lower()
                if routed in {"event_json", "document_query", "freeform_question"}:
                    return routed
            except Exception:
                pass

        return "freeform_question"

    def _parse_event_input(self, raw_input: str | dict[str, Any]) -> dict[str, Any]:
        if isinstance(raw_input, dict):
            return raw_input
        try:
            return json.loads(raw_input)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw_input, re.DOTALL)
            if match:
                return json.loads(match.group(0))
        raise ValueError("Nao foi possivel interpretar o evento como JSON valido.")

    def _extract_document_focus(self, user_text: str, documents_catalog: list[dict[str, Any]]) -> str | None:
        lowered = str(user_text or "").lower()
        if "rolament" in lowered:
            return "rolamento_inner"

        for item in documents_catalog:
            fault_family = canonicalize_fault_label(item.get("fault_family"))
            title = str(item.get("title") or "").lower()
            if fault_family and fault_family != "nao_informada":
                family_terms = {
                    fault_family,
                    fault_family.replace("_", " "),
                    format_fault_label_pt(fault_family).lower(),
                }
                if any(term and term in lowered for term in family_terms):
                    return fault_family
            if title and title in lowered:
                return fault_family
        return None

    def _casual_response(self, lowered: str) -> dict[str, Any] | None:
        greeting_patterns = ["oi", "ola", "ol?", "bom dia", "boa tarde", "boa noite"]
        thanks_patterns = ["obrigado", "obrigada", "valeu"]
        joke_patterns = ["piada", "conte uma piada", "me conta uma piada"]
        laugh_patterns = ["kkk", "haha", "rsrs"]

        if any(pattern in lowered for pattern in joke_patterns):
            return {
                "answer_type": "casual_chat",
                "executive_summary": (
                    "Claro. Versao manutencao preditiva: o sensor falou que estava tudo normal, "
                    "mas era so o rolamento tentando manter a postura profissional."
                ),
                "evidence_points": [],
                "recommended_actions": [
                    "Se quiser, depois eu volto para o modo serio e explico qualquer parte tecnica do projeto."
                ],
                "cited_documents": [],
                "refusal_reason": "",
            }

        if any(pattern in lowered for pattern in greeting_patterns):
            return {
                "answer_type": "casual_chat",
                "executive_summary": (
                    "Oi. Posso te ajudar com uma pergunta tecnica, listar documentos da base, "
                    "analisar um evento JSON ou resumir a arquitetura do projeto."
                ),
                "evidence_points": [],
                "recommended_actions": [],
                "cited_documents": [],
                "refusal_reason": "",
            }

        if any(pattern in lowered for pattern in thanks_patterns):
            return {
                "answer_type": "casual_chat",
                "executive_summary": "De nada. Se quiser, seguimos com a parte tecnica.",
                "evidence_points": [],
                "recommended_actions": [],
                "cited_documents": [],
                "refusal_reason": "",
            }

        if any(pattern in lowered for pattern in laugh_patterns):
            return {
                "answer_type": "casual_chat",
                "executive_summary": "Boa. Se quiser, eu continuo no modo leve ou volto para a analise tecnica.",
                "evidence_points": [],
                "recommended_actions": [],
                "cited_documents": [],
                "refusal_reason": "",
            }

        return None

    def _event_query_text(self, event: dict[str, Any], candidate_fault: str) -> str:
        return (
            f"falha {candidate_fault} "
            f"rpm {event.get('rpm')} "
            f"temperatura {event.get('temperature_c')} "
            f"vibracao_x {event.get('x_rms_velocity_mm_s')} "
            f"vibracao_z {event.get('z_rms_velocity_mm_s')} "
            "inspecao manutencao correcao procedimento tecnico"
        )

    def _deterministic_fallback(
        self,
        event: dict[str, Any],
        validation: dict[str, Any],
        history: dict[str, Any],
        documents: list[dict[str, Any]],
        candidate_fault: str,
    ) -> dict[str, Any]:
        label_kind = get_label_kind(candidate_fault)
        refusal_reason = ""
        effective_label = candidate_fault
        if not validation.get("valid", True):
            refusal_reason = "Evento invalido segundo validacao fisica."
            effective_label = "evento_invalido"
        elif history.get("ood_flag"):
            refusal_reason = "Evento fora do envelope estatistico historico (OOD). Requer validacao humana e registro complementar antes de prescricao automatica."
        elif not documents and not is_state_label(candidate_fault):
            refusal_reason = "Nao ha documento tecnico suficiente para sustentar prescricao."

        if label_kind == "state" and not refusal_reason:
            executive_summary = (
                f"O evento se parece mais com um estado operacional ({format_fault_label_pt(candidate_fault)}) "
                "do que com uma falha mecanica ou eletrica confirmada."
            )
            recommended_actions = [
                "Confirmar se o equipamento realmente esta parado ou em condicao basal esperada.",
                "Validar contexto operacional antes de abrir ordem de manutencao corretiva.",
                "Usar a resposta como classificacao de estado, nao como diagnostico de falha."
            ]
            inspection_checklist = [
                "Confirmar se a rotacao e coerente com o estado informado.",
                "Verificar se o evento representa parada, baseline ou transiente operacional.",
                "Registrar contexto de operacao para evitar classificar estado como falha."
            ]
            risk_notes = [
                "Estado operacional nao equivale automaticamente a defeito fisico.",
                "Nao usar esta resposta isoladamente para justificar intervencao corretiva.",
                "Se houver suspeita real de falha, coletar evento em carga e contexto comparavel."
            ]
            cited_documents: list[str] = []
            evidence_points = [
                history["summary"],
                "A camada semantica classificou o rotulo candidato como estado operacional.",
                *[f"Validacao: {warning}" for warning in validation.get("warnings", [])],
            ]
            confidence_value = float(history.get("confidence_pct") or (history["fault_distribution"][0]["pct"] if history["fault_distribution"] else 0.0))
            return {
                "probable_fault": candidate_fault,
                "confidence_pct": confidence_value,
                "executive_summary": executive_summary,
                "evidence_points": evidence_points,
                "recommended_actions": recommended_actions,
                "inspection_checklist": inspection_checklist,
                "risk_notes": risk_notes,
                "refusal_reason": refusal_reason,
                "cited_documents": cited_documents,
            }

        inspection_checklist = [
            "Confirmar consistencia do evento de sensores.",
            "Verificar contexto operacional e rotacao.",
            "Comparar com ocorrencias historicas proximas.",
        ]
        if not documents or effective_label == "evento_invalido":
            inspection_checklist = []

        return {
            "probable_fault": effective_label,
            "confidence_pct": 0.0 if effective_label == "evento_invalido" else float(history.get("confidence_pct") or (history["fault_distribution"][0]["pct"] if history["fault_distribution"] else 0.0)),
            "executive_summary": (
                f"O evento sugere {format_fault_label_pt(candidate_fault)} com base em evidencias historicas."
                if not refusal_reason and effective_label != "evento_invalido"
                else "O evento foi bloqueado por validacao fisica antes de qualquer prescricao automatica."
                if effective_label == "evento_invalido"
                else f"O evento foi analisado, mas a resposta foi limitada: {refusal_reason}"
            ),
            "evidence_points": [
                history["summary"],
                (
                    f"Guardrail OOD: status={history.get('ood_status')} | score={history.get('ood_score')} "
                    f"| limite95={history.get('ood_threshold_95')} | limite99={history.get('ood_threshold_99')}"
                ),
                *[f"Validacao: {warning}" for warning in validation.get("warnings", [])],
            ],
            "recommended_actions": (
                ["Executar procedimento tecnico rastreado e validar inspecao local."]
                if documents and not refusal_reason and effective_label != "evento_invalido"
                else ["Validar instrumentacao e ampliar base documental antes de automatizar a prescricao."]
            ),
            "inspection_checklist": inspection_checklist,
            "risk_notes": [
                "Usar a recomendacao apenas dentro do contexto operacional semelhante.",
                "Requer validacao humana antes de intervencao fisica.",
                "A classificacao historica usa Mahalanobis + k-NN ponderado com deteccao OOD.",
            ],
            "refusal_reason": refusal_reason,
            "cited_documents": [] if effective_label == "evento_invalido" else [doc["title"] for doc in documents],
        }

    def _deterministic_freeform_response(
        self,
        user_text: str,
        documents: list[dict[str, Any]],
        document_summary: str,
        answer_type: str,
    ) -> dict[str, Any]:
        cited_documents = [doc["title"] for doc in documents]
        refusal_reason = ""
        lowered = user_text.lower()

        if answer_type == "document_query":
            if cited_documents:
                summary = "A base documental atual possui documentos tecnicos indexados para consulta do copiloto."
                evidence = [document_summary]
                actions = ["Se quiser, posso abrir por familia de falha, procedimento ou checklist tecnico."]
            else:
                summary = "No momento nao encontrei documentos indexados na base documental."
                evidence = [document_summary]
                actions = ["Execute a ingestao documental antes de consultar procedimentos ou lastro tecnico."]
                refusal_reason = "Sem documentos indexados para responder com lastro."
            return {
                "answer_type": answer_type,
                "executive_summary": summary,
                "evidence_points": evidence,
                "recommended_actions": actions,
                "cited_documents": cited_documents,
                "refusal_reason": refusal_reason,
            }

        if len(lowered.split()) <= 12:
            casual_response = self._casual_response(lowered)
            if casual_response is not None:
                return casual_response

        if ("usa rag" in lowered or "o que e rag" in lowered or "oque e rag" in lowered or lowered.strip() == "rag") and "rag_groq" not in lowered:
            return {
                "answer_type": answer_type,
                "executive_summary": "RAG e a combinacao de recuperacao de contexto com geracao de resposta pelo modelo.",
                "evidence_points": [
                    "No projeto, o RAG consulta a base documental chunkada antes da resposta final.",
                    "Isso ajuda o LLM a responder apoiado em trechos recuperados, e nao apenas por memoria generica.",
                ],
                "recommended_actions": [
                    "Se quiser, posso explicar o RAG do projeto em linguagem simples ou em termos mais tecnicos."
                ],
                "cited_documents": [],
                "refusal_reason": "",
            }

        if "fft" in lowered:
            return {
                "answer_type": answer_type,
                "executive_summary": "FFT e uma tecnica classica de analise em frequencia importante para manutencao preditiva, mas o pipeline atual do projeto nao calcula FFT diretamente.",
                "evidence_points": [
                    "O projeto atual trabalha sobre features estatisticas ja extraidas do dataset banner.csv.",
                    "Sem sinal bruto de vibracao, FFT entra como conceito tecnico explicavel, nao como etapa calculada no motor atual.",
                ],
                "recommended_actions": [
                    "Se quiser, posso explicar FFT conceitualmente ou contrastar com o motor atual baseado em features tabulares."
                ],
                "cited_documents": [],
                "refusal_reason": "",
            }

        if "llm" in lowered and ("orquestra" in lowered or "infer?ncia num?rica" in lowered or "inferencia numerica" in lowered):
            return {
                "answer_type": answer_type,
                "executive_summary": "No projeto atual, o LLM nao executa o motor numerico principal; ele orquestra o fluxo, resume evidencias e sintetiza a resposta final.",
                "evidence_points": [
                    "A busca historica principal continua em codigo Python auditavel com Mahalanobis + k-NN ponderado.",
                    "O LLM entra no roteamento, na explicacao e na resposta final em linguagem operacional.",
                ],
                "recommended_actions": [
                    "Se quiser, posso detalhar a separacao entre motor numerico, RAG documental e camada de sintese."
                ],
                "cited_documents": [],
                "refusal_reason": "",
            }

        if "mongodb" in lowered or "mongo" in lowered:
            if "vetorial" in lowered or "persist" in lowered or "persist?ncia" in lowered or "persistencia" in lowered:
                return {
                    "answer_type": answer_type,
                    "executive_summary": "Hoje o MongoDB atua principalmente como persistencia opcional; a busca vetorial principal ainda e calculada na aplicacao.",
                    "evidence_points": [
                        "Documentos, chunks, logs e conversas podem ser persistidos no Mongo.",
                        "A similaridade vetorial documental atual continua sendo calculada localmente em Python.",
                    ],
                    "recommended_actions": [
                        "Se quiser, posso explicar a diferenca entre o estado atual e uma migracao futura para Vector Search nativo."
                    ],
                    "cited_documents": [],
                    "refusal_reason": "",
                }

        if "banco vetorial nativo" in lowered or "vetorial nativo" in lowered or "atlas vector search" in lowered:
            return {
                "answer_type": answer_type,
                "executive_summary": "No estado atual, o projeto nao usa banco vetorial nativo; a vetorizacao e o ranking documental continuam locais na aplicacao.",
                "evidence_points": [
                    "Os chunks sao persistidos, mas a similaridade ainda e calculada em Python no pipeline atual.",
                    "MongoDB hoje funciona principalmente como persistencia opcional, nao como ANN vetorial nativo da busca principal.",
                ],
                "recommended_actions": [
                    "Se quiser, posso contrastar o estado atual com uma futura migracao para Vector Search nativo."
                ],
                "cited_documents": [],
                "refusal_reason": "",
            }

        if ("mongo" in lowered or "mongodb" in lowered) and ("cair" in lowered or "para" in lowered or "parar" in lowered):
            return {
                "answer_type": answer_type,
                "executive_summary": "Se o Mongo ficar indisponivel, o sistema nao precisa parar; o projeto usa fallback local para continuar operando.",
                "evidence_points": [
                    "Historico, documentos, conversas e logs podem continuar em armazenamento local quando o Mongo nao estiver ativo.",
                    "O Mongo atual e uma persistencia opcional, nao um ponto unico obrigatorio para o fluxo demonstrativo.",
                ],
                "recommended_actions": [
                    "Se quiser, posso detalhar como funciona o fallback local e o que muda quando o Mongo volta."
                ],
                "cited_documents": [],
                "refusal_reason": "",
            }

        if "cavita" in lowered and "hist" in lowered:
            return {
                "answer_type": answer_type,
                "executive_summary": "Sem historico rotulado de cavitacao, o sistema nao deveria inventar diagnostico numerico confiavel; no maximo, ele consegue apoiar por documento, se houver lastro textual.",
                "evidence_points": [
                    "A inferencia historica depende de ocorrencias comparaveis no dataset.",
                    "Sem historico e sem documento, a resposta correta e admitir limitacao e pedir mais base."
                ],
                "recommended_actions": [
                    "Adicionar documento tecnico e registrar ocorrencias historicas reais antes de automatizar prescricao para essa falha."
                ],
                "cited_documents": [],
                "refusal_reason": "",
            }

        if not documents:
            refusal_reason = "A pergunta foi entendida, mas a base documental recuperada nao sustenta resposta tecnica confiavel."
            return {
                "answer_type": answer_type,
                "executive_summary": "Consigo responder livremente, mas neste caso nao encontrei lastro suficiente na base para sustentar a orientacao tecnica.",
                "evidence_points": [document_summary],
                "recommended_actions": ["Refine a pergunta com o componente, sintoma, falha ou procedimento desejado."],
                "cited_documents": [],
                "refusal_reason": refusal_reason,
            }

        return {
            "answer_type": answer_type,
            "executive_summary": "A pergunta tecnica foi respondida com base nos trechos documentais mais aderentes recuperados.",
            "evidence_points": [document_summary, *[doc["chunk_text"][:220] for doc in documents[:3]]],
            "recommended_actions": ["Se quiser, posso converter isso em checklist, procedimento passo a passo ou resumo executivo."],
            "cited_documents": cited_documents,
            "refusal_reason": refusal_reason,
        }

    def _render_response_markdown(self, payload: dict[str, Any]) -> str:
        probable_fault = payload.get("probable_fault", "nao_informado")
        label_kind = get_label_kind(probable_fault)
        confidence = payload.get("confidence_pct", 0)
        summary = payload.get("executive_summary", "")
        evidence_points = payload.get("evidence_points") or []
        actions = payload.get("recommended_actions") or []
        checklist = payload.get("inspection_checklist") or []
        risks = payload.get("risk_notes") or []
        refusal_reason = payload.get("refusal_reason", "")
        cited_documents = payload.get("cited_documents") or []

        label_title = "Falha"
        heading = "### Diagnostico provavel"
        if probable_fault == "evento_invalido":
            label_title = "Status"
        elif label_kind == "state":
            label_title = "Estado operacional"

        lines = [
            heading,
            f"- **{label_title}:** `{probable_fault}`",
            f"- **Confianca:** `{confidence}%`",
            "",
            "### Resumo executivo",
            summary or "Sem resumo executivo gerado.",
            "",
            "### Prescricao recomendada",
        ]
        if actions:
            for item in actions:
                lines.append(f"- {item}")
        else:
            lines.append("- Sem prescricao automatica disponivel.")

        lines.extend(["", "### Rastreio utilizado"])
        if cited_documents:
            for doc in cited_documents:
                lines.append(f"- Documento: **{doc}**")
        else:
            lines.append("- Sem documento tecnico aderente recuperado.")

        lines.extend(["", "### Evidencias"])
        if evidence_points:
            for item in evidence_points:
                lines.append(f"- {item}")
        else:
            lines.append("- Sem evidencias detalhadas registradas.")

        if checklist:
            lines.extend(["", "### Checklist de inspecao"])
            for item in checklist:
                lines.append(f"- {item}")

        lines.extend(["", "### Riscos e limitacoes"])
        if risks:
            for item in risks:
                lines.append(f"- {item}")
        if refusal_reason:
            lines.append(f"- **Limitacao:** {refusal_reason}")
        if not risks and not refusal_reason:
            lines.append("- Sem restricoes adicionais destacadas.")
        return "\n".join(lines)

    def _stringify_evidence_item(self, item: Any) -> str:
        if isinstance(item, str):
            return item
        if isinstance(item, dict):
            title = item.get("title") or item.get("document_title")
            fault_family = item.get("fault_family")
            source_file = item.get("source_file")
            excerpt = item.get("excerpt") or item.get("chunk_text")
            score = item.get("score")
            pieces: list[str] = []
            if title:
                pieces.append(f"Documento: {title}")
            if fault_family:
                pieces.append(f"familia: {fault_family}")
            if score is not None:
                pieces.append(f"score: {score}")
            if source_file:
                pieces.append(f"origem: {source_file}")
            if excerpt:
                pieces.append(f"trecho: {str(excerpt)[:220]}")
            return " | ".join(pieces) if pieces else json.dumps(item, ensure_ascii=False)
        return str(item)

    def _stringify_action_item(self, item: Any) -> str:
        if isinstance(item, str):
            return item
        if isinstance(item, dict):
            action = item.get("action")
            description = item.get("description")
            if action and description:
                return f"{action}: {description}"
            if action:
                return str(action)
            if description:
                return str(description)
            return json.dumps(item, ensure_ascii=False)
        return str(item)

    def _normalize_cited_documents(self, payload: dict[str, Any], fallback_documents: list[dict[str, Any]]) -> None:
        raw_documents = payload.get("cited_documents") or []
        normalized: list[str] = []
        for item in raw_documents:
            if isinstance(item, str):
                normalized.append(item)
            elif isinstance(item, dict):
                title = item.get("title") or item.get("document_title")
                if title:
                    normalized.append(str(title))
        if not normalized and fallback_documents:
            normalized = [str(doc.get("title")) for doc in fallback_documents if doc.get("title")]
        seen: list[str] = []
        for item in normalized:
            if item and item not in seen:
                seen.append(item)
        payload["cited_documents"] = seen

    def _normalize_evidence_points(self, payload: dict[str, Any]) -> None:
        evidence_points = payload.get("evidence_points") or []
        payload["evidence_points"] = [self._stringify_evidence_item(item) for item in evidence_points]

    def _normalize_response_payload(self, payload: dict[str, Any], fallback_documents: list[dict[str, Any]]) -> dict[str, Any]:
        for key in ["recommended_actions", "inspection_checklist", "risk_notes", "evidence_points"]:
            value = payload.get(key)
            if isinstance(value, str):
                payload[key] = [value]
            elif value is None:
                payload[key] = []
        payload["recommended_actions"] = [self._stringify_action_item(item) for item in payload.get("recommended_actions", [])]
        payload["inspection_checklist"] = [self._stringify_action_item(item) for item in payload.get("inspection_checklist", [])]
        payload["risk_notes"] = [self._stringify_action_item(item) for item in payload.get("risk_notes", [])]
        self._normalize_cited_documents(payload, fallback_documents)
        self._normalize_evidence_points(payload)
        return payload

    def _render_freeform_markdown(self, payload: dict[str, Any]) -> str:
        summary = payload.get("executive_summary", "")
        evidence_points = payload.get("evidence_points") or []
        actions = payload.get("recommended_actions") or []
        cited_documents = payload.get("cited_documents") or []
        refusal_reason = payload.get("refusal_reason", "")
        answer_type = payload.get("answer_type", "freeform_question")

        if answer_type == "casual_chat":
            lines = [summary or "Posso conversar com voce por aqui tambem."]
            if actions:
                lines.extend(["", "Posso tambem:"])
                for item in actions[:2]:
                    lines.append(f"- {item}")
            return "\n".join(lines)

        if answer_type == "freeform_question":
            lines = [summary or "Sem resposta consolidada."]

            if actions:
                lines.extend(["", "Posso tambem:"])
                for item in actions[:3]:
                    lines.append(f"- {item}")

            if refusal_reason:
                lines.extend(["", f"Limitacao atual: {refusal_reason}"])

            return "\n".join(lines)

        lines = [
            "### Base documental",
            summary or "Sem resposta consolidada.",
            "",
            "### Evidencias e lastro",
        ]

        if cited_documents:
            for doc in cited_documents:
                lines.append(f"- Documento: **{doc}**")
        else:
            lines.append("- Nenhum documento aderente foi recuperado.")

        for item in evidence_points:
            if item not in cited_documents:
                lines.append(f"- {item}")

        lines.extend(["", "### Proximos passos"])
        if actions:
            for item in actions:
                lines.append(f"- {item}")
        else:
            lines.append("- Nenhuma acao adicional sugerida.")

        if refusal_reason:
            lines.extend(["", "### Limitacao", f"- {refusal_reason}"])
        return "\n".join(lines)

    def _infer_freeform(self, raw_input: str, model_name: str | None = None, answer_type: str = "freeform_question") -> dict[str, Any]:
        started = time.perf_counter()
        selected_model = model_name or SETTINGS.default_llm_model
        documents_catalog = DOCUMENT_SERVICE.list_documents()
        lowered_input = raw_input.lower()
        requested_fault_family = self._extract_document_focus(raw_input, documents_catalog)
        if answer_type == "document_query":
            document_result = DOCUMENT_SERVICE.search_chunks(query_text="catalogo documentos base documental", top_k=0)
            document_result.chunks = []
            if requested_fault_family:
                focused_documents = [
                    item for item in documents_catalog if canonicalize_fault_label(item.get("fault_family")) == requested_fault_family
                ]
                label_pt = "rolamentos" if requested_fault_family == "rolamento_inner" and "rolament" in lowered_input else format_fault_label_pt(requested_fault_family)
                document_result.summary = (
                    f"{len(focused_documents)} documento(s) encontrado(s) para {label_pt}."
                    if focused_documents
                    else f"Nao encontrei documento especifico para {label_pt}."
                )
            else:
                focused_documents = documents_catalog
                document_result.summary = f"{len(documents_catalog)} documento(s) indexado(s) na base documental."
        else:
            focused_documents = documents_catalog
            document_result = DOCUMENT_SERVICE.search_chunks(query_text=raw_input, top_k=SETTINGS.top_k_documents)

        response_payload = self._deterministic_freeform_response(
            user_text=raw_input,
            documents=document_result.chunks,
            document_summary=document_result.summary,
            answer_type=answer_type,
        )
        raw_llm_response = None
        usage = {}
        skip_llm = (
            response_payload.get("answer_type") == "casual_chat"
            or answer_type == "document_query"
            or not document_result.chunks
            or any(
            marker in lowered_input
            for marker in [
                "fft",
                "usa rag",
                "o que e rag",
                "oque e rag",
                "mongodb",
                "mongo",
                "banco vetorial",
                "vetorial nativo",
                "atlas vector search",
                "mongo cair",
                "se mongo cair",
                "inferencia numerica",
                "inferência numérica",
                "orquestra",
                "cavita",
            ]
            )
        )

        if answer_type == "document_query" and focused_documents:
            family_display = "rolamentos" if requested_fault_family == "rolamento_inner" and "rolament" in lowered_input else None
            document_lines = [
                f"{item.get('title')} | familia: {family_display or format_fault_label_pt(item.get('fault_family'))} | origem: {item.get('source_file')}"
                for item in focused_documents
            ]
            if requested_fault_family:
                focus_label = "rolamentos" if requested_fault_family == "rolamento_inner" and "rolament" in lowered_input else format_fault_label_pt(requested_fault_family)
                response_payload["executive_summary"] = (
                    f"Encontrei {len(focused_documents)} documento(s) relacionado(s) a {focus_label} na base documental."
                )
                response_payload["recommended_actions"] = [
                    "Se quiser, posso resumir esse procedimento ou listar os principais passos tecnicos desse documento."
                ]
            else:
                response_payload["executive_summary"] = (
                    f"A base documental atual possui {len(documents_catalog)} documentos indexados, "
                    "cada um associado a uma familia tecnica de falha ou procedimento."
                )
                response_payload["recommended_actions"] = [
                    "Se quiser, posso listar os documentos por familia de falha ou resumir cada procedimento."
                ]
            response_payload["executive_summary"] = (
                response_payload["executive_summary"]
            )
            response_payload["evidence_points"] = [document_result.summary, *document_lines]
            response_payload["cited_documents"] = [item.get("title") for item in focused_documents]
            response_payload["refusal_reason"] = ""

        if not skip_llm and self._provider in {"groq", "ollama"} and (self._provider != "groq" or self._groq_client is not None):
            context_payload = {
                "user_question": raw_input,
                "answer_type": answer_type,
                "indexed_documents": [
                    {
                        "title": item.get("title"),
                        "fault_family": item.get("fault_family"),
                        "source_file": item.get("source_file"),
                    }
                    for item in documents_catalog
                ],
                "document_summary": document_result.summary,
                "document_chunks": [
                    {
                        "title": item["title"],
                        "fault_family": item["fault_family"],
                        "score": item["score"],
                        "excerpt": item["chunk_text"][:450],
                    }
                    for item in document_result.chunks
                ],
            }
            try:
                raw_llm_response, usage = self._chat_complete(
                    model=selected_model,
                    temperature=0.2,
                    messages=[
                        {"role": "system", "content": FREEFORM_SYSTEM_PROMPT},
                        {"role": "user", "content": json.dumps(context_payload, ensure_ascii=False, default=str)},
                    ],
                )
                parsed = self._extract_json(raw_llm_response)
                if parsed:
                    response_payload.update(parsed)
            except Exception as exc:
                response_payload["evidence_points"] = [
                    *response_payload.get("evidence_points", []),
                    f"Fallback local usado apos falha no LLM: {exc}",
                ]

        response_payload = self._normalize_response_payload(response_payload, document_result.chunks)
        response_payload["response_markdown"] = self._render_freeform_markdown(response_payload)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        result = {
            "event": None,
            "validation": {"valid": True, "errors": [], "warnings": [], "mode": answer_type},
            "history": {
                "neighbors": [],
                "fault_distribution": [],
                "summary": "Consulta livre sem busca por vizinhos historicos.",
            },
            "documents": {
                "summary": document_result.summary,
                "chunks": document_result.chunks,
            },
            "agent_response": response_payload,
            "runtime": {
                "model": selected_model,
                "elapsed_ms": elapsed_ms,
                "timestamp": datetime.now(UTC).isoformat(),
                "usage": usage,
            },
            "raw_llm_response": raw_llm_response,
        }

        log_inference(
            {
                "model": selected_model,
                "elapsed_ms": elapsed_ms,
                "probable_fault": None,
                "confidence_pct": None,
                "refusal_reason": response_payload.get("refusal_reason"),
                "documents_count": len(document_result.chunks),
                "history_neighbors": 0,
                "usage": usage,
                "answer_type": answer_type,
            }
        )
        return result

    def infer_event(self, raw_input: str | dict[str, Any], model_name: str | None = None) -> dict[str, Any]:
        input_type = self._classify_input(raw_input)
        if input_type != "event_json":
            return self._infer_freeform(str(raw_input), model_name=model_name, answer_type=input_type)

        started = time.perf_counter()
        event = HISTORY_SERVICE.normalize_event(self._parse_event_input(raw_input))
        validation = HISTORY_SERVICE.validate_event(event)
        history_result = HISTORY_SERVICE.search_similar_events(event, top_k=SETTINGS.top_k_history)
        candidate_fault = history_result.candidate_fault or canonicalize_fault_label(event.get("fault"))
        input_fault_label = canonicalize_fault_label(event.get("fault"))
        input_fault_kind = get_label_kind(input_fault_label)

        if input_fault_label == "motor_desligado" and history_result.ood_status in {"ood", "fronteira"}:
            candidate_fault = input_fault_label

        if (
            get_label_kind(candidate_fault) == "state"
            and float(event.get("rpm") or 0) > 0
            and not (input_fault_label == "motor_desligado" and history_result.ood_status in {"ood", "fronteira"})
        ):
            non_state_distribution = [
                item for item in history_result.fault_distribution
                if get_label_kind(item.get("canonical_fault")) != "state"
            ]
            if non_state_distribution:
                candidate_fault = non_state_distribution[0]["canonical_fault"]

        if not validation.get("valid", True) or is_state_label(candidate_fault):
            document_result = DOCUMENT_SERVICE.search_chunks(query_text="", top_k=0)
            document_result.chunks = []
            document_result.summary = "Busca documental pulada para evitar tratar estado operacional ou evento invalido como falha prescritiva."
        else:
            document_query = self._event_query_text(event, candidate_fault)
            document_result = DOCUMENT_SERVICE.search_chunks(
                query_text=document_query,
                fault_family=candidate_fault,
                top_k=SETTINGS.top_k_documents,
            )

        response_payload = self._deterministic_fallback(
            event=event,
            validation=validation,
            history={
                "neighbors": history_result.neighbors,
                "fault_distribution": history_result.fault_distribution,
                "confidence_pct": history_result.confidence_pct,
                "candidate_fault": history_result.candidate_fault,
                "similarity_metric": history_result.similarity_metric,
                "ood_score": history_result.ood_score,
                "ood_threshold_95": history_result.ood_threshold_95,
                "ood_threshold_99": history_result.ood_threshold_99,
                "ood_flag": history_result.ood_flag,
                "ood_status": history_result.ood_status,
                "summary": history_result.summary,
            },
            documents=document_result.chunks,
            candidate_fault=candidate_fault,
        )
        raw_llm_response = None
        usage = {}
        selected_model = model_name or SETTINGS.default_llm_model

        if (self._provider in {"groq", "ollama"} and (self._provider != "groq" or self._groq_client is not None)) and validation.get("valid", True):
            context_payload = {
                "event": event,
                "validation": validation,
                "candidate_fault": candidate_fault,
                "history_summary": history_result.summary,
                "history_distribution": history_result.fault_distribution,
                "history_neighbors": history_result.neighbors,
                "history_similarity_metric": history_result.similarity_metric,
                "history_confidence_pct": history_result.confidence_pct,
                "ood": {
                    "flag": history_result.ood_flag,
                    "status": history_result.ood_status,
                    "score": history_result.ood_score,
                    "threshold_95": history_result.ood_threshold_95,
                    "threshold_99": history_result.ood_threshold_99,
                },
                "document_summary": document_result.summary,
                "document_chunks": [
                    {
                        "title": item["title"],
                        "fault_family": item["fault_family"],
                        "score": item["score"],
                        "excerpt": item["chunk_text"][:450],
                    }
                    for item in document_result.chunks
                ],
                "catalog": get_fault_catalog(),
            }
            try:
                raw_llm_response, usage = self._chat_complete(
                    model=selected_model,
                    temperature=0.1,
                    messages=[
                        {"role": "system", "content": f"{SYSTEM_PROMPT}\n\n{FEW_SHOT_PROMPT}"},
                        {"role": "user", "content": json.dumps(context_payload, ensure_ascii=False, default=str)},
                    ],
                )
                parsed = self._extract_json(raw_llm_response)
                if parsed:
                    response_payload.update(parsed)
            except Exception as exc:
                response_payload["risk_notes"].append(f"Fallback local usado apos falha no LLM: {exc}")

        response_payload = self._normalize_response_payload(response_payload, document_result.chunks)
        response_payload["response_markdown"] = self._render_response_markdown(response_payload)

        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        result = {
            "event": event,
            "validation": validation,
            "history": {
                "neighbors": history_result.neighbors,
                "fault_distribution": history_result.fault_distribution,
                "confidence_pct": history_result.confidence_pct,
                "candidate_fault": history_result.candidate_fault,
                "similarity_metric": history_result.similarity_metric,
                "ood_score": history_result.ood_score,
                "ood_threshold_95": history_result.ood_threshold_95,
                "ood_threshold_99": history_result.ood_threshold_99,
                "ood_flag": history_result.ood_flag,
                "ood_status": history_result.ood_status,
                "summary": history_result.summary,
            },
            "documents": {
                "summary": document_result.summary,
                "chunks": document_result.chunks,
            },
            "agent_response": response_payload,
            "runtime": {
                "model": selected_model,
                "elapsed_ms": elapsed_ms,
                "timestamp": datetime.now(UTC).isoformat(),
                "usage": usage,
            },
            "raw_llm_response": raw_llm_response,
        }

        log_inference(
            {
                "model": selected_model,
                "elapsed_ms": elapsed_ms,
                "probable_fault": response_payload.get("probable_fault"),
                "confidence_pct": response_payload.get("confidence_pct"),
                "refusal_reason": response_payload.get("refusal_reason"),
                "documents_count": len(document_result.chunks),
                "history_neighbors": len(history_result.neighbors),
                "usage": usage,
                "answer_type": "event_json",
            }
        )
        return result


AGENT = PrescriptiveAgent()
