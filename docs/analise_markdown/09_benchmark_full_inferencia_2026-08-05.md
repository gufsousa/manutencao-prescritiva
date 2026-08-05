# Benchmark Completo de Inferencia 2026-08-05

## Escopo

- Amostra robusta e balanceada com **50 eventos**.
- Familias testadas: desalinhamento, desbalanceamento, rolamento_inner, correia, cocked_rotor.
- Tecnicas estatisticas e vetoriais executadas em todas as 50 amostras.
- `llm_vector_rag` executado duas vezes: uma com **Groq `llama-3.1-8b-instant`** e outra com **Ollama `qwen2.5-coder:7b`**.

## Tecnicas avaliadas

- `euclidean_knn`: baseline atual por distancia Euclidiana.
- `mahalanobis_weighted_knn`: baseline robusto com distancia de Mahalanobis, voto ponderado e sinal OOD.
- `cosine_knn`: vizinhos por cosseno nas features escaladas.
- `centroid_euclidean`: centroide de classe.
- `text_vector_vote`: textualizacao do evento e voto por exemplos recuperados por vetor.
- `llm_vector_rag_groq`: LLM total com vetores usando Groq.
- `llm_vector_rag_ollama_small`: LLM total com vetores usando Ollama local menor.

## Resultado consolidado

| technique | provider | model | rows | accuracy | macro_f1 | avg_latency_ms |
| --- | --- | --- | --- | --- | --- | --- |
| mahalanobis_weighted_knn | local | deterministic | 50 | 0.9200 | 0.9195 | 75.5000 |
| euclidean_knn | local | deterministic | 50 | 0.8000 | 0.8027 | 98.6670 |
| cosine_knn | local | deterministic | 50 | 0.8000 | 0.7942 | 147.5330 |
| llm_vector_rag_groq | groq | llama-3.1-8b-instant | 50 | 0.7400 | 0.7443 | 9942.8140 |
| llm_vector_rag_ollama_small | ollama | qwen2.5-coder:7b | 50 | 0.6800 | 0.6900 | 20808.9200 |
| centroid_euclidean | local | deterministic | 50 | 0.4800 | 0.4654 | 122.9270 |
| text_vector_vote | local | deterministic | 50 | 0.4400 | 0.4248 | 1234.9120 |

## Comparacao direta do `llm_vector_rag`

- Acuracia Groq (`llama-3.1-8b-instant`): **0.7400**
- Acuracia Ollama (`qwen2.5-coder:7b`): **0.6800**
- Delta de acuracia: **+0.0600**
- Macro-F1 Groq: **0.7443**
- Macro-F1 Ollama: **0.6900**
- Delta de Macro-F1: **+0.0543**
- Latencia media Groq: **9942.814 ms**
- Latencia media Ollama: **20808.920 ms**

## Leitura tecnica

- A melhor tecnica geral em acuracia foi **`mahalanobis_weighted_knn`** com **0.9200**.
- O novo baseline combina distancia de Mahalanobis, voto ponderado e guardrail OOD, o que melhora a robustez numerica sem depender de geracao probabilistica para classificar o evento.
- Se o baseline numerico ficar acima do LLM, isso reforca que a parte numerica ainda carrega o sinal mais forte nesta base.
- Se o `llm_vector_rag_groq` se aproximar do baseline, isso sustenta melhor a narrativa LLM-first com recuperacao externa.
- A comparacao com o Ollama local menor mede a perda de qualidade ao trazer o pipeline para execucao edge/local.

## Leitura apoiada na literatura

- Boye e Moell, *Large Language Models and Mathematical Reasoning Failures* (arXiv, 17 de fevereiro de 2025; revisado em 21 de fevereiro de 2025) relatam erros persistentes de aritmetica, planejamento e raciocinio em varias etapas, inclusive quando a resposta final parece plausivel. Fonte: https://arxiv.org/abs/2502.11574
- Li et al., *Exposing Numeracy Gaps: A Benchmark to Evaluate Fundamental Numerical Abilities in Large Language Models* (Findings of ACL 2025, julho de 2025) mostram fraquezas persistentes em aritmetica, recuperacao numerica e comparacao de magnitude em modelos fortes. Fonte: https://aclanthology.org/2025.findings-acl.1026/

## Recall por familia

### mahalanobis_weighted_knn

| family | label_pt | recall |
| --- | --- | --- |
| desalinhamento | Desalinhamento | 1.0000 |
| desbalanceamento | Desbalanceamento | 1.0000 |
| rolamento_inner | Rolamento inner race | 0.9000 |
| correia | Correia | 0.8000 |
| cocked_rotor | Cocked rotor | 0.9000 |

Principais confusoes:
- `cocked_rotor` -> `desbalanceamento`: 1 ocorrencia(s)
- `correia` -> `cocked_rotor`: 1 ocorrencia(s)
- `correia` -> `desalinhamento`: 1 ocorrencia(s)
- `rolamento_inner` -> `desalinhamento`: 1 ocorrencia(s)

### euclidean_knn

| family | label_pt | recall |
| --- | --- | --- |
| desalinhamento | Desalinhamento | 0.9000 |
| desbalanceamento | Desbalanceamento | 0.8000 |
| rolamento_inner | Rolamento inner race | 0.9000 |
| correia | Correia | 0.7000 |
| cocked_rotor | Cocked rotor | 0.7000 |

Principais confusoes:
- `correia` -> `cocked_rotor`: 2 ocorrencia(s)
- `desbalanceamento` -> `cocked_rotor`: 2 ocorrencia(s)
- `cocked_rotor` -> `desbalanceamento`: 1 ocorrencia(s)
- `cocked_rotor` -> `correia`: 1 ocorrencia(s)
- `cocked_rotor` -> `rolamento_inner`: 1 ocorrencia(s)

### cosine_knn

| family | label_pt | recall |
| --- | --- | --- |
| desalinhamento | Desalinhamento | 0.9000 |
| desbalanceamento | Desbalanceamento | 0.9000 |
| rolamento_inner | Rolamento inner race | 0.9000 |
| correia | Correia | 0.8000 |
| cocked_rotor | Cocked rotor | 0.5000 |

Principais confusoes:
- `cocked_rotor` -> `correia`: 2 ocorrencia(s)
- `cocked_rotor` -> `desalinhamento`: 1 ocorrencia(s)
- `cocked_rotor` -> `desbalanceamento`: 1 ocorrencia(s)
- `cocked_rotor` -> `rolamento_inner`: 1 ocorrencia(s)
- `correia` -> `cocked_rotor`: 1 ocorrencia(s)

### llm_vector_rag_groq

| family | label_pt | recall |
| --- | --- | --- |
| desalinhamento | Desalinhamento | 0.9000 |
| desbalanceamento | Desbalanceamento | 0.7000 |
| rolamento_inner | Rolamento inner race | 0.7000 |
| correia | Correia | 0.8000 |
| cocked_rotor | Cocked rotor | 0.6000 |

Principais confusoes:
- `desbalanceamento` -> `desalinhamento`: 3 ocorrencia(s)
- `correia` -> `desalinhamento`: 2 ocorrencia(s)
- `cocked_rotor` -> `rolamento_inner`: 2 ocorrencia(s)
- `cocked_rotor` -> `correia`: 1 ocorrencia(s)
- `cocked_rotor` -> `desalinhamento`: 1 ocorrencia(s)

### llm_vector_rag_ollama_small

| family | label_pt | recall |
| --- | --- | --- |
| desalinhamento | Desalinhamento | 0.7000 |
| desbalanceamento | Desbalanceamento | 0.6000 |
| rolamento_inner | Rolamento inner race | 0.7000 |
| correia | Correia | 0.8000 |
| cocked_rotor | Cocked rotor | 0.6000 |

Principais confusoes:
- `desbalanceamento` -> `desalinhamento`: 4 ocorrencia(s)
- `cocked_rotor` -> `rolamento_inner`: 2 ocorrencia(s)
- `rolamento_inner` -> `desalinhamento`: 2 ocorrencia(s)
- `correia` -> `desalinhamento`: 2 ocorrencia(s)
- `cocked_rotor` -> `desalinhamento`: 1 ocorrencia(s)

### centroid_euclidean

| family | label_pt | recall |
| --- | --- | --- |
| desalinhamento | Desalinhamento | 0.8000 |
| desbalanceamento | Desbalanceamento | 0.5000 |
| rolamento_inner | Rolamento inner race | 0.4000 |
| correia | Correia | 0.5000 |
| cocked_rotor | Cocked rotor | 0.2000 |

Principais confusoes:
- `cocked_rotor` -> `correia`: 7 ocorrencia(s)
- `rolamento_inner` -> `desalinhamento`: 3 ocorrencia(s)
- `desbalanceamento` -> `desalinhamento`: 3 ocorrencia(s)
- `correia` -> `rolamento_inner`: 3 ocorrencia(s)
- `desbalanceamento` -> `correia`: 2 ocorrencia(s)

### text_vector_vote

| family | label_pt | recall |
| --- | --- | --- |
| desalinhamento | Desalinhamento | 0.8000 |
| desbalanceamento | Desbalanceamento | 0.1000 |
| rolamento_inner | Rolamento inner race | 0.2000 |
| correia | Correia | 0.6000 |
| cocked_rotor | Cocked rotor | 0.5000 |

Principais confusoes:
- `desbalanceamento` -> `desalinhamento`: 8 ocorrencia(s)
- `rolamento_inner` -> `desalinhamento`: 4 ocorrencia(s)
- `rolamento_inner` -> `desbalanceamento`: 3 ocorrencia(s)
- `cocked_rotor` -> `rolamento_inner`: 2 ocorrencia(s)
- `correia` -> `desalinhamento`: 2 ocorrencia(s)

## Conclusao

- Este benchmark mede o comportamento de tecnicas numericas, vetoriais textuais e LLM total com vetores em 50 amostras balanceadas.
- O resultado ajuda a defender, com dado experimental, se o LLM deve ser o motor principal da classificacao ou a camada de orquestracao e sintese.
- Relatorio gerado em `2026-08-05T14:28:38.650995+00:00`.
