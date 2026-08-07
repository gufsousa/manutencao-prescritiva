# Roadmap Agentic e Escalabilidade

Data de referencia: **7 de agosto de 2026**.

## Objetivo

Traduzir os achados da matriz de `115` testes e da literatura recente em um roadmap pratico para evoluir o copiloto em tres eixos:

1. melhora do comportamento agentic;
2. ferramentas internas relevantes para um fluxo mais autonomo;
3. escalabilidade de recuperacao documental e historico operacional.

## Leitura do estado atual

O estado atual do projeto ja mostra um desenho funcional e coerente para MVP:

- roteamento entre `event_json`, `document_query` e `freeform_question`;
- motor numerico auditavel para similaridade historica;
- RAG documental local;
- guardrails fisicos e `OOD`;
- fallback deterministico quando o lastro e fraco.

Pelo resultado mais recente da suite:

- matriz ampliada: `115/115 PASS`;
- consultas sobre rolamentos passaram a citar o documento correto;
- `FFT`, `LLM` e `cavitacao sem historico` deixaram de herdar documentos irrelevantes;
- casos com `OOD` e `features` faltantes passaram a expor confianca calibrada.

Mesmo assim, os testes ainda sugerem tres gargalos reais:

1. algumas perguntas livres conceituais ainda dependem demais de regras pontuais;
2. cenarios `OOD` extremos ainda podem recuperar documentos, mesmo quando a resposta final e corretamente limitada;
3. a recuperacao documental continua simples demais para crescer com seguranca.

## O que a literatura apoia

### 1. ReAct como estrategia de ferramenta, nao como fim em si

O artigo **ReAct: Synergizing Reasoning and Acting in Language Models**, publicado no arXiv em **6 de outubro de 2022**, propoe intercalar raciocinio e acoes externas para reduzir alucinacao e melhorar interpretabilidade:

- https://arxiv.org/abs/2210.03629

Leitura aplicada ao projeto:

- faz sentido quando houver de fato multiplas ferramentas;
- nao faz sentido virar um planner pesado para perguntas simples e deterministicas.

### 2. Plan-and-Solve como evolucao mais leve

**Plan-and-Solve Prompting**, publicado no arXiv em **6 de maio de 2023**, mostra ganho ao decompor tarefas em subtarefas sem exigir um agente completo:

- https://arxiv.org/abs/2305.04091

Leitura aplicada:

- para o projeto atual, um `planner leve` e mais aderente do que um `ReAct` completo;
- principalmente para perguntas compostas como:
  - conceito + documento;
  - limite do sistema + implicacao pratica;
  - pergunta livre + checklist final.

### 3. Self-Refine e Reflexion para melhorar resposta, nao classificar falha

**Self-Refine**, publicado em **30 de marco de 2023**:

- https://arxiv.org/abs/2303.17651

**Reflexion**, publicado em **20 de marco de 2023**:

- https://arxiv.org/abs/2303.11366

Leitura aplicada:

- sao interessantes para refinar texto, tom, clareza e citacao;
- nao sao o melhor caminho para substituir o motor historico numerico.

### 4. RAG robusto depende de retrieval melhor, nao so de mais LLM

**Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks**, publicado em **22 de maio de 2020**:

- https://arxiv.org/abs/2005.11401

**Dense Passage Retrieval**, publicado em **10 de abril de 2020**:

- https://arxiv.org/abs/2004.04906

**Corrective Retrieval-Augmented Generation (CRAG)**, publicado em **29 de janeiro de 2024**:

- https://arxiv.org/abs/2401.15884

**Self-RAG**, publicado em **17 de outubro de 2023**:

- https://arxiv.org/abs/2310.11511

Leitura aplicada:

- o gargalo do seu projeto hoje esta mais em `retrieve -> filtrar -> reranquear -> decidir se responde` do que em gerar texto;
- CRAG e Self-RAG apoiam bem uma camada de avaliacao da qualidade da recuperacao antes da resposta final.

### 5. Escalabilidade vetorial pede ANN e retrieval hibrido

**HNSW**, publicado em **30 de marco de 2016**:

- https://arxiv.org/abs/1603.09320

**From BM25 to Corrective RAG: Benchmarking Retrieval Strategies for Text-and-Table Documents**, publicado em **2 de abril de 2026**:

- https://arxiv.org/abs/2604.01733

Leitura aplicada:

- dense retrieval sozinho nao e sempre dominante;
- busca hibrida `sparse + dense + reranking` e o caminho mais seguro;
- para crescer, o projeto deve sair de ranking total em memoria para ANN com filtro e reranking.

### 6. Escalabilidade do lado numerico pede janela, deteccao de anomalia e trilha temporal

**Deep Learning for Time Series Anomaly Detection: A Survey**, publicado em **2022**:

- https://arxiv.org/abs/2211.05244

**Foundation Models for Time Series: A Survey**, publicado em **2025**:

- https://arxiv.org/abs/2504.04011

**Predicting machine failures from multivariate time series**, publicado em **2024**:

- https://arxiv.org/abs/2402.17804

Leitura aplicada:

- se houver sinal bruto ou janelas temporais, o caminho mais promissor para escalar o motor numerico nao e `LLM sobre texto`, e sim:
  - anomalia multivariada;
  - classificacao temporal;
  - embeddings de serie temporal;
  - memoria deslizante e drift.

## Ferramentas internas relevantes para um agente mais autonomo

Se o projeto evoluir para um fluxo mais agentic, as ferramentas internas mais relevantes seriam:

### 1. `router_tool`

Papel:

- decidir se a entrada e:
  - evento;
  - pergunta documental;
  - pergunta composta;
  - conversa casual;
  - pergunta arquitetural.

Estado atual:

- ja existe de forma embutida no `agent_service`.

Evolucao:

- transformar em ferramenta explicita com justificativa curta de roteamento.

### 2. `history_tool`

Papel:

- validar evento;
- medir `OOD`;
- contar `features` faltantes;
- recuperar vizinhos;
- devolver confianca crua e calibrada.

Estado atual:

- ja existe de forma forte e auditavel.

Evolucao:

- expor tambem:
  - `abstain_reason`;
  - `missing_feature_policy`;
  - `coverage_score`.

### 3. `document_catalog_tool`

Papel:

- responder perguntas catalograficas diretamente do indice de documentos, sem depender de chunk retrieval.

Motivacao:

- varios casos de QA melhoram quando o sistema usa catalogo inteiro e nao similaridade de chunk.

### 4. `document_retrieval_tool`

Papel:

- recuperar chunks com:
  - busca densa;
  - busca lexical;
  - filtro por `fault_family`;
  - reranking final.

Evolucao:

- primeiro `hybrid retrieval`;
- depois `retrieval grader`.

### 5. `retrieval_grader_tool`

Papel:

- avaliar se a recuperacao ficou boa o suficiente para responder.

Inspiracao:

- CRAG;
- Self-RAG.

Saida esperada:

- `retrieval_ok`;
- `low_evidence`;
- `needs_query_rewrite`;
- `answer_catalog_only`.

### 6. `response_refiner_tool`

Papel:

- refinar resposta final em tom, clareza, citacao e concisao.

Inspiracao:

- Self-Refine.

Uso recomendado:

- apenas no final;
- nunca para mudar o diagnostico numerico.

### 7. `observability_review_tool`

Papel:

- olhar logs recentes;
- detectar padroes de erro;
- sugerir novas regras ou testes.

Inspiracao:

- Reflexion, mas com memoria operacional auditavel.

## Roadmap proposto

### Fase 1. Curto prazo

Objetivo:

- endurecer seguranca sem aumentar muito a complexidade.

Acoes:

1. separar `document_catalog_tool` de `document_retrieval_tool`;
2. bloquear citacao documental em cenarios `OOD` severos quando o documento nao tiver relacao clara com a hipotese historica;
3. adicionar `retrieval_grader` simples por heuristica:
   - score minimo;
   - diversidade de documentos;
   - consistencia com `fault_family`;
4. registrar em log:
   - `retrieval_quality`;
   - `abstained_due_to_low_evidence`;
   - `used_catalog_path`;
5. ampliar a suite de QA para cobrir:
   - pergunta catalografica;
   - pergunta conceitual;
   - pergunta arquitetural;
   - evento com baixa cobertura de features;
   - evento com OOD severo.

Risco:

- pouco risco arquitetural;
- ganho alto em honestidade de resposta.

### Fase 2. Medio prazo

Objetivo:

- sair do RAG local simples para RAG mais robusto.

Acoes:

1. migrar de `HashingVectorizer` puro para retrieval hibrido:
   - BM25 ou equivalente;
   - embedding denso;
   - fusao de ranking;
2. introduzir reranking leve;
3. testar ANN com indice vetorial nativo ou motor dedicado;
4. avaliar query decomposition para perguntas compostas;
5. avaliar `planner leve` em vez de `ReAct` completo.

Risco:

- medio;
- mais componentes para medir e manter.

### Fase 3. Escalabilidade documental

Objetivo:

- suportar muito mais documentos e chunks sem perda grande de latencia.

Acoes:

1. trocar ranking exaustivo por ANN;
2. adotar filtros de metadado antes da busca vetorial;
3. medir:
   - recall@k;
   - MRR;
   - latencia p50/p95;
   - taxa de citacao correta;
4. separar ingestao, indexacao e serving;
5. versionar embeddings e chunks.

Boas opcoes arquiteturais:

- Atlas Vector Search;
- FAISS;
- motor ANN dedicado com busca hibrida;
- Mongo como persistencia + outro indice de retrieval, se necessario.

### Fase 4. Escalabilidade numerica

Objetivo:

- deixar de operar so com evento pontual e passar a olhar contexto temporal.

Acoes:

1. introduzir janelas temporais;
2. medir drift e mudanca de regime;
3. testar detector de anomalia multivariado;
4. separar:
   - classificacao de falha conhecida;
   - deteccao de anomalia nova;
5. avaliar modelos de serie temporal apenas se houver sinal e rotulo adequados.

Leitura importante:

- para maquinas rotativas, se vier sinal bruto, o ganho mais plausivel costuma estar mais em engenharia de sinal, janelas e modelos temporais do que em textualizar tudo para LLM.

### Fase 5. Agente mais autonomo

Objetivo:

- aumentar autonomia sem perder auditabilidade.

Acoes:

1. manter o diagnostico numerico como ferramenta fechada;
2. permitir ao agente escolher entre:
   - catalogo;
   - retrieval;
   - historico;
   - resposta curta;
3. adicionar um `planner leve`:
   - entender pergunta;
   - escolher ferramenta;
   - validar evidencia;
   - responder;
4. so depois testar `ReAct` completo, se houver varias ferramentas reais e ganho medido.

## Recomendacao objetiva para este projeto

Se a pergunta for "vale migrar agora para um agente autonomo tipo ReAct?", a resposta mais honesta e:

- **nao ainda como prioridade principal**.

O que vale mais a pena agora:

1. retrieval hibrido;
2. grader de evidencia;
3. separacao catalogo vs chunk retrieval;
4. regra de abstencao mais forte em `OOD` e baixa cobertura de features;
5. logs melhores para aprender com erro operacional.

Depois disso, sim, faz sentido testar um fluxo agentic mais explicito.

## Roadmap resumido em uma frase

Primeiro melhorar `retrieve + grade + abstain`, depois escalar `index + ANN + hybrid`, e so entao sofisticar o agente.

## Referencias

- ReAct: https://arxiv.org/abs/2210.03629
- Plan-and-Solve: https://arxiv.org/abs/2305.04091
- Self-Refine: https://arxiv.org/abs/2303.17651
- Reflexion: https://arxiv.org/abs/2303.11366
- DPR: https://arxiv.org/abs/2004.04906
- RAG: https://arxiv.org/abs/2005.11401
- Self-RAG: https://arxiv.org/abs/2310.11511
- CRAG: https://arxiv.org/abs/2401.15884
- HNSW: https://arxiv.org/abs/1603.09320
- Benchmark retrieval 2026: https://arxiv.org/abs/2604.01733
- TS anomaly survey: https://arxiv.org/abs/2211.05244
- Foundation models for time series survey: https://arxiv.org/abs/2504.04011
- Predicting machine failures from multivariate time series: https://arxiv.org/abs/2402.17804
