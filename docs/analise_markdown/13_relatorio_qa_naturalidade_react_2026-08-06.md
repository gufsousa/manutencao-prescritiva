# Relatorio de QA, Naturalidade e ReAct

Data de execucao: **6 de agosto de 2026**.

## Objetivo

Reexecutar a validacao ponta a ponta do copiloto apos os ajustes mais recentes, com foco adicional em:

- naturalidade nas respostas curtas;
- capacidade de sintese em perguntas livres;
- aderencia a consultas sobre a base documental;
- implicacoes arquiteturais do uso, ou nao, de um fluxo mais proximo de `ReAct`.

## Script executado

Script principal:

`scripts/run_quality_matrix_100.py`

Comando utilizado:

```powershell
python scripts\run_quality_matrix_100.py --write-json docs\analise_markdown\quality_matrix_100_results_2026-08-06.json
```

Arquivo de saida:

- `docs/analise_markdown/quality_matrix_100_results_2026-08-06.json`

## Resultado consolidado

- Total de verificacoes: `110`
- Aprovadas: `110`
- Falhas: `0`
- Skipped: `0`

Leitura pratica:

- os guardrails fisicos seguem consistentes;
- a camada documental parou de responder de forma generica em consultas por familia;
- o fluxo livre ficou mais natural para interacoes curtas;
- os cenarios sem lastro documental passaram a bloquear melhor respostas tecnicas inventadas.

## O que foi melhorado nesta rodada

### 1. Consulta documental mais aderente

Foram melhorados casos como:

- `liste documentos de rolamentos`
- `listar documentos de correias`
- `documentos de polia`
- `liste documentos de cocked rotor`

Comportamento observado agora:

- a intencao cai corretamente em `document_query`;
- a resposta lista o documento aderente em vez de desviar para conversa generica;
- o resumo fica mais especifico para a familia solicitada.

Exemplo observado:

> `Encontrei 1 documento(s) relacionado(s) a rolamentos na base documental.`

### 2. Conversa curta menos artificial

Foram estabilizados casos como:

- `oi`
- `obrigado`
- `kkk`
- `conte uma piada`

Comportamento atual:

- respostas curtas nao tentam abrir um discurso tecnico desnecessario;
- o copiloto continua util, mas sem soar robotico demais;
- a conversa leve nao contamina o fluxo tecnico.

### 3. Resposta sobre RAG mais objetiva

A pergunta:

- `Usa RAG?`

passou a responder o conceito do projeto, em vez de cair em formulacoes vagas ou laterais.

Exemplo observado:

> `RAG e a combinacao de recuperacao de contexto com geracao de resposta pelo modelo.`

### 4. Guardrail mais forte sem base documental

O caso que ainda escapava era:

- pergunta tecnica livre sem documentos indexados.

Antes:

- o fluxo ainda podia deixar o LLM responder por cima do guardrail.

Depois do ajuste:

- se nao houver `chunks` documentais recuperados, o fluxo livre fica bloqueado para resposta tecnica com falsa seguranca;
- a resposta passa a admitir falta de lastro.

Exemplo observado:

> `nao encontrei lastro suficiente na base para sustentar a orientacao tecnica`

## Leitura dos 110 testes

Os casos adicionais desta rodada reforcaram quatro grupos:

1. catalogo documental;
2. naturalidade de conversa;
3. sintese em perguntas sobre arquitetura e RAG;
4. resistencia a resposta sem base documental.

Os testes mostraram que o maior ganho recente nao veio de mudar o motor numerico, e sim de:

- melhorar o roteamento;
- endurecer os guardrails;
- reduzir liberdade do LLM quando o caso pede resposta deterministica;
- deixar a resposta livre mais curta e mais util.

## O que ainda merece melhoria

Mesmo com `110/110 PASS`, ainda existem oportunidades reais:

### 1. Perguntas amplas sobre todos os documentos

Casos como:

- `Quais documentos existem na base e que tipo de falha cada um cobre?`

ainda podem sintetizar demais ou privilegiar os trechos mais recuperados, em vez de montar um catalogo completo documento a documento.

Melhoria recomendada:

- quando a pergunta for claramente catalografica, responder a partir do `documents_catalog` inteiro antes de olhar `chunks`.

### 2. Sintese ainda pode ficar curta demais

Em algumas perguntas livres, o texto ficou menos generico, mas ainda tende a:

- responder certo;
- responder curto;
- nao explorar tanto a diferenca conceitual entre termos proximos.

Melhoria recomendada:

- usar um passo final de refinamento apenas para clareza textual, sem liberar nova inferencia.

### 3. Politica de resposta livre

Hoje o sistema esta mais seguro porque:

- respostas de arquitetura e limites do sistema foram determinizadas;
- respostas sem lastro foram secadas.

Melhoria recomendada:

- explicitar essa politica em configuracao, e nao apenas em codigo.

## ReAct na literatura e o que isso significa aqui

Foram revisadas referencias centrais que ajudam a pensar a evolucao do fluxo agentic:

1. **ReAct: Synergizing Reasoning and Acting in Language Models**  
   Link: https://arxiv.org/abs/2210.03629

2. **Reflexion: Language Agents with Verbal Reinforcement Learning**  
   Link: https://arxiv.org/abs/2303.11366

3. **Plan-and-Solve Prompting: Improving Zero-Shot Chain-of-Thought Reasoning by Large Language Models**  
   Link: https://arxiv.org/abs/2305.04091

4. **Self-Refine: Iterative Refinement with Self-Feedback**  
   Link: https://arxiv.org/abs/2303.17651

### Leitura tecnica resumida

#### ReAct

O ReAct original faz sentido quando o agente precisa:

- pensar em etapas;
- decidir qual ferramenta chamar;
- observar retorno da ferramenta;
- reajustar a proxima acao.

Isso e forte para ambientes de busca, QA multi-hop e tarefas iterativas com observacao externa.

#### Reflexion

O Reflexion acrescenta memoria textual de fracasso e tentativa, para melhorar proximas rodadas.

Isso e util quando:

- ha repeticao de episodios;
- vale aprender com falhas anteriores sem retreinar o modelo.

#### Plan-and-Solve

O Plan-and-Solve ajuda quando o modelo erra por pular etapas.

Ele e mais leve que um agente completo e pode ser mais barato que um planner iterativo de verdade.

#### Self-Refine

O Self-Refine e util quando a primeira resposta esta correta no conteudo, mas fraca em clareza, estrutura ou tom.

## Analise aplicada ao projeto

Com base nos 110 testes, a recomendacao atual **nao** e migrar direto para um `ReAct` completo.

Motivos:

1. o fluxo do projeto ja tem poucas ferramentas e papeis bem definidos;
2. boa parte dos erros recentes nao era falta de planejamento iterativo, e sim:
   - roteamento frouxo;
   - excesso de liberdade do LLM;
   - falta de guardrail quando nao havia documento;
   - resposta documental pouco especifica;
3. um `ReAct` mais solto aumentaria:
   - latencia;
   - variabilidade;
   - custo cognitivo da trilha;
   - superficie de erro.

### O que a literatura sugere como proximo passo mais aderente

Em vez de um `ReAct` amplo, o mais aderente ao projeto hoje parece ser:

1. **router deterministico + ferramentas fixas**
   - manter `event_json`, `document_query` e `freeform_question`;
   - manter chamadas internas previsiveis.

2. **Plan-and-Solve local apenas para perguntas complexas**
   - usar um mini-plano textual quando a pergunta livre exigir decomposicao;
   - evitar isso para perguntas curtas e catalograficas.

3. **Self-Refine restrito a forma, nao ao diagnostico**
   - aplicar refinamento so para melhorar naturalidade e sintese;
   - nao usar essa etapa para reinventar evidencia.

4. **Reflexion apenas se houver memoria de avaliacao**
   - so faz sentido se o projeto acumular feedback real de erro, revisao humana ou benchmark recurrente.

## Conclusao

Depois da nova rodada, o projeto ficou melhor exatamente onde estava mais fragil:

- consulta a documentos;
- respostas curtas;
- perguntas sobre RAG;
- bloqueio de respostas sem base.

A literatura sobre `ReAct` e tecnicas proximas nao contradiz isso; pelo contrario, ela sugere que:

- nem todo problema precisa de um agente iterativo completo;
- em fluxos como este, o maior ganho pode vir de **restricao, decomposicao leve e refinamento controlado**, e nao de mais liberdade agentica.

Resumo final:

- o copiloto esta mais natural;
- o fluxo documental esta mais aderente;
- os guardrails ficaram mais honestos;
- a evolucao recomendada e um agentic **leve e controlado**, nao um `ReAct` aberto por padrao.
