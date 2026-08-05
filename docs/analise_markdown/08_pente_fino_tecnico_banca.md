# Pente Fino Tecnico Para Perguntas da Banca

Este documento foi feito para estudo rapido da implementacao atual. A ideia e responder perguntas como:

- o que foi usado no projeto;
- por que foi usado;
- onde isso aparece no codigo;
- como funciona na pratica;
- o que e MVP e o que ainda e evolucao futura.

Data de referencia desta analise: **5 de agosto de 2026**.

## Resumo executivo

O projeto implementa um **copiloto de manutencao prescritiva LLM-first** com interface em Streamlit. O chat e a superficie principal. O agente roteia a entrada entre:

- `event_json`: inferencia prescritiva com historico + documentos;
- `document_query`: perguntas sobre a base documental;
- `freeform_question`: duvidas tecnicas livres.

O sistema usa:

- **abstracao de provedor de LLM** com suporte a **Groq API** e **Ollama local**;
- **MongoDB** como persistencia opcional;
- **fallback local em JSON/JSONL** quando Mongo esta desabilitado;
- **HashingVectorizer + similaridade cosseno** para embeddings locais;
- **busca historica numerica** com `StandardScaler` + `Mahalanobis` + `k-NN` ponderado + `OOD`;
- **taxonomia semantica de falhas** em YAML;
- **prompts externos** em pasta separada;
- **observabilidade** por logs de inferencia e benchmark.

## Visao curta para responder rapido

| Pergunta da banca | Resposta curta | Onde esta no codigo |
| --- | --- | --- |
| Qual e a interface principal? | Streamlit multipage com chat como tela central. | [Home.py](C:\Projetos\Manutencao-prescritiva-main\Home.py:112), [src/sidebar.py](C:\Projetos\Manutencao-prescritiva-main\src\sidebar.py:46) |
| O sistema usa LLM? | Sim. Usa camada abstrata para Groq ou Ollama no roteamento de intencao e na sintese da resposta. | [src/agent_service.py](C:\Projetos\Manutencao-prescritiva-main\src\agent_service.py:25), [src/agent_service.py](C:\Projetos\Manutencao-prescritiva-main\src\agent_service.py:457) |
| O sistema usa RAG? | Sim, um RAG documental local: extrai PDF, quebra em chunks, vetoriza e ranqueia por similaridade cosseno. | [src/document_service.py](C:\Projetos\Manutencao-prescritiva-main\src\document_service.py:43), [src/document_service.py](C:\Projetos\Manutencao-prescritiva-main\src\document_service.py:56), [src/document_service.py](C:\Projetos\Manutencao-prescritiva-main\src\document_service.py:161), [src/vectorization.py](C:\Projetos\Manutencao-prescritiva-main\src\vectorization.py:26) |
| Usa banco vetorial nativo? | Nao. Hoje os vetores sao gerados e comparados na aplicacao. Mongo guarda vetores e documentos, mas a busca vetorial nao usa Atlas Vector Search nativo. | [src/document_service.py](C:\Projetos\Manutencao-prescritiva-main\src\document_service.py:97), [src/document_service.py](C:\Projetos\Manutencao-prescritiva-main\src\document_service.py:167), [src/mongo_store.py](C:\Projetos\Manutencao-prescritiva-main\src\mongo_store.py:72) |
| Usa MongoDB Atlas? | Pode usar. O projeto conecta via `pymongo` se `MONGO_ENABLED=true` e houver connection string. | [src/settings.py](C:\Projetos\Manutencao-prescritiva-main\src\settings.py:46), [src/mongo_store.py](C:\Projetos\Manutencao-prescritiva-main\src\mongo_store.py:33), [src/mongo_store.py](C:\Projetos\Manutencao-prescritiva-main\src\mongo_store.py:36) |
| Como e feita a busca historica? | Normaliza features, aplica `StandardScaler`, usa distancia de Mahalanobis, voto ponderado e guardrail OOD. | [src/history_service.py](C:\Projetos\Manutencao-prescritiva-main\src\history_service.py:132), [src/history_service.py](C:\Projetos\Manutencao-prescritiva-main\src\history_service.py:138), [src/history_service.py](C:\Projetos\Manutencao-prescritiva-main\src\history_service.py:195) |
| Tem validacao fisica do evento? | Sim. Temperatura, RPM e vibracao passam por guardrails simples antes da prescricao. | [src/history_service.py](C:\Projetos\Manutencao-prescritiva-main\src\history_service.py:98) |
| Tem semantica de falhas? | Sim. Rotulos livres sao canonizados por um lexico YAML. | [config/fault_lexicon.yaml](C:\Projetos\Manutencao-prescritiva-main\config\fault_lexicon.yaml), [src/fault_semantics.py](C:\Projetos\Manutencao-prescritiva-main\src\fault_semantics.py:52) |
| Os prompts sao editaveis fora do codigo? | Sim. O projeto carrega prompts da pasta `prompts/`. | [src/prompt_loader.py](C:\Projetos\Manutencao-prescritiva-main\src\prompt_loader.py:10), [prompts](C:\Projetos\Manutencao-prescritiva-main\prompts) |
| Tem logs e rastreabilidade? | Sim. Inference e benchmark sao logados em Mongo e em `jsonl`. | [src/observability.py](C:\Projetos\Manutencao-prescritiva-main\src\observability.py:21), [src/observability.py](C:\Projetos\Manutencao-prescritiva-main\src\observability.py:32) |

## Stack usada

| Biblioteca ou tecnologia | Papel no projeto | Onde aparece |
| --- | --- | --- |
| `Python` | linguagem base que organiza toda a aplicacao | [Home.py](C:\Projetos\Manutencao-prescritiva-main\Home.py), [src](C:\Projetos\Manutencao-prescritiva-main\src) |
| `Streamlit` | interface principal com chat, sidebar, paginas e visualizacao | [Home.py](C:\Projetos\Manutencao-prescritiva-main\Home.py:112), [pages](C:\Projetos\Manutencao-prescritiva-main\pages) |
| `Groq API` e `Ollama` | camada de execucao de LLM por meio de um provider abstrato | [src/agent_service.py](C:\Projetos\Manutencao-prescritiva-main\src\agent_service.py:25), [src/settings.py](C:\Projetos\Manutencao-prescritiva-main\src\settings.py:17) |
| `pandas` e `numpy` | base de manipulacao tabular, carga, benchmark e calculo numerico | [src/history_service.py](C:\Projetos\Manutencao-prescritiva-main\src\history_service.py:9), [src/benchmark_service.py](C:\Projetos\Manutencao-prescritiva-main\src\benchmark_service.py:8) |
| `scikit-learn` | escalonamento numerico e vetorizacao textual local | [src/history_service.py](C:\Projetos\Manutencao-prescritiva-main\src\history_service.py:12), [src/vectorization.py](C:\Projetos\Manutencao-prescritiva-main\src\vectorization.py:11) |
| `StandardScaler` + `Mahalanobis` + `k-NN` ponderado + `OOD` | motor historico numerico auditavel para busca de similares e classificacao | [src/history_service.py](C:\Projetos\Manutencao-prescritiva-main\src\history_service.py:132), [src/history_service.py](C:\Projetos\Manutencao-prescritiva-main\src\history_service.py:195) |
| `HashingVectorizer` + similaridade cosseno | RAG documental local sem dependencia de embedding externo | [src/vectorization.py](C:\Projetos\Manutencao-prescritiva-main\src\vectorization.py:11), [src/document_service.py](C:\Projetos\Manutencao-prescritiva-main\src\document_service.py:171) |
| `pypdf` | leitura e extracao de texto dos PDFs usados na base documental | [src/document_service.py](C:\Projetos\Manutencao-prescritiva-main\src\document_service.py:43) |
| `MongoDB` via `pymongo` | persistencia opcional de historico, documentos, chunks, logs, benchmarks e conversas | [src/mongo_store.py](C:\Projetos\Manutencao-prescritiva-main\src\mongo_store.py:17) |
| `JSON` e `JSONL` local | fallback quando Mongo esta desabilitado ou indisponivel | [src/mongo_store.py](C:\Projetos\Manutencao-prescritiva-main\src\mongo_store.py:14), [src/observability.py](C:\Projetos\Manutencao-prescritiva-main\src\observability.py:12), [src/conversation_store.py](C:\Projetos\Manutencao-prescritiva-main\src\conversation_store.py:12) |
| `.env` + `dotenv` | configuracao de provider, modelo, Mongo e parametros operacionais | [src/settings.py](C:\Projetos\Manutencao-prescritiva-main\src\settings.py:17), [.env.example](C:\Projetos\Manutencao-prescritiva-main\.env.example) |
| `YAML` | taxonomia semantica de falhas e aliases fora do core Python | [config/fault_lexicon.yaml](C:\Projetos\Manutencao-prescritiva-main\config\fault_lexicon.yaml), [src/fault_semantics.py](C:\Projetos\Manutencao-prescritiva-main\src\fault_semantics.py:30) |

## Arquitetura da aplicacao

### Fluxo macro

1. O usuario interage pelo chat em [Home.py](C:\Projetos\Manutencao-prescritiva-main\Home.py:112).
2. A entrada e enviada ao agente em [src/agent_service.py](C:\Projetos\Manutencao-prescritiva-main\src\agent_service.py:457).
3. O agente classifica a intencao em [src/agent_service.py](C:\Projetos\Manutencao-prescritiva-main\src\agent_service.py:49).
4. Se for evento, o sistema valida, busca historico e consulta documentos.
5. Se for consulta livre, usa a busca documental livre e o LLM responde em tom tecnico.
6. A resposta e renderizada em markdown no chat.
7. A execucao e logada em observabilidade.

### Modulos principais

| Modulo | Papel | Onde responder se perguntarem |
| --- | --- | --- |
| `Home.py` | Chat principal, streaming e experiencia do usuario | "a aplicacao abre no chat e o resto sao superficies auxiliares" |
| `src/agent_service.py` | Motor cognitivo do copiloto | "decide o fluxo e sintetiza a resposta final" |
| `src/history_service.py` | Historico operacional | "faz validacao, busca Mahalanobis ponderada e deteccao OOD" |
| `src/document_service.py` | Base documental | "ingere PDFs, gera chunks e recupera trechos" |
| `src/vectorization.py` | Embeddings locais | "gera vetores locais para RAG sem dependencia externa" |
| `src/mongo_store.py` | Persistencia | "encapsula Mongo e fallback local" |
| `src/fault_semantics.py` | Camada semantica | "padroniza a linguagem das falhas" |
| `src/observability.py` | Logs | "garante rastreabilidade da inferencia" |
| `src/benchmark_service.py` | Benchmark | "mede comportamento por modelo e cenario" |
| `src/conversation_store.py` | Conversas | "persiste historico de chat e recarga pela sidebar" |

## O que exatamente o agente faz

### 1. Classificacao de intencao

O projeto nao trata toda mensagem como evento. Isso foi implementado para evitar erro de JSON em perguntas livres.

| Caso | Comportamento | Onde esta |
| --- | --- | --- |
| Dicionario Python ou JSON detectado | `event_json` | [src/agent_service.py](C:\Projetos\Manutencao-prescritiva-main\src\agent_service.py:49) |
| Pergunta sobre documentos | `document_query` | [src/agent_service.py](C:\Projetos\Manutencao-prescritiva-main\src\agent_service.py:56) |
| Demais perguntas tecnicas | `freeform_question` | [src/agent_service.py](C:\Projetos\Manutencao-prescritiva-main\src\agent_service.py:77) |

Resposta de banca:

- "O agente primeiro decide se a entrada e um evento ou uma consulta livre. Isso evita forcar parse JSON em toda mensagem."

### 2. Fluxo para evento

O fluxo prescritivo principal acontece em [src/agent_service.py](C:\Projetos\Manutencao-prescritiva-main\src\agent_service.py:457).

Sequencia:

1. Parse do evento em [src/agent_service.py](C:\Projetos\Manutencao-prescritiva-main\src\agent_service.py:84).
2. Normalizacao das features em [src/history_service.py](C:\Projetos\Manutencao-prescritiva-main\src\history_service.py:91).
3. Validacao fisica em [src/history_service.py](C:\Projetos\Manutencao-prescritiva-main\src\history_service.py:98).
4. Busca de similares em [src/history_service.py](C:\Projetos\Manutencao-prescritiva-main\src\history_service.py:127).
5. Montagem da consulta documental em [src/agent_service.py](C:\Projetos\Manutencao-prescritiva-main\src\agent_service.py:102).
6. Busca de chunks em [src/document_service.py](C:\Projetos\Manutencao-prescritiva-main\src\document_service.py:161).
7. Montagem do contexto para o LLM em [src/agent_service.py](C:\Projetos\Manutencao-prescritiva-main\src\agent_service.py:476).
8. Renderizacao final em markdown em [src/agent_service.py](C:\Projetos\Manutencao-prescritiva-main\src\agent_service.py:204).

### 3. Fluxo para pergunta livre

O fluxo livre esta em [src/agent_service.py](C:\Projetos\Manutencao-prescritiva-main\src\agent_service.py:347).

Ele:

- recupera o catalogo de documentos;
- consulta chunks com a pergunta do usuario;
- pede ao LLM uma resposta tecnica apoiada em lastro;
- ou usa fallback deterministico quando necessario.

Resposta de banca:

- "Nao usamos o LLM apenas como chatbot aberto. Ele trabalha em cima de contexto recuperado e com formato esperado de saida."

## RAG documental: como funciona

### O que foi implementado

Foi implementado um RAG documental local com as seguintes etapas:

1. leitura dos PDFs base;
2. extracao de texto;
3. chunking;
4. vetorizacao local;
5. armazenamento dos chunks com vetor;
6. consulta por similaridade.

### Onde cada etapa esta

| Etapa | Como funciona | Codigo |
| --- | --- | --- |
| Fonte dos documentos | Lista fixa de 6 PDFs e familia de falha | [src/document_service.py](C:\Projetos\Manutencao-prescritiva-main\src\document_service.py:18) |
| Extracao de texto | `PdfReader` le pagina a pagina | [src/document_service.py](C:\Projetos\Manutencao-prescritiva-main\src\document_service.py:43) |
| Fallback de texto | Se PDF extrair pouco texto, usa texto de apoio | [src/document_service.py](C:\Projetos\Manutencao-prescritiva-main\src\document_service.py:31), [src/document_service.py](C:\Projetos\Manutencao-prescritiva-main\src\document_service.py:50) |
| Chunking | Quebra por sentencas com overlap | [src/document_service.py](C:\Projetos\Manutencao-prescritiva-main\src\document_service.py:56) |
| Dedupe de chunks | Usa `md5` para evitar chunk duplicado | [src/document_service.py](C:\Projetos\Manutencao-prescritiva-main\src\document_service.py:74) |
| Vetores | `embed_many` cria vetores densos normalizados | [src/document_service.py](C:\Projetos\Manutencao-prescritiva-main\src\document_service.py:97), [src/vectorization.py](C:\Projetos\Manutencao-prescritiva-main\src\vectorization.py:32) |
| Busca | Similaridade cosseno sobre vetores de chunks | [src/document_service.py](C:\Projetos\Manutencao-prescritiva-main\src\document_service.py:171), [src/vectorization.py](C:\Projetos\Manutencao-prescritiva-main\src\vectorization.py:38) |
| Boost semantico | Soma `0.12` se `fault_family` bater | [src/document_service.py](C:\Projetos\Manutencao-prescritiva-main\src\document_service.py:176) |

### Pergunta importante: "Usou banco vetorial?"

Resposta correta e segura:

- "Usei **vetorizacao** e **busca vetorial**, mas nao um banco vetorial dedicado ou o **Atlas Vector Search nativo**."
- "No estado atual, os vetores sao calculados localmente com `HashingVectorizer`, persistidos junto com os chunks no MongoDB e a similaridade e calculada na propria aplicacao."

Ou seja:

- **Sim**, existe busca vetorial no projeto.
- **Nao**, ela nao depende hoje de indice vetorial nativo do Atlas.
- **MongoDB** esta sendo usado como **camada de persistencia** dos documentos e vetores, nao como mecanismo nativo de ANN.

### Como isso funcionaria no Atlas se evoluir

Se a banca perguntar "como migraria para Atlas Vector Search?", a resposta pode ser:

1. manter a ingestao documental e os chunks;
2. trocar o vetor local por embedding de modelo compativel;
3. criar indice vetorial no Atlas sobre o campo `vector`;
4. substituir a etapa de ranking local por consulta `$vectorSearch`;
5. manter o resto do pipeline igual.

### Diferenca entre o estado atual e um Atlas vetorial nativo

| Item | Estado atual | Evolucao futura no Atlas |
| --- | --- | --- |
| Geração de vetor | Local com `HashingVectorizer` | Embedding model dedicado |
| Armazenamento | MongoDB ou JSON local | MongoDB Atlas |
| Busca vetorial | Calculada em Python | `$vectorSearch` no Atlas |
| Escalabilidade | Boa para MVP/local | Melhor para escala maior |
| Dependencia externa | Baixa | Maior, mas mais robusta |

## Busca historica: como funciona

### Ideia

O historico operacional e tratado como uma base numerica para achar eventos parecidos.

### Etapas

| Etapa | Como funciona | Codigo |
| --- | --- | --- |
| Definicao das features | Lista de 12 grandezas numericas | [src/history_service.py](C:\Projetos\Manutencao-prescritiva-main\src\history_service.py:19) |
| Leitura do dataset | `banner.csv` via pandas | [src/history_service.py](C:\Projetos\Manutencao-prescritiva-main\src\history_service.py:55) |
| Canonizacao da falha | Gera `canonical_fault` | [src/history_service.py](C:\Projetos\Manutencao-prescritiva-main\src\history_service.py:59) |
| Escalonamento | `StandardScaler` sobre medianas | [src/history_service.py](C:\Projetos\Manutencao-prescritiva-main\src\history_service.py:97) |
| Corte por RPM | Prioriza mesma rotacao quando houver amostra suficiente | [src/history_service.py](C:\Projetos\Manutencao-prescritiva-main\src\history_service.py:185) |
| Distancia | Mahalanobis com pseudo-inversa da covariancia | [src/history_service.py](C:\Projetos\Manutencao-prescritiva-main\src\history_service.py:138), [src/history_service.py](C:\Projetos\Manutencao-prescritiva-main\src\history_service.py:141) |
| Voto | `k-NN` ponderado por distancia | [src/history_service.py](C:\Projetos\Manutencao-prescritiva-main\src\history_service.py:160), [src/history_service.py](C:\Projetos\Manutencao-prescritiva-main\src\history_service.py:195) |
| OOD | Limiar estatistico por qui-quadrado aproximado | [src/history_service.py](C:\Projetos\Manutencao-prescritiva-main\src\history_service.py:145), [src/history_service.py](C:\Projetos\Manutencao-prescritiva-main\src\history_service.py:199) |
| Resultado | Vizinho + distribuicao ponderada + sinal OOD | [src/history_service.py](C:\Projetos\Manutencao-prescritiva-main\src\history_service.py:214), [src/history_service.py](C:\Projetos\Manutencao-prescritiva-main\src\history_service.py:235) |

### Resposta curta para a banca

- "A busca historica e um mecanismo de similaridade numerica robusta. As features do evento sao padronizadas com `StandardScaler`, comparadas ao historico por distancia de Mahalanobis, classificadas por `k-NN` ponderado e protegidas por um guardrail OOD."

### Ponto forte

- robusto a correlacao entre variaveis;
- auditavel;
- barato para MVP;
- faz sentido para dados tabulares numericos;
- sabe sinalizar quando o evento saiu do envelope estatistico esperado.

### Ponto fraco

- nao e um modelo temporal;
- nao considera sequencia de janelas no tempo;
- ainda nao trata aprendizado online;
- o OOD atual e estatistico, nao semantico.

## Validacao fisica do evento

Foi implementado um conjunto de guardrails simples em [src/history_service.py](C:\Projetos\Manutencao-prescritiva-main\src\history_service.py:98).

Validacoes atuais:

- temperatura plausivel entre `-40` e `220`;
- RPM plausivel entre `0` e `10000`;
- vibracoes nao negativas;
- alerta quando `rpm == 0` com vibracao relevante.

Resposta de banca:

- "Antes de prescrever, o sistema faz validacao fisica minima para nao aceitar leitura absurdamente incoerente."

## Camada semantica de falhas

### O que faz

Padroniza rotulos como:

- erros de digitacao;
- aliases;
- variacoes de nome;
- distincao entre `state` e `fault`.

### Onde esta

| Componente | Funcao |
| --- | --- |
| [config/fault_lexicon.yaml](C:\Projetos\Manutencao-prescritiva-main\config\fault_lexicon.yaml) | Fonte da taxonomia |
| [src/fault_semantics.py](C:\Projetos\Manutencao-prescritiva-main\src\fault_semantics.py:30) | Carrega YAML |
| [src/fault_semantics.py](C:\Projetos\Manutencao-prescritiva-main\src\fault_semantics.py:52) | Canoniza rotulo |
| [src/fault_semantics.py](C:\Projetos\Manutencao-prescritiva-main\src\fault_semantics.py:97) | Gera label amigavel |
| [src/fault_semantics.py](C:\Projetos\Manutencao-prescritiva-main\src\fault_semantics.py:108) | Distingue estado de falha |

### Resposta curta

- "A camada semantica garante que o sistema nao dependa de um unico spelling do rotulo de falha."

## MongoDB, Atlas e fallback local

### O que o projeto faz hoje

O projeto encapsula persistencia em [src/mongo_store.py](C:\Projetos\Manutencao-prescritiva-main\src\mongo_store.py:17).

Colecoes logicas:

- `history`
- `documents`
- `document_chunks`
- `logs`
- `benchmarks`
- `conversations`

Mapeamento em [src/mongo_store.py](C:\Projetos\Manutencao-prescritiva-main\src\mongo_store.py:61).

### Quando o Mongo e usado

O Mongo so e ativado se:

- `MONGO_ENABLED=true`
- `MONGO_CONNECTION_STRING` existir

Isso esta em [src/mongo_store.py](C:\Projetos\Manutencao-prescritiva-main\src\mongo_store.py:33).

### Quando cai para local

Se o Mongo nao estiver ativo, o sistema usa:

- `data/app_state/local_store.json`
- `data/app_state/conversations.json`
- `data/app_state/logs/*.jsonl`

### Pergunta classica: "Por que usar Mongo aqui?"

Resposta boa:

- documentos e chunks sao naturalmente documentos JSON;
- logs e conversas tambem;
- o modelo de dados e flexivel;
- Atlas permitiria escalar para consultas centralizadas;
- para MVP, o fallback local garante portabilidade.

### Pergunta classica: "Usou Atlas Vector Search?"

Resposta segura:

- "Nao ainda. O Atlas esta sendo usado como persistencia opcional. A parte vetorial ainda esta implementada no lado da aplicacao."
- "Se a arquitetura evoluir, o caminho natural e manter os vetores no Mongo e migrar o ranking para indice vetorial nativo com `$vectorSearch`."

## Observabilidade e rastreabilidade

### O que fica logado

Cada inferencia registra:

- `model`
- `elapsed_ms`
- `probable_fault`
- `confidence_pct`
- `refusal_reason`
- `documents_count`
- `history_neighbors`
- `usage`

Isso e feito em [src/observability.py](C:\Projetos\Manutencao-prescritiva-main\src\observability.py:21).

Benchmarks sao logados em [src/observability.py](C:\Projetos\Manutencao-prescritiva-main\src\observability.py:32).

### Por que isso importa

- medir custo e latencia;
- auditar prescricao;
- acompanhar recusas;
- comparar modelos.

## Benchmark

O benchmark foi pensado para comparar modelos Groq em cenarios do proprio dataset.

| Etapa | Onde esta |
| --- | --- |
| Gera cenarios base | [src/benchmark_service.py](C:\Projetos\Manutencao-prescritiva-main\src\benchmark_service.py:23) |
| Executa cenarios por modelo | [src/benchmark_service.py](C:\Projetos\Manutencao-prescritiva-main\src\benchmark_service.py:59) |
| Loga resultado | [src/benchmark_service.py](C:\Projetos\Manutencao-prescritiva-main\src\benchmark_service.py:82) |

Resposta de banca:

- "O benchmark nao mede so texto bonito. Ele mede latencia, documentos recuperados, confianca e recusas por modelo."

### Resultado consolidado mais recente

Na rodada completa executada em **5 de agosto de 2026** com **50 amostras balanceadas**, os principais resultados foram:

| Tecnica | Provider | Modelo | Accuracy | Macro-F1 |
| --- | --- | --- | --- | --- |
| `mahalanobis_weighted_knn` | local | deterministic | `0.92` | `0.9195` |
| `euclidean_knn` | local | deterministic | `0.80` | `0.8027` |
| `cosine_knn` | local | deterministic | `0.80` | `0.7942` |
| `llm_vector_rag_groq` | groq | `llama-3.1-8b-instant` | `0.74` | `0.7443` |
| `llm_vector_rag_ollama_small` | ollama | `qwen2.5-coder:7b` | `0.68` | `0.6900` |
| `centroid_euclidean` | local | deterministic | `0.48` | `0.4654` |
| `text_vector_vote` | local | deterministic | `0.44` | `0.4248` |

Leitura para a banca:

- "O melhor baseline geral foi o `Mahalanobis + k-NN` ponderado, o que reforca que a parte numerica ainda carrega o sinal mais forte desta base."
- "O `llm_vector_rag` com Groq ficou competitivo como camada de orquestracao e sintese, mas nao superou o motor numerico."
- "O teste com Ollama local mostrou queda de qualidade, mas preservou a viabilidade do modo edge com modelo menor."

### Sweep Groq por modelo

Tambem foi executado um sweep adicional no Groq, em **5 de agosto de 2026**, para comparar diferentes modelos no mesmo pipeline `llm_vector_rag`.

| Modelo Groq | Amostras validas | Accuracy | Macro-F1 | Observacao |
| --- | --- | --- | --- | --- |
| `llama-3.1-8b-instant` | `50` | `0.74` | `0.7443` | melhor resultado no pipeline atual |
| `llama-3.3-70b-versatile` | `50` | `0.72` | `0.7245` | muito proximo do melhor |
| `openai/gpt-oss-120b` | `39` | `0.6923` | `0.6922` | execucao parcial por limite de TPM |
| `openai/gpt-oss-20b` | `50` | `0.54` | `0.4939` | abaixo dos dois Llama |
| `qwen/qwen3.6-27b` | `50` | `0.02` | `0.0303` | baixa aderencia ao prompt atual |

Resposta curta:

- "No sweep mais recente, o melhor modelo Groq para esse caso foi o `llama-3.1-8b-instant`, nao um modelo maior."
- "Isso sugere que o gargalo atual esta mais na representacao do evento, no prompt e na recuperacao do que apenas no tamanho do modelo."

## Literatura contra usar LLM como motor numerico direto

Duas referencias fortes e recentes para sustentar a decisao arquitetural:

1. Boye e Moell, **Large Language Models and Mathematical Reasoning Failures**.
   Data no arXiv: **17 de fevereiro de 2025**, revisado em **21 de fevereiro de 2025**.
   Link: https://arxiv.org/abs/2502.11574
   Leitura util para a banca:
   O artigo mostra que, mesmo em modelos fortes, persistem erros de aritmetica, planejamento e raciocinio em varias etapas, inclusive com respostas finais aparentemente corretas mas baseadas em logica falha.

2. Li et al., **Exposing Numeracy Gaps: A Benchmark to Evaluate Fundamental Numerical Abilities in Large Language Models**.
   Publicacao: **Findings of ACL 2025**, julho de **2025**.
   Link: https://aclanthology.org/2025.findings-acl.1026/
   Leitura util para a banca:
   O artigo mostra fraquezas persistentes em aritmetica, comparacao de magnitude, recuperacao numerica e raciocinio em varias etapas, defendendo que LLMs ainda falham justamente nas capacidades numericas basicas exigidas em cenarios reais.

Resposta curta recomendada:

- "A literatura recente reforca que LLM e excelente para sintese, explicacao e RAG, mas ainda nao e a melhor opcao para inferencia numerica bruta e auditavel."
- "Por isso a arquitetura separa motor simbolico numerico e motor neural semantico."

## Prompts e estilo agentic

### O que foi feito

Os prompts foram externalizados para facilitar manutencao e demonstrar engenharia de prompt.

| Prompt | Papel | Onde esta |
| --- | --- | --- |
| `maintenance_event_system.md` | System prompt para evento | [prompts/maintenance_event_system.md](C:\Projetos\Manutencao-prescritiva-main\prompts\maintenance_event_system.md) |
| `freeform_system.md` | Prompt para duvida tecnica/documental | [prompts/freeform_system.md](C:\Projetos\Manutencao-prescritiva-main\prompts\freeform_system.md) |
| `input_router.md` | Prompt de roteamento de intencao | [prompts/input_router.md](C:\Projetos\Manutencao-prescritiva-main\prompts\input_router.md) |
| `prescriptive_response_few_shot.md` | Few-shot do comportamento esperado | [prompts/prescriptive_response_few_shot.md](C:\Projetos\Manutencao-prescritiva-main\prompts\prescriptive_response_few_shot.md) |
| Loader | Le prompts da pasta | [src/prompt_loader.py](C:\Projetos\Manutencao-prescritiva-main\src\prompt_loader.py:10) |

### Pergunta classica: "Isso e ReAct?"

Resposta honesta:

- "Hoje nao e um ReAct completo com planner iterativo e tool calling explicito."
- "O projeto esta mais proximo de um fluxo agentic leve com roteamento de intencao e consulta de ferramentas internas."
- "A arquitetura ja foi preparada para evoluir para planner mais explicito."

## Interface e UX

### O que foi priorizado

- chat como tela principal;
- sidebar persistente;
- nova conversa;
- historico de conversas;
- dashboard e paginas auxiliares.

### Onde isso esta

| Componente | Onde esta |
| --- | --- |
| Chat principal | [Home.py](C:\Projetos\Manutencao-prescritiva-main\Home.py:112) |
| Persistencia do chat | [Home.py](C:\Projetos\Manutencao-prescritiva-main\Home.py:43), [src/conversation_store.py](C:\Projetos\Manutencao-prescritiva-main\src\conversation_store.py:43) |
| Sidebar compartilhada | [src/sidebar.py](C:\Projetos\Manutencao-prescritiva-main\src\sidebar.py:46) |
| Navegacao lateral | [src/sidebar.py](C:\Projetos\Manutencao-prescritiva-main\src\sidebar.py:63) |
| Historico de conversa | [src/sidebar.py](C:\Projetos\Manutencao-prescritiva-main\src\sidebar.py:89) |
| Barra de envio inferior | [Home.py](C:\Projetos\Manutencao-prescritiva-main\Home.py:190) |

## Estilo de codigo adotado

### Principios

| Principio | Como aparece |
| --- | --- |
| Separacao de responsabilidades | cada servico cuida de uma coisa: agente, historico, documentos, persistencia, UI |
| Funcoes pequenas e nomeadas | ex.: `_classify_input`, `search_chunks`, `validate_event` |
| Configuracao fora do core | `.env`, prompts e YAML |
| Fallback explicito | Mongo opcional e fallback local |
| Auditabilidade | logs, markdown estruturado e ultimas evidencias no chat |

### Exemplos no codigo

| Conceito | Exemplo |
| --- | --- |
| Encapsulamento de persistencia | [src/mongo_store.py](C:\Projetos\Manutencao-prescritiva-main\src\mongo_store.py:17) |
| Encapsulamento do agente | [src/agent_service.py](C:\Projetos\Manutencao-prescritiva-main\src\agent_service.py:25) |
| Semantica desacoplada | [src/fault_semantics.py](C:\Projetos\Manutencao-prescritiva-main\src\fault_semantics.py:52) |
| Config centralizada | [src/settings.py](C:\Projetos\Manutencao-prescritiva-main\src\settings.py:26) |
| Prompt fora do codigo | [src/prompt_loader.py](C:\Projetos\Manutencao-prescritiva-main\src\prompt_loader.py:10) |

## O que esta no `.gitignore` e por que

`.gitignore` atual: [.gitignore](C:\Projetos\Manutencao-prescritiva-main\.gitignore)

| Item ignorado | Por que foi ignorado |
| --- | --- |
| `__pycache__/`, `*.py[cod]` | artefatos de compilacao Python |
| `.venv/`, `venv/`, `env/` | ambiente virtual local |
| `.env`, `.env.local` | segredos e configuracao local |
| `data/app_state/` | estado transitório local, logs e store de fallback |
| `*.jsonl` | logs locais de inferencia/benchmark |
| `docs/11 - prova prtica.docx`, `docs/11 - prova prtica.pdf` | arquivos da prova mantidos fora do versionamento |
| `scripts/generate_eda_artifacts.py` | script auxiliar que nao precisa entrar no commit principal |

Referencias de implementacao: [.gitignore](C:\Projetos\Manutencao-prescritiva-main\.gitignore:12), [.gitignore](C:\Projetos\Manutencao-prescritiva-main\.gitignore:18), [.gitignore](C:\Projetos\Manutencao-prescritiva-main\.gitignore:26), [.gitignore](C:\Projetos\Manutencao-prescritiva-main\.gitignore:30)

## Perguntas dificeis e respostas recomendadas

### "Por que nao usar KNN puro como motor principal?"

Resposta:

- "Porque a proposta da prova pede uma solucao centrada em LLM/copiloto na estacao de trabalho."
- "O numerico continua existindo, mas como ferramenta auxiliar chamada pelo agente, nao como produto final isolado."

### "Entao o LLM esta fazendo a parte numerica?"

Resposta:

- "Nao. A parte numerica principal de similaridade historica ainda e calculada por codigo Python auditavel."
- "O LLM orquestra, resume, recusa quando falta lastro e entrega a resposta final em linguagem operacional."

### "O sistema esta pronto para producao?"

Resposta:

- "Nao ainda. Esta em estado de MVP demonstravel."
- "Ja possui base de arquitetura, rastreabilidade, fallback e benchmark, mas ainda cabem melhorias em qualidade de RAG, guardrails e busca vetorial nativa."

### "Se o Mongo cair, o sistema para?"

Resposta:

- "Nao. O projeto cai para persistencia local."

### "Como o sistema sabe que um documento e de uma falha?"

Resposta:

- "Hoje isso vem de metadado explicito em `DOC_SOURCES` e do campo `fault_family` aplicado a cada documento e chunk."

### "FFT esta implementado no calculo?"

Resposta segura:

- "Nao. FFT pode aparecer como conceito em resposta tecnica baseada em documento, mas o projeto atual nao calcula FFT no pipeline numerico."
- "O pipeline usa features que ja vieram no dataset e comparacao historica em cima dessas features."

## Limites atuais que voce pode admitir sem se comprometer

| Tema | Estado atual | Como responder |
| --- | --- | --- |
| Atlas Vector Search | Nao implementado nativamente | "persistencia em Mongo, busca vetorial local na aplicacao" |
| ANN escalavel | Nao | "MVP local com ranking em memoria" |
| Serie temporal longa | Nao | "comparacao evento a evento" |
| Planner ReAct completo | Nao | "agentic leve com roteamento e ferramentas internas" |
| FFT calculada no pipeline | Nao | "conceito pode ser explicado, mas nao e calculo do motor atual" |
| Aprendizado online | Nao | "dataset e base documental sao ingeridos, nao ha treino incremental" |

### Pergunta potencial da banca: "Entao por que usar Mongo agora?"

Resposta recomendada:

- "Porque ele ja organiza a persistencia operacional do MVP: historico, documentos, chunks, logs e conversas."
- "Ou seja, o Mongo ja faz sentido hoje como camada de dados, mesmo antes da ativacao do motor vetorial nativo."
- "Se houver evolucao futura, a mesma base pode receber indice vetorial e consulta por `$vectorSearch`, reduzindo o ranking manual em Python."

## Melhor forma de apresentar tecnicamente

Se precisar resumir em 30 segundos:

> "O projeto e um copiloto de manutencao prescritiva LLM-first em Streamlit. O chat e a interface principal. O agente decide se a entrada e evento ou pergunta livre. Para evento, ele valida o payload, busca similares no historico com `StandardScaler`, distancia de Mahalanobis, `k-NN` ponderado e guardrail OOD, consulta trechos documentais via chunks vetorizados com `HashingVectorizer` e similaridade cosseno, e sintetiza a resposta por uma camada abstrata que pode usar Groq ou Ollama local. MongoDB funciona como persistencia opcional, com fallback local para garantir portabilidade. Os prompts e a taxonomia de falhas ficam externos ao codigo para facilitar governanca e evolucao." 

## Leitura complementar no proprio repositorio

- [README.md](C:\Projetos\Manutencao-prescritiva-main\README.md)
- [docs/analise_markdown/04_confronto_literatura_web.md](C:\Projetos\Manutencao-prescritiva-main\docs\analise_markdown\04_confronto_literatura_web.md)
- [docs/analise_markdown/05_plano_mvp_streamlit_llm_first.md](C:\Projetos\Manutencao-prescritiva-main\docs\analise_markdown\05_plano_mvp_streamlit_llm_first.md)
- [docs/analise_markdown/09_benchmark_full_inferencia_2026-08-05.md](C:\Projetos\Manutencao-prescritiva-main\docs\analise_markdown\09_benchmark_full_inferencia_2026-08-05.md)
- [docs/analise_markdown/10_benchmark_groq_model_sweep_2026-08-05.md](C:\Projetos\Manutencao-prescritiva-main\docs\analise_markdown\10_benchmark_groq_model_sweep_2026-08-05.md)
