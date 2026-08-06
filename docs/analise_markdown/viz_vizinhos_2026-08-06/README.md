# Visualizacao de Vizinhos: motor matematico vs embedding textual local

Data de referencia: **6 de agosto de 2026**.

## Escopo

- classes analisadas: cocked_rotor, correia, rolamento_inner, rolamento_outer, rolamento_ball, desbalanceamento, polia, desalinhamento, normal;
- amostragem balanceada: `120` eventos por classe;
- comparacao entre o espaco numerico do motor historico e o espaco textual vetorizado usado na etapa de recuperacao por embeddings;
- o foco aqui e a geometria dos vizinhos, nao a etapa generativa final do LLM.

## Metricas resumidas

- pureza media dos `top-5` vizinhos no espaco numerico: `0.2961`
- pureza media dos `top-5` vizinhos no espaco textual: `0.1546`
- silhouette no espaco numerico: `-0.1272`
- silhouette no espaco textual: `-0.0115`

Leitura curta:

- o espaco textual ficou mais misturado do que o espaco numerico no recorte das classes mais frageis;
- isso nao significa que o LLM seja inutil, mas indica que a etapa de textualizacao + embedding local perde separacao diagnostica importante;
- o resultado conversa com a literatura e com a intuicao de dominio: features de vibracao ja resumidas para texto tendem a preservar menos estrutura discriminativa do que o vetor numerico original.

## Artefatos gerados

- `docs/analise_markdown/viz_vizinhos_2026-08-06/01_espacos_numericos_vs_textuais.html`
- `docs/analise_markdown/viz_vizinhos_2026-08-06/02_casos_vizinhos_numericos_vs_textuais.html`
- `docs/analise_markdown/viz_vizinhos_2026-08-06/metrics.json`
- `docs/analise_markdown/viz_vizinhos_2026-08-06/neighbor_cases.json`

## Casos destacados

### desbalanceamento -> desalinhamento

- sample_id: `5283`
- classe real: `desbalanceamento`
- classe prevista pelo `llm_vector_rag_groq`: `desalinhamento`
- vizinhos numericos: desbalanceamento, desbalanceamento, normal, normal, normal
- vizinhos textuais: polia, rolamento_inner, normal, correia, desalinhamento

### cocked_rotor -> rolamento_inner

- sample_id: `38223`
- classe real: `cocked_rotor`
- classe prevista pelo `llm_vector_rag_groq`: `rolamento_inner`
- vizinhos numericos: normal, rolamento_outer, rolamento_ball, correia, cocked_rotor
- vizinhos textuais: correia, normal, cocked_rotor, desbalanceamento, cocked_rotor

### rolamento_inner -> desalinhamento

- sample_id: `129987`
- classe real: `rolamento_inner`
- classe prevista pelo `llm_vector_rag_groq`: `desalinhamento`
- vizinhos numericos: rolamento_inner, normal, rolamento_inner, desalinhamento, polia
- vizinhos textuais: desalinhamento, desalinhamento, normal, polia, rolamento_outer
