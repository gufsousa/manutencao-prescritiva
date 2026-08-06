# Avaliacao de Roteamento de Intencao

Data de execucao: **6 de agosto de 2026**.

## Objetivo

Avaliar se o copiloto deve continuar com:

- roteamento deterministico + heuristicas;
- classificador simples de intencao;
- ou um passo adicional de planejamento leve, em vez de um agente `ReAct` completo.

## Script executado

Arquivo:

- `scripts/run_intent_routing_eval.py`

Comando:

```powershell
python scripts\run_intent_routing_eval.py --write-json docs\analise_markdown\intent_routing_eval_2026-08-06.json
```

Saida:

- `docs/analise_markdown/intent_routing_eval_2026-08-06.json`

## Matriz executada

Foram avaliados `41` casos divididos em:

- conversa curta;
- consulta documental;
- pergunta livre tecnica;
- evento estruturado;
- casos hibridos;
- casos de borda com linguagem telegráfica.

## Resultado consolidado

### Rodada inicial

- `37/41 PASS`
- `4/41 FAIL`

Falhas encontradas:

1. string de evento em formato de dicionario Python com aspas simples;
2. consulta telegráfica `documento rolamento`;
3. consulta abreviada `tem doc de polia?`;
4. subtipo `example_event` tratado como fail, embora o route estivesse correto.

### Rodada apos ajuste heuristico

- `39/41 PASS`
- `2/41 FAIL`

Casos ainda restantes:

1. `o que sao rolamentos e qual documento fala disso?`
2. `Tenho um documento novo sobre cavitacao. O que o sistema faz se nao houver historico?`

## Leitura tecnica do resultado

Os `2` casos restantes nao sao erros simples de classificacao.

Eles sao casos de **intencao composta**:

- parte da pergunta pede conceito tecnico;
- parte pede documento;
- ou parte pede documento e parte pede limite arquitetural.

Isso sugere que o router atual:

- ja esta bom para intencoes puras;
- comecou a mostrar limite quando a pergunta mistura dois objetivos em uma unica frase.

## Conclusao pratica

O resultado nao indica necessidade imediata de um `ReAct` completo.

Ele indica algo mais especifico:

### O que ja funciona bem com heuristica

- saudacao versus pergunta tecnica;
- consulta documental direta;
- evento estruturado JSON;
- pergunta arquitetural curta;
- pergunta livre conceitual.

### Onde a heuristica comeca a perder

- perguntas compostas;
- perguntas que pedem duas saidas ao mesmo tempo;
- perguntas que misturam conceito + documento + limite do sistema.

## O que a literatura sugere

### 1. ReAct

Referencia:

- Yao et al., **ReAct: Synergizing Reasoning and Acting in Language Models**  
  https://arxiv.org/abs/2210.03629

Leitura aplicada:

- `ReAct` faz sentido quando o agente precisa decidir iterativamente qual ferramenta chamar, observar retorno e replanejar;
- ele e forte para tarefas multi-step com interacao externa;
- para este projeto, isso tende a ser excessivo na maioria das perguntas comuns.

### 2. Toolformer

Referencia:

- Schick et al., **Toolformer: Language Models Can Teach Themselves to Use Tools**  
  https://arxiv.org/abs/2302.04761

Leitura aplicada:

- a ideia principal e aprender quando usar ferramenta;
- isso conversa bem com o problema de `rotear antes de responder`;
- mas o projeto atual ainda nao precisa treinamento especifico para isso.

### 3. Plan-and-Solve

Referencia:

- Wang et al., **Plan-and-Solve Prompting**  
  https://arxiv.org/abs/2305.04091

Leitura aplicada:

- este trabalho e o mais aderente ao problema observado;
- ele sugere decompor a tarefa em subtarefas antes de responder;
- para o projeto, isso pode virar um passo leve do tipo:
  - identificar que a pergunta tem duas intencoes;
  - responder primeiro o conceito;
  - depois anexar os documentos relevantes.

### 4. Literatura de Intent Classification

Referencias:

- Larson et al., **A Survey of Intent Classification and Slot-Filling Datasets for Task-Oriented Dialog**  
  https://arxiv.org/abs/2207.13211

- Balaraman et al., **Recent Neural Methods on Slot Filling and Intent Classification for Task-Oriented Dialogue Systems**  
  https://arxiv.org/abs/2011.00564

Leitura aplicada:

- problemas de intencao nao sao apenas classificacao de frase curta;
- ha impacto forte de dominio, composicao, multi-intent e formulacao aberta;
- isso reforca que, neste projeto, so trocar heuristica por um classificador puro pode nao resolver os casos compostos.

## Recomendacao arquitetural

### Nao recomendado agora

- migrar tudo para um `ReAct` completo;
- introduzir planner iterativo para toda pergunta;
- colocar mais liberdade agentica onde a maior parte dos casos ja esta estavel.

### Recomendado agora

Implementar um **planner leve apenas para perguntas compostas**.

Exemplo de politica:

1. router deterministico continua como camada principal;
2. se a pergunta tiver forte sinal de duas intencoes:
   - `conceito + documento`
   - `documento + limite arquitetural`
   - `procedimento + exemplo`
3. acionar um mini-planejamento local:
   - `subtarefa 1`: responder o conceito;
   - `subtarefa 2`: listar ou resumir documentos;
   - `subtarefa 3`: consolidar em uma unica resposta.

## Interpretacao final

Com base em `39/41 PASS`:

- o projeto ja nao parece precisar de um agente mais pesado para o fluxo normal;
- as falhas residuais apontam mais para **multi-intent decomposition** do que para falta de `ReAct`;
- o melhor proximo passo e um **router + planner leve para casos compostos**, e nao um salto direto para um agente iterativo completo.
