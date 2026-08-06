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

O caso de `rolamento_inner` permaneceu estavel no teste de vies, mas convergiu para `rolamento_outer` em todas as variantes. Isso nao quebrou o guardrail de vies por rotulo, porem indica uma proximidade semantica/numerica nessa familia que merece revisao futura com mais profundidade.

## Extensao: matriz de 100 testes

Depois da suite inicial de `15` verificacoes, foi executada uma matriz mais ampla com `100` casos cobrindo:

- catalogo documental;
- perguntas sobre arquitetura;
- FFT e limites do pipeline;
- guardrails fisicos;
- estados operacionais;
- OOD;
- ausencia de base documental;
- vies por rotulo;
- fluxo de chat;
- comparacao Python vs Mongo.

Resultado consolidado da matriz ampliada:

- Total de verificacoes: `100`
- Aprovadas: `90`
- Falhas: `10`
- JSON gerado: `docs/analise_markdown/quality_matrix_100_results_2026-08-06.json`

## Principais fragilidades encontradas

As `10` falhas da matriz ampliada se concentraram em tres grupos principais:

1. Perguntas arquiteturais ainda incompletas

- `arch_03`: a pergunta sobre banco vetorial nativo ainda pode cair em resposta documental genérica;
- `arch_05`: a pergunta sobre queda do Mongo ainda nao responde de forma deterministica em todos os enunciados equivalentes.

2. Guardrail documental ainda permissivo

- `doc_guard_05`: mesmo sem documentos indexados, a resposta ainda pode manter estrutura de diagnostico e checklist mais forte do que o ideal para um caso sem lastro.

3. Separacao fraca entre algumas familias de falha

- `bias_label_09`, `bias_label_10`, `bias_label_11`: amostras de `rolamento_inner` convergiram para `rolamento_outer`;
- `bias_label_12`: um caso de `cocked_rotor` caiu para `desalinhamento`;
- `bias_label_14`: um caso de `polia` caiu para `normal`;
- `bias_label_20`: estabilidade media das classes ficou em `20%`, abaixo do limiar esperado.

4. Disputa entre semantica de estado e OOD extremo

- `ood_08`: ao combinar evento extremo com rotulo de estado, o sistema preservou o OOD, mas nao manteve a classificacao como estado operacional.

## Melhorias futuras recomendadas

- ampliar o roteamento deterministico para perguntas de arquitetura, fallback e banco vetorial;
- endurecer a politica de resposta quando nao houver documento, reduzindo checklist e prescricao residual;
- revisar a separacao entre `rolamento_inner` e `rolamento_outer`, incluindo features, proximidade estatistica e criterios de classe;
- revisar classes mais frageis como `cocked_rotor`, `polia` e estados operacionais sob OOD extremo;
- introduzir uma politica explicita para conflitos entre `state`, `fault` e `OOD`, priorizando a semantica correta do caso.

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
