# Comparativo llm_vector_rag_groq: Python vs Mongo Atlas

## Escopo

- Benchmark com **20 amostras** balanceadas.
- Pipeline avaliado: `llm_vector_rag_groq` com modelo `llama-3.1-8b-instant`.
- O que muda entre as execucoes: apenas a busca documental.
- Backend A: ranking documental em Python.
- Backend B: ranking documental no MongoDB Atlas via `$vectorSearch`.
- `top_k_docs`: 4.

## Metricas por backend

| backend | rows | accuracy | macro_f1 | avg_latency_ms | avg_doc_latency_ms | same_prediction_ratio |
| --- | --- | --- | --- | --- | --- | --- |
| mongo | 20 | 0.6000 | 0.5857 | 18160.8380 | 32.7630 | 1.0000 |
| python | 20 | 0.6000 | 0.5857 | 18484.3720 | 114.9500 | 1.0000 |

## Resumo agregado

| backend | rows | accuracy | avg_latency_ms | avg_doc_latency_ms |
| --- | --- | --- | --- | --- |
| mongo | 20 | 0.6000 | 18160.8378 | 32.7630 |
| python | 20 | 0.6000 | 18484.3724 | 114.9501 |

## Consistencia entre backends

- Mesma falha predita entre Python e Mongo em **100.00%** das amostras.
- Overlap medio dos chunks documentais no backend Mongo: **4.00** em top-4.
- Mesma ordem exata de chunks entre Python e Mongo em **100.00%** das amostras.

## Leitura tecnica

- Se a acuracia e as predicoes finais ficarem proximas, isso indica que a migracao do ranking vetorial para o Atlas preserva o comportamento do pipeline atual.
- Se o Atlas reduzir latencia mantendo a mesma saida, ele passa a ser uma opcao forte para evolucao arquitetural.
- Se houver divergencia alta, o gargalo passa a ser tuning de index, estrategia ANN/ENN ou detalhes de score entre os motores.

- Relatorio gerado em `2026-08-05T22:09:24.537275+00:00`.