# Análise Exploratória e Insights do Dataset `banner.csv`

## 1. Resumo executivo

- A base possui **166.796 registros** e **26 colunas originais** no arquivo analítico principal.
- O período coberto vai de **30/04/2026 17:17** até **16/06/2026 18:59**.
- Não há valores faltantes e não há duplicidade de `id`.
- Existem **151 rótulos originais** de falha, mas eles se consolidam em **17 famílias canônicas**.
- Aproximadamente **72.82%** dos registros pertencem a famílias com documentação técnica diretamente associável ao acervo atual.

## 2. O que a exploração mostrou

### Integridade estrutural

- O dataset está sólido para AED e modelagem inicial.
- A maior fragilidade não está nos valores numéricos, mas na taxonomia de `fault`.
- O arquivo `banner.xlsx` não é necessário para a análise; o `banner.csv` é a fonte confiável.

### Taxonomia de falhas

- Os rótulos originais misturam tipo de defeito, variação de ensaio, posição, carga, geração do experimento e erros de digitação.
- Sem normalização, a modelagem ficará inflada em número de classes e perderá consistência operacional.
- A consolidação em famílias canônicas é um passo obrigatório antes de qualquer pipeline prescritivo.

### Cobertura documental

- Há boa cobertura documental para rolamentos, desalinhamento, desbalanceamento, correias, polias e `cocked_rotor`.
- Famílias como `eccentric_rotor`, `ventoinha` e `falta_fase` aparecem na base, mas ainda não têm procedimento correspondente no acervo atual.
- Isso exige política de recusa: o sistema pode diagnosticar ou sugerir hipótese, mas não deve prescrever sem documento associado.

### Regime operacional

- A rotação está concentrada em poucos patamares (`0`, `500`, `1000`, `2000` e `3000` rpm).
- Comparações por similaridade devem respeitar o contexto de `rpm` para evitar falsos vizinhos.

### Sinal das variáveis

- As variáveis vibracionais mostram separação útil entre famílias documentadas.
- Temperatura, velocidade RMS, aceleração de pico, curtose e crest factor carregam sinal analítico relevante.
- A separação não é perfeita em todas as classes; por isso, o modelo deve combinar múltiplas variáveis e contexto operacional.

## 3. Top 10 rótulos originais

- `rolamento_inner`: 13.000 registros
- `eccentric_rotor`: 11.808 registros
- `desbalanceado_1parafuso`: 10.079 registros
- `cocked_rotor`: 10.000 registros
- `rolamento_outer`: 10.000 registros
- `rolamento_combination`: 10.000 registros
- `rolamento_ball`: 9.004 registros
- `polia`: 9.000 registros
- `ventoinha`: 9.000 registros
- `correia`: 9.000 registros

## 4. Famílias canônicas mais frequentes

- `rolamento_inner`: 17.712 registros (documentada)
- `eccentric_rotor`: 16.497 registros (sem documento)
- `normal`: 15.077 registros (sem documento)
- `rolamento_outer`: 14.813 registros (documentada)
- `rolamento_combination`: 14.550 registros (documentada)
- `cocked_rotor`: 14.275 registros (documentada)
- `rolamento_ball`: 13.704 registros (documentada)
- `desbalanceamento`: 13.237 registros (documentada)
- `ventoinha`: 12.299 registros (sem documento)
- `polia`: 12.000 registros (documentada)
- `correia`: 11.999 registros (documentada)
- `desalinhamento`: 9.178 registros (documentada)

## 5. Distribuição de rpm

- `0 rpm`: 658 registros (0.39%)
- `500 rpm`: 55.857 registros (33.49%)
- `1000 rpm`: 53.414 registros (32.02%)
- `2000 rpm`: 55.160 registros (33.07%)
- `3000 rpm`: 1.707 registros (1.02%)

## 6. Famílias sem suporte documental direto no acervo atual

- `eccentric_rotor`: 16.497 registros
- `normal`: 15.077 registros
- `ventoinha`: 12.299 registros
- `falta_fase`: 800 registros
- `motor_desligado`: 497 registros
- `teste`: 99 registros
- `outros`: 52 registros
- `transiente_aceleracao`: 7 registros

## 7. Medianas das variáveis-chave por família documentada

| família | temperature_c | z_rms_velocity_mm_s | x_rms_velocity_mm_s | z_peak_acceleration_g | x_peak_acceleration_g |
|---|---:|---:|---:|---:|---:|
| cocked_rotor | 23.28 | 1.503 | 2.296 | 0.492 | 0.574 |
| desbalanceamento | 23.41 | 1.747 | 2.558 | 0.498 | 0.576 |
| rolamento_ball | 22.58 | 1.596 | 2.445 | 0.513 | 0.607 |
| rolamento_combination | 23.13 | 1.589 | 2.455 | 0.513 | 0.603 |
| rolamento_inner | 22.97 | 1.612 | 2.423 | 0.5 | 0.59 |
| rolamento_outer | 22.56 | 1.589 | 2.399 | 0.513 | 0.595 |

## 8. Insights práticos

- O repositório já permite construir um **baseline forte de busca por similaridade**.
- O próximo ganho de qualidade não virá de um modelo mais complexo, e sim de **padronização semântica e mapeamento fault-documento**.
- O motor prescritivo deve ser **híbrido**: diagnóstico numérico + recuperação documental + geração textual controlada.
- O notebook finalizado sustenta bem a narrativa técnica do case e ajuda a justificar decisões de arquitetura.

## 9. Próximos passos recomendados

1. Criar um dicionário canônico de falhas e variantes.
2. Mapear cada família documentada aos PDFs procedurais correspondentes.
3. Segmentar a busca por similaridade por faixa de `rpm`.
4. Criar baseline de recuperação histórica e avaliar top-k por família.
5. Integrar a camada documental com regra explícita de recusa para falhas sem cobertura.
