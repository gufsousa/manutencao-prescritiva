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
