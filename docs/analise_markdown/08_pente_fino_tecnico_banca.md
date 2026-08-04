# Pente Fino Tecnico Para Perguntas da Banca

Este documento foi feito para estudo rapido da implementacao atual. A ideia e responder perguntas como:

- o que foi usado no projeto;
- por que foi usado;
- onde isso aparece no codigo;
- como funciona na pratica;
- o que e MVP e o que ainda e evolucao futura.

Data de referencia desta analise: **4 de agosto de 2026**.

## Resumo executivo

O projeto implementa um **copiloto de manutencao prescritiva LLM-first** com interface em Streamlit. O chat e a superficie principal. O agente roteia a entrada entre:

- `event_json`: inferencia prescritiva com historico + documentos;
- `document_query`: perguntas sobre a base documental;
- `freeform_question`: duvidas tecnicas livres.

O sistema usa:

- **Groq API** como backend de LLM;
- **MongoDB** como persistencia opcional;
- **fallback local em JSON/JSONL** quando Mongo esta desabilitado;
- **HashingVectorizer + similaridade cosseno** para embeddings locais;
- **busca historica numerica** com `StandardScaler` + distancia Euclidiana;
- **taxonomia semantica de falhas** em YAML;
- **prompts externos** em pasta separada;
- **observabilidade** por logs de inferencia e benchmark.

## Visao curta para responder rapido

| Pergunta da banca | Resposta curta | Onde esta no codigo |
| --- | --- | --- |
| Qual e a interface principal? | Streamlit multipage com chat como tela central. | [Home.py](C:\Projetos\Manutencao-prescritiva-main\Home.py:112), [src/sidebar.py](C:\Projetos\Manutencao-prescritiva-main\src\sidebar.py:46) |
| O sistema usa LLM? | Sim. Usa Groq para roteamento de intencao e sintese da resposta. | [src/agent_service.py](C:\Projetos\Manutencao-prescritiva-main\src\agent_service.py:25), [src/agent_service.py](C:\Projetos\Manutencao-prescritiva-main\src\agent_service.py:457) |
| O sistema usa RAG? | Sim, um RAG documental local: extrai PDF, quebra em chunks, vetoriza e ranqueia por similaridade cosseno. | [src/document_service.py](C:\Projetos\Manutencao-prescritiva-main\src\document_service.py:43), [src/document_service.py](C:\Projetos\Manutencao-prescritiva-main\src\document_service.py:56), [src/document_service.py](C:\Projetos\Manutencao-prescritiva-main\src\document_service.py:161), [src/vectorization.py](C:\Projetos\Manutencao-prescritiva-main\src\vectorization.py:26) |
| Usa banco vetorial nativo? | Nao. Hoje os vetores sao gerados e comparados na aplicacao. Mongo guarda vetores e documentos, mas a busca vetorial nao usa Atlas Vector Search nativo. | [src/document_service.py](C:\Projetos\Manutencao-prescritiva-main\src\document_service.py:97), [src/document_service.py](C:\Projetos\Manutencao-prescritiva-main\src\document_service.py:167), [src/mongo_store.py](C:\Projetos\Manutencao-prescritiva-main\src\mongo_store.py:72) |
| Usa MongoDB Atlas? | Pode usar. O projeto conecta via `pymongo` se `MONGO_ENABLED=true` e houver connection string. | [src/settings.py](C:\Projetos\Manutencao-prescritiva-main\src\settings.py:46), [src/mongo_store.py](C:\Projetos\Manutencao-prescritiva-main\src\mongo_store.py:33), [src/mongo_store.py](C:\Projetos\Manutencao-prescritiva-main\src\mongo_store.py:36) |
| Como e feita a busca historica? | Normaliza features, aplica `StandardScaler`, calcula distancia Euclidiana para achar vizinhos mais proximos. | [src/history_service.py](C:\Projetos\Manutencao-prescritiva-main\src\history_service.py:86), [src/history_service.py](C:\Projetos\Manutencao-prescritiva-main\src\history_service.py:127), [src/history_service.py](C:\Projetos\Manutencao-prescritiva-main\src\history_service.py:140) |
| Tem validacao fisica do evento? | Sim. Temperatura, RPM e vibracao passam por guardrails simples antes da prescricao. | [src/history_service.py](C:\Projetos\Manutencao-prescritiva-main\src\history_service.py:98) |
| Tem semantica de falhas? | Sim. Rotulos livres sao canonizados por um lexico YAML. | [config/fault_lexicon.yaml](C:\Projetos\Manutencao-prescritiva-main\config\fault_lexicon.yaml), [src/fault_semantics.py](C:\Projetos\Manutencao-prescritiva-main\src\fault_semantics.py:52) |
| Os prompts sao editaveis fora do codigo? | Sim. O projeto carrega prompts da pasta `prompts/`. | [src/prompt_loader.py](C:\Projetos\Manutencao-prescritiva-main\src\prompt_loader.py:10), [prompts](C:\Projetos\Manutencao-prescritiva-main\prompts) |
| Tem logs e rastreabilidade? | Sim. Inference e benchmark sao logados em Mongo e em `jsonl`. | [src/observability.py](C:\Projetos\Manutencao-prescritiva-main\src\observability.py:21), [src/observability.py](C:\Projetos\Manutencao-prescritiva-main\src\observability.py:32) |

## Stack usada

| Categoria | Tecnologia | Como entra no projeto | Onde esta |
| --- | --- | --- | --- |
| Frontend | Streamlit | Chat, sidebar, paginas, graficos e tabelas | [Home.py](C:\Projetos\Manutencao-prescritiva-main\Home.py:112), [pages](C:\Projetos\Manutencao-prescritiva-main\pages) |
| LLM | Groq API | Roteamento de intencao e resposta final | [src/agent_service.py](C:\Projetos\Manutencao-prescritiva-main\src\agent_service.py:25), [src/agent_service.py](C:\Projetos\Manutencao-prescritiva-main\src\agent_service.py:377), [src/agent_service.py](C:\Projetos\Manutencao-prescritiva-main\src\agent_service.py:491) |
| Persistencia | MongoDB via `pymongo` | Guarda historico, documentos, chunks, logs, benchmarks e conversas | [src/mongo_store.py](C:\Projetos\Manutencao-prescritiva-main\src\mongo_store.py:17) |
| Fallback | JSON e JSONL local | Continua funcionando sem Mongo | [src/mongo_store.py](C:\Projetos\Manutencao-prescritiva-main\src\mongo_store.py:14), [src/observability.py](C:\Projetos\Manutencao-prescritiva-main\src\observability.py:12), [src/conversation_store.py](C:\Projetos\Manutencao-prescritiva-main\src\conversation_store.py:12) |
| Vetorizacao | `HashingVectorizer` | Gera embeddings locais sem chamar API externa | [src/vectorization.py](C:\Projetos\Manutencao-prescritiva-main\src\vectorization.py:11) |
| Similaridade textual | Cosseno | Rankeia chunks documentais | [src/vectorization.py](C:\Projetos\Manutencao-prescritiva-main\src\vectorization.py:38), [src/document_service.py](C:\Projetos\Manutencao-prescritiva-main\src\document_service.py:171) |
| Similaridade numerica | `StandardScaler` + distancia Euclidiana | Busca vizinhos no historico | [src/history_service.py](C:\Projetos\Manutencao-prescritiva-main\src\history_service.py:86), [src/history_service.py](C:\Projetos\Manutencao-prescritiva-main\src\history_service.py:140) |
| PDFs | `pypdf` | Extrai texto dos documentos | [src/document_service.py](C:\Projetos\Manutencao-prescritiva-main\src\document_service.py:43) |
| Dados tabulares | `pandas`, `numpy` | Limpeza, carga, distancias e benchmark | [src/history_service.py](C:\Projetos\Manutencao-prescritiva-main\src\history_service.py:9), [src/benchmark_service.py](C:\Projetos\Manutencao-prescritiva-main\src\benchmark_service.py:8) |
| Configuracao | `.env` + `dotenv` | Modelos, Mongo e parametros | [src/settings.py](C:\Projetos\Manutencao-prescritiva-main\src\settings.py:17), [.env.example](C:\Projetos\Manutencao-prescritiva-main\.env.example) |
| Semantica | YAML | Lexico de falhas e aliases | [config/fault_lexicon.yaml](C:\Projetos\Manutencao-prescritiva-main\config\fault_lexicon.yaml), [src/fault_semantics.py](C:\Projetos\Manutencao-prescritiva-main\src\fault_semantics.py:30) |

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
| `src/history_service.py` | Historico operacional | "faz validacao e busca de similares numericos" |
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
| Canonizacao da falha | Gera `canonical_fault` | [src/history_service.py](C:\Projetos\Manutencao-prescritiva-main\src\history_service.py:58) |
| Escalonamento | `StandardScaler` sobre medianas | [src/history_service.py](C:\Projetos\Manutencao-prescritiva-main\src\history_service.py:86) |
| Corte por RPM | Prioriza mesma rotacao quando houver amostra suficiente | [src/history_service.py](C:\Projetos\Manutencao-prescritiva-main\src\history_service.py:132) |
| Distancia | `np.linalg.norm` entre evento e historico | [src/history_service.py](C:\Projetos\Manutencao-prescritiva-main\src\history_service.py:140) |
| Resultado | Vizinho + distribuicao de falhas | [src/history_service.py](C:\Projetos\Manutencao-prescritiva-main\src\history_service.py:143), [src/history_service.py](C:\Projetos\Manutencao-prescritiva-main\src\history_service.py:158) |

### Resposta curta para a banca

- "A busca historica e um mecanismo de similaridade numerica. As features do evento sao padronizadas com `StandardScaler` e comparadas ao historico via distancia Euclidiana."

### Ponto forte

- simples;
- auditavel;
- barato para MVP;
- faz sentido para dados tabulares numericos.

### Ponto fraco

- nao e um modelo temporal;
- nao considera sequencia de janelas no tempo;
- ainda nao trata aprendizado online nem proximidade mais sofisticada.

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

## Melhor forma de apresentar tecnicamente

Se precisar resumir em 30 segundos:

> "O projeto e um copiloto de manutencao prescritiva LLM-first em Streamlit. O chat e a interface principal. O agente decide se a entrada e evento ou pergunta livre. Para evento, ele valida o payload, busca similares no historico com `StandardScaler` e distancia Euclidiana, consulta trechos documentais via chunks vetorizados com `HashingVectorizer` e similaridade cosseno, e sintetiza a resposta com Groq. MongoDB funciona como persistencia opcional, com fallback local para garantir portabilidade. Os prompts e a taxonomia de falhas ficam externos ao codigo para facilitar governanca e evolucao." 

## Leitura complementar no proprio repositorio

- [README.md](C:\Projetos\Manutencao-prescritiva-main\README.md)
- [docs/analise_markdown/04_confronto_literatura_web.md](C:\Projetos\Manutencao-prescritiva-main\docs\analise_markdown\04_confronto_literatura_web.md)
- [docs/analise_markdown/05_plano_mvp_streamlit_llm_first.md](C:\Projetos\Manutencao-prescritiva-main\docs\analise_markdown\05_plano_mvp_streamlit_llm_first.md)
