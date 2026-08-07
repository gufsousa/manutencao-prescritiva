# Relatorio de Cobertura Documental por Falha

Data de execucao: **7 de agosto de 2026**.

## Objetivo

Validar, de ponta a ponta, se o copiloto **so prescreve com lastro documental quando existe documento tecnicamente mapeado para a familia de falha**.

## Regra validada

- Se a falha tem documento mapeado, a resposta pode citar documento e sugerir acoes.
- Se a falha **nao** tem documento mapeado, a resposta deve:
  - recusar prescricao sustentada por documento;
  - nao citar chunks de outras familias;
  - devolver limitacao explicita da base documental.

## Falhas com documento mapeado na base atual

- `cocked_rotor`
- `correia`
- `desalinhamento`
- `desbalanceamento`
- `polia`
- `rolamento_inner`

## Falhas sem documento mapeado na base atual

- `eccentric_rotor`
- `falta_fase`
- `rolamento_ball`
- `rolamento_combination`
- `rolamento_outer`
- `ventoinha`

## Resultado consolidado

- Total de falhas reais avaliadas: `12`
- Falhas com documento mapeado: `6`
- Falhas sem documento mapeado: `6`
- Resultado confirmado apos ajuste: `12/12` cenarios aprovados

## Ajuste implementado

Antes do ajuste, a busca documental fazia fallback para chunks semanticamente parecidos mesmo quando a falha inferida **nao tinha documento proprio**. Isso permitia prescricao indevida para familias descobertas apenas no historico.

Agora o fluxo:

1. identifica a falha candidata pelo motor historico;
2. verifica se existe documento com `fault_family` exatamente mapeada para essa falha;
3. so aceita chunks recuperados como base de prescricao se esse mapeamento existir;
4. caso contrario, bloqueia a prescricao documental e devolve limitacao explicita.

## Exemplo do comportamento correto apos ajuste

### Falha com documento

- `cocked_rotor`:
  - cita `Procedimento de Cocked Rotor`;
  - devolve acoes extraidas do chunk;
  - permite resposta prescritiva.

### Falha sem documento

- `ventoinha`:
  - nao cita documento;
  - devolve `Nao ha documento tecnico suficiente para sustentar prescricao.`;
  - nao reaproveita procedimento de `polia`, `correia` ou outra familia proxima.

## Script de reproducao

Arquivo:

- `scripts/run_fault_document_coverage_check.py`

Comando:

```powershell
python scripts/run_fault_document_coverage_check.py
```

Saida JSON padrao:

- `docs/analise_markdown/fault_document_coverage_2026-08-07.json`

## Leitura tecnica

Esse teste melhora a seguranca arquitetural do copiloto porque separa:

- **classificacao historica**: pode apontar uma familia provavel;
- **prescricao documental**: so acontece quando existe lastro tecnico especifico para aquela familia.

Isso evita que similaridade semantica superficial seja confundida com cobertura procedural real.
