# Relatorio de QA e Guardrails

Data de execucao: **6 de agosto de 2026**.

## Objetivo

Validar o comportamento do copiloto em perguntas livres, eventos estruturados, guardrails fisicos, ausencia de base documental e resistencia a vies por rotulo manual no payload.

## Ajustes validados

- perguntas arquiteturais sobre `MongoDB`, `LLM`, `FFT` e falha nova sem historico passaram a seguir resposta deterministica mais estavel;
- eventos classificados como `estado operacional` nao puxam prescricao documental indevida;
- eventos fisicamente invalidos sao bloqueados como `evento_invalido`;
- resposta sem base documental nao inventa prescricao tecnica;
- variacoes artificiais do campo `fault` nao passaram a dominar a classificacao numerica.

## Suite executada

Script utilizado:

`scripts/run_quality_regression.py`

Blocos testados:

1. perguntas livres documentais e arquiteturais;
2. evento tipico de falha conhecida;
3. evento de estado operacional;
4. evento fisicamente incoerente;
5. comportamento sem documentos indexados;
6. teste de vies por rotulo em amostras reais do dataset.

## Resultado consolidado

- Total de verificacoes: `15`
- Aprovadas: `15`
- Falhas: `0`

Resumo por categoria:

| Categoria | Casos | Resultado |
| --- | --- | --- |
| Freeform | `7` | `7/7 PASS` |
| Event | `3` | `3/3 PASS` |
| No-doc | `2` | `2/2 PASS` |
| Bias | `3` | `3/3 PASS` |

## Casos cobertos

### Perguntas livres

- quais documentos existem na base e que tipo de falha cada um cobre;
- diferenca entre desbalanceamento e desalinhamento;
- o que e FFT e por que ela e importante;
- se o pipeline atual calcula FFT;
- o que acontece com cavitacao sem historico;
- se o LLM faz inferencia numerica principal ou apenas orquestra;
- se o MongoDB atua como persistencia ou motor vetorial nativo.

### Eventos estruturados

- evento tipico de falha conhecida;
- evento com cara de `motor parado`;
- evento fisicamente incoerente com temperatura e RPM invalidos.

### Guardrail sem documentos

- evento conhecido sem base documental disponivel;
- pergunta documental com base documental vazia.

### Vies por rotulo

Foram testadas amostras reais com quatro variantes de payload:

- sem rotulo manual;
- rotulo `normal`;
- rotulo `motor parado`;
- rotulo propositalmente errado.

O objetivo foi verificar se o motor numerico continuava estavel mesmo com contaminacao artificial do campo `fault`.

## Observacao tecnica

Na rodada inicial, alguns casos de `rolamento_inner`, `cocked_rotor` e `polia` pareciam instaveis. Depois do pente fino, foi identificado um fator estrutural importante: a busca historica podia comparar eventos de teste contra um historico persistido parcial no `MongoDB`, enquanto a avaliacao usava amostras do dataset completo.

Esse ponto foi corrigido:

- o historico persistido parcial continua valido para persistencia;
- a inferencia diagnostica volta automaticamente para o `banner.csv` completo enquanto a cobertura do Mongo nao estiver praticamente sincronizada.

## Extensao: matriz ampliada de 110 testes

Depois da suite inicial de `15` verificacoes, foi executada uma matriz mais ampla com `110` casos cobrindo:

- catalogo documental;
- variacoes de linguagem para listar documentos por familia;
- perguntas sobre arquitetura;
- FFT e limites do pipeline;
- guardrails fisicos;
- estados operacionais;
- OOD;
- ausencia de base documental;
- vies por rotulo;
- fluxo de chat;
- naturalidade em conversa curta;
- capacidade de sintese em perguntas livres;
- comparacao Python vs Mongo.

Resultado consolidado final da matriz ampliada:

- Total de verificacoes: `110`
- Aprovadas: `110`
- Falhas: `0`
- JSON gerado: `docs/analise_markdown/quality_matrix_100_results_2026-08-06.json`

## O que foi ajustado entre a primeira e a ultima rodada

Os casos que falhavam na rodada inicial foram tratados em quatro frentes:

1. Perguntas arquiteturais

- respostas deterministicas mais estaveis para banco vetorial nativo;
- resposta explicita para queda do Mongo e fallback local.

2. Guardrail sem documento

- reducao de checklist residual quando nao houver lastro documental;
- resposta mais seca em cenarios sem base documental indexada.

3. Estado operacional versus falha em carga

- preservacao do caso `motor_desligado` em `OOD` extremo;
- bloqueio de rotulos de estado como `baseline` e `teste` quando o evento estiver em carga e a distribuicao historica apontar para falha mecanica.

4. Uso de historico persistido parcial

- a inferencia deixou de usar historico parcial do Mongo para similaridade diagnostica;
- o fallback para o dataset completo eliminou vies por amostragem incompleta na comparacao historica.

5. Naturalidade e consulta documental

- consultas como `liste documentos de rolamentos` passaram a cair corretamente no fluxo documental;
- respostas curtas como `oi`, `obrigado` e `conte uma piada` deixaram de responder de forma generica demais;
- perguntas sobre `RAG` passaram a responder o conceito do projeto, em vez de desviar para interpretacoes erradas do termo.

## Leitura adicional sobre proximidade entre classes

Foi executada uma checagem numerica direta no dataset completo, usando as `12` features do motor historico escaladas com `StandardScaler` e comparacao entre centroides de classe.

Pares mais proximos observados:

- `cocked_rotor <-> correia`: distancia `0.2910`
- `rolamento_ball <-> rolamento_inner`: distancia `0.3130`
- `rolamento_ball <-> rolamento_outer`: distancia `0.3628`
- `rolamento_inner <-> rolamento_outer`: distancia `0.4272`
- `desalinhamento <-> normal`: distancia `0.4523`
- `desbalanceamento <-> polia`: distancia `0.5876`

Leitura tecnica:

- parte das confusoes encontradas nao parece ser apenas erro de prompt ou de UI;
- existe proximidade estatistica real entre algumas familias no espaco de features disponiveis;
- isso ajuda a explicar por que `rolamento_inner`, `rolamento_outer`, `cocked_rotor`, `correia`, `polia` e `normal` ainda se misturam em certos casos.

## O `llm_vector_rag` infere melhor nesses casos?

No benchmark consolidado de **5 de agosto de 2026**, a resposta curta e: **nao**.

Evidencias:

- `mahalanobis_weighted_knn`: `accuracy=0.92`, `macro_f1=0.9195`
- `llm_vector_rag_groq`: `accuracy=0.74`, `macro_f1=0.7443`

Confusoes relevantes do pipeline `llm_vector_rag_groq`:

- `desbalanceamento -> desalinhamento`: `3` ocorrencias
- `cocked_rotor -> rolamento_inner`: `2` ocorrencias
- `correia -> desalinhamento`: `2` ocorrencias
- `rolamento_inner -> desalinhamento`: `1` ocorrencia
- `rolamento_inner -> correia`: `1` ocorrencia

Conclusao pratica:

- o LLM melhora a camada de explicacao, prescricao textual e orquestracao;
- ele nao eliminou melhor do que o motor numerico as ambiguidades entre classes proximas;
- no estado atual, a melhoria mais promissora esta em separar melhor as classes, revisar features e ampliar o lastro documental, e nao apenas trocar o modelo gerador.

## Melhorias futuras recomendadas

- revisar a separacao entre `rolamento_inner` e `rolamento_outer`, incluindo features, proximidade estatistica e criterios de classe;
- revisar classes mais frageis como `cocked_rotor`, `polia` e estados operacionais sob OOD extremo;
- introduzir uma politica explicita para conflitos entre `state`, `fault` e `OOD`, priorizando a semantica correta do caso;
- evoluir para representacoes mais discriminativas quando houver sinal bruto, como FFT, envelope e bandas de frequencia;
- manter a regra de nao usar historico persistido parcial para diagnostico final, exceto quando o espelho persistido estiver praticamente sincronizado.

## Comando de reproducao

```powershell
@'
import json
from scripts.run_quality_regression import run_freeform_cases, run_event_cases, run_no_doc_cases, run_label_bias_cases

rows = []
rows.extend(run_freeform_cases())
rows.extend(run_event_cases())
rows.extend(run_no_doc_cases())
rows.extend(run_label_bias_cases())
print(json.dumps(rows, ensure_ascii=False, indent=2))
failed = [r for r in rows if r["status"] == "FAIL"]
print(f"FAILED={len(failed)} TOTAL={len(rows)}")
'@ | python -
```

Saida esperada:

```text
FAILED=0 TOTAL=15
```
