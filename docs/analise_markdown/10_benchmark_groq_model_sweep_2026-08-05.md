# Sweep de Modelos Groq para llm_vector_rag

## Escopo

- Avaliacao em 50 amostras balanceadas.
- Familias: desalinhamento, desbalanceamento, rolamento_inner, correia, cocked_rotor.
- Objetivo: comparar diferentes modelos Groq no mesmo pipeline `llm_vector_rag`.

## Modelos testados

- `llama-3.1-8b-instant`
- `llama-3.3-70b-versatile`
- `openai/gpt-oss-20b`
- `openai/gpt-oss-120b`
- `qwen/qwen3.6-27b`

## Resultado consolidado

| provider | model | rows | accuracy | macro_f1 | avg_latency_ms |
| --- | --- | --- | --- | --- | --- |
| groq | llama-3.1-8b-instant | 50 | 0.7400 | 0.7443 | 18628.4290 |
| groq | llama-3.3-70b-versatile | 50 | 0.7200 | 0.7245 | 16122.0160 |
| groq | openai/gpt-oss-120b | 39 | 0.6923 | 0.6922 | 15045.6550 |
| groq | openai/gpt-oss-20b | 50 | 0.5400 | 0.4939 | 16432.1560 |
| groq | qwen/qwen3.6-27b | 50 | 0.0200 | 0.0303 | 28011.2740 |

## Referencias cruzadas

- Referencia anterior Groq `llama-3.1-8b-instant`: acuracia **0.7400**, macro-F1 **0.7443**.
- Referencia local Ollama `qwen2.5-coder:7b`: acuracia **0.6800**, macro-F1 **0.6900**.

## Leitura tecnica

- Se um modelo Groq maior superar o `llama-3.1-8b-instant`, isso indica que o pipeline `llm_vector_rag` ainda tem margem de ganho por capacidade de raciocinio e aderencia de sintese.
- Se a melhora for pequena, reforca que o gargalo principal nao esta apenas no modelo, mas na representacao do evento, na recuperacao e no tipo de supervisao disponivel.
- O contraste com o Ollama local mostra a perda de qualidade ao trazer o mesmo paradigma para um modelo menor em execucao edge.
- No sweep executado em **5 de agosto de 2026**, o melhor resultado permaneceu com `llama-3.1-8b-instant`, seguido de perto por `llama-3.3-70b-versatile`.
- `openai/gpt-oss-120b` ficou com execucao parcial de **39/50 amostras** por limite de tokens por minuto da conta no Groq, entao este numero deve ser lido como indicativo e nao como comparacao final fechada.
- `qwen/qwen3.6-27b` teve desempenho muito abaixo dos demais neste prompt e neste formato de saida JSON, indicando baixa aderencia ao pipeline atual.

## Fonte dos modelos avaliados

- Catalogo oficial Groq consultado em **5 de agosto de 2026**: https://console.groq.com/docs/models

- Relatorio gerado em `2026-08-05T04:13:23.639824+00:00`.
