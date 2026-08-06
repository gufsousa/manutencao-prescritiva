# Apresentacao 10 Minutos - CRISP-DM

Data de referencia: **6 de agosto de 2026**.

Objetivo desta apresentacao:

- apresentar o projeto de forma curta, tecnica e defensavel;
- usar o **CRISP-DM** como estrutura narrativa;
- mostrar que a arquitetura final foi guiada por **literatura + restricoes do case + benchmark**;
- deixar claro que o projeto e um **copiloto prescritivo demonstravel**, e nao um substituto total da engenharia de manutencao.

---

## Slide 1 - Titulo

**Copiloto de Manutencao Prescritiva LLM-First com Nucleo Numerico Auditavel**

Subtitulo sugerido:

**Projeto em Streamlit com historico operacional, RAG documental local, benchmark e deploy em Streamlit Cloud**

Fala sugerida:

> Este projeto implementa um copiloto de manutencao prescritiva para maquinas rotativas. A interface principal e um chat em Streamlit, mas o nucleo da decisao foi mantido numerico e auditavel. O LLM entra como camada de orquestracao, explicacao e prescricao textual, apoiado por base documental e por busca historica.

---

## Slide 2 - Business Understanding

### Problema de negocio

- receber eventos de sensores em JSON;
- consultar historico operacional com rotulos de falha;
- consultar documentos tecnicos;
- devolver uma resposta prescritiva com lastro e limitacoes explicitas.

### Restricoes do case

- execucao em estacao de trabalho com foco **edge/on-premise**;
- limite operacional de **16 GB de VRAM**;
- necessidade de evitar alucinacao;
- dado principal fornecido como **features estatisticas ja extraidas**, e nao como sinal bruto.

### Revisao da literatura usada nesta etapa

A revisao de literatura sugeriu duas direcoes complementares:

1. para o **nucleo diagnostico**, a literatura do dominio continua sustentando com mais forca abordagens de **inferencia estatistica e similaridade numerica**, como:
   - `k-NN`
   - distancias como `Mahalanobis`
   - deteccao de anomalia / OOD
   - representacoes fisicas e espectrais quando houver sinal bruto

2. para a **camada de interface cognitiva**, a literatura mais recente sustenta o uso de:
   - **LLM**
   - **RAG**
   - copilotos tecnicos baseados em documento
   - orquestracao de contexto com limitacao de alucinacao

### Decisao de negocio adotada

- usar **motor numerico** para o diagnostico principal;
- usar **RAG documental** para recuperar lastro tecnico;
- usar **LLM** para sintetizar resposta, explicar e prescrever com linguagem operacional.

Fala sugerida:

> A revisao da literatura nao apontou o LLM como melhor motor para inferencia numerica de vibracao. O que ela sustenta melhor e uma arquitetura hibrida: diagnostico numerico ou estatistico no nucleo, e LLM com RAG na camada de explicacao, interface e apoio documental. Foi essa linha que guiou o projeto.

---

## Slide 3 - Data Understanding

### O que o case entregou

- `banner.csv` com historico operacional;
- colunas numericas como:
  - RMS
  - pico
  - curtose
  - fator de crista
  - RPM
  - temperatura
- coluna `fault` com mistura de:
  - falhas reais
  - estados operacionais
  - ruidos semanticos

### Leitura critica do dado

- o case **nao trouxe sinal bruto**;
- portanto, o projeto **nao implementa FFT diretamente no pipeline**;
- isso desloca o problema de engenharia vibracional profunda para um problema de:
  - similaridade historica
  - validacao fisica
  - semantica de falhas
  - recuperacao documental

Fala sugerida:

> O ponto mais importante aqui e que o dado ja veio resumido. Entao a solucao precisava respeitar o que existia de fato no dataset, sem fingir uma analise espectral completa que o material fornecido nao permitia fazer.

---

## Slide 4 - Data Preparation

### Preparacao do historico

- leitura do `banner.csv`;
- conversao de tipos;
- canonizacao semantica da coluna `fault`;
- separacao entre `state` e `fault`;
- guardrails fisicos basicos no evento.

### Preparacao documental

- ingestao de PDFs;
- extracao de texto com `pypdf`;
- chunking;
- vetorizacao local;
- armazenamento em persistencia opcional.

### Preparacao da persistencia

- `MongoDB` opcional;
- fallback local em `JSON/JSONL`;
- historico persistido usado com cuidado para nao enviesar diagnostico parcial.

Fala sugerida:

> A etapa de preparacao foi decisiva para manter a aderencia. Ela organizou o historico, tratou a semantica de falhas e estruturou a base documental para que o LLM nao respondesse solto, mas sempre apoiado por contexto recuperado.

---

## Slide 5 - Modeling

### Arquitetura final

**Camada 1 - Motor numerico**

- `StandardScaler`
- distancia de `Mahalanobis`
- `k-NN` ponderado
- guardrail `OOD`

**Camada 2 - RAG documental**

- `HashingVectorizer`
- similaridade cosseno
- busca local por chunks

**Camada 3 - LLM**

- roteamento de intencao
- sintese da resposta
- organizacao das evidencias e proximos passos

### Por que essa arquitetura

- respeita o dado disponivel;
- reduz dependencia de inferencia numerica pelo LLM;
- mantem lastro documental;
- permite rodar em ambiente local ou hibrido.

Fala sugerida:

> Em vez de delegar tudo ao LLM, a arquitetura separa responsabilidades: o numerico diagnostica, o RAG recupera, e o LLM explica. Essa foi a principal decisao neuro-simbolica do projeto.

---

## Slide 6 - Evaluation

### Resultado de benchmark

Pontos principais:

- `mahalanobis_weighted_knn` foi o melhor baseline geral;
- `llm_vector_rag_groq` foi competitivo como camada de orquestracao e explicacao;
- o pipeline com LLM **nao superou** o motor numerico no nucleo diagnostico.

### Resultado resumido

- `mahalanobis_weighted_knn`: `accuracy=0.92`, `macro_f1=0.9195`
- `llm_vector_rag_groq`: `accuracy=0.74`, `macro_f1=0.7443`
- `llm_vector_rag_ollama_small`: `accuracy=0.68`, `macro_f1=0.6900`

### Qualidade funcional

- matriz de QA ampliada: `100/100 PASS`
- smoke test: aprovado
- compilacao: aprovada

### Graficos para mostrar neste slide

- `02_macro_f1_por_tecnica.html`
- `03_latencia_media_por_tecnica.html`
- `04_recall_por_familia.html`

Fala sugerida:

> O benchmark confirmou a hipotese inicial: o LLM agrega bastante como camada de explicacao e copiloto, mas o motor numerico ainda e o componente mais forte para o diagnostico nesta base.

---

## Slide 7 - Deployment

### O que foi entregue

- aplicacao multipage em Streamlit;
- deploy em `Streamlit Cloud`;
- suporte a `Groq` e `Ollama`;
- `MongoDB` opcional;
- fallback local para aumentar portabilidade.

### Vantagem da entrega

- facil demonstracao;
- execucao simples;
- interface unica para:
  - chat
  - historico
  - documentos
  - benchmark
  - observabilidade

Fala sugerida:

> O deploy em Streamlit Cloud fecha bem o ciclo do projeto, porque transforma a prova em algo demonstravel ponta a ponta, mantendo ao mesmo tempo a possibilidade de execucao local ou hibrida.

---

## Slide 8 - Limites Atuais

- nao calcula FFT diretamente no pipeline atual;
- nao usa sinais brutos de vibracao;
- nao implementa ainda banco vetorial nativo como motor principal;
- nao e uma solucao de producao;
- continua sendo um **MVP demonstravel**.

Fala sugerida:

> Os limites foram assumidos de forma explicita. O projeto nao tenta vender uma profundidade que o dado fornecido nao suportava. Essa honestidade tecnica foi uma escolha deliberada.

---

## Slide 9 - Melhorias Futuras

- migrar a recuperacao documental para `MongoDB Vector Search` nativo ou indice vetorial dedicado;
- evoluir embeddings locais para modelos semanticos melhores;
- ampliar regras para classes novas, `OOD` e open-set;
- incorporar representacoes espectrais se houver sinal bruto no futuro;
- melhorar ainda mais a separacao entre classes proximas.

Fala sugerida:

> A principal evolucao futura seria aproximar mais o projeto do dominio vibracional classico quando houver sinal bruto, sem abandonar a camada de copiloto e rastreabilidade que o LLM trouxe para a interface.

---

## Slide 10 - Fechamento

### Mensagem final

- a literatura apoiou uma leitura **hibrida**, e nao um LLM como motor numerico puro;
- o dado disponivel favoreceu um **nucleo estatistico auditavel**;
- o projeto entregou um **copiloto prescritivo funcional**, com:
  - historico
  - documentos
  - LLM
  - benchmark
  - deploy

Frase final sugerida:

> O principal resultado deste trabalho foi transformar um caso de manutencao prescritiva em um copiloto demonstravel e rastreavel, preservando um nucleo numerico aderente ao dado disponivel e usando LLM com RAG onde ele realmente agregou valor.

---

## Ordem sugerida de fala

Tempo total: **10 minutos**

- Slide 1: `0:40`
- Slide 2: `1:40`
- Slide 3: `1:00`
- Slide 4: `1:00`
- Slide 5: `1:30`
- Slide 6: `1:50`
- Slide 7: `0:50`
- Slide 8: `0:40`
- Slide 9: `0:35`
- Slide 10: `0:15`

---

## Checklist visual para a apresentacao

- usar o diagrama macro da arquitetura logo apos o slide 2;
- usar pelo menos `2` graficos de benchmark no slide de avaliacao;
- mostrar `1` screenshot do chat e `1` screenshot do dashboard;
- destacar visualmente:
  - `100/100 PASS`
  - `0.92` de `accuracy` no baseline numerico
  - `0.74` no melhor pipeline LLM
  - deploy em Streamlit Cloud

---

## Pergunta dificil e resposta curta

**"Por que nao usar o LLM como motor principal de inferencia?"**

Resposta curta:

> Porque a literatura e os testes deste projeto apontaram que, para este tipo de dado, a inferencia numerica direta permaneceu mais forte e auditavel. O LLM agregou mais como camada de explicacao, recuperacao documental e prescricao textual.
