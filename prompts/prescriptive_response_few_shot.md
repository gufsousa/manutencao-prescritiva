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
