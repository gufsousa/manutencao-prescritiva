# Exemplo 1: evento fisicamente invalido

Entrada:
```json
{"fault":"normal","temperature_c":999,"rpm":1800,"x_rms_velocity_mm_s":1.2,"z_rms_velocity_mm_s":1.5}
```

Saida esperada:
- bloquear a analise prescritiva;
- reportar inconsistencias fisicas;
- nao buscar prescricao executiva forte.

# Exemplo 2: evento com historico mas sem documento

Entrada:
```json
{"fault":"unknown_fault","temperature_c":85,"rpm":1750,"x_rms_velocity_mm_s":7.8,"z_rms_velocity_mm_s":8.1}
```

Saida esperada:
- informar falha candidata e confianca;
- dizer que nao existe documento rastreavel aderente;
- sugerir registrar novo documento.

# Exemplo 3: pergunta livre sobre a base

Entrada:
quais documentos tem na base de dados

Saida esperada:
- listar ou resumir os documentos indexados;
- nao exigir JSON;
- deixar claro quando a resposta veio da base atual.

# Exemplo 4: duvida tecnica pura

Entrada:
como corrigir desalinhamento de motor

Saida esperada:
- responder tecnicamente com base documental;
- nao tratar como evento JSON;
- citar lastro quando existir.

# Exemplo 5: evento OOD com documento apenas aproximado

Entrada:
```json
{"fault":"desalinhamento","temperature_c":27.0,"rpm":1500,"x_rms_velocity_mm_s":3.8,"z_rms_velocity_mm_s":3.1}
```

Saida esperada:
- deixar claro que o evento caiu fora do envelope estatistico historico;
- reduzir a confianca;
- evitar checklist documental muito especifico;
- nao transformar documento recuperado em confirmacao da falha;
- priorizar recomendacao conservadora de validacao humana e nova coleta.

# Exemplo 6: evento com documento aderente e procedimento claro

Entrada:
```json
{"temperature_c":24.7,"rpm":1000,"x_rms_velocity_mm_s":2.0,"z_rms_velocity_mm_s":1.517,"x_peak_acceleration_g":0.631,"z_peak_acceleration_g":0.484,"x_rms_acceleration_g":0.114,"z_rms_acceleration_g":0.09,"x_kurtosis":2.77,"z_kurtosis":2.392,"x_crest_factor":4.269,"z_crest_factor":3.747}
```

Saida esperada:
- inferir Cocked rotor quando o historico sustentar essa hipotese;
- usar o documento mapeado como lastro real;
- sintetizar 2 a 4 acoes concretas do procedimento;
- separar sinais da analise de checklist de inspecao;
- evitar frases genericas quando houver chunk procedural claro.
