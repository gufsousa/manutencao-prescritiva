# Plano de Implementação do MVP Streamlit

Data de referência: **4 de agosto de 2026**

## 1. Objetivo

Implementar um MVP funcional de manutenção prescritiva com:

- `Streamlit` multipágina;
- agente `LLM-first` usando `Groq` com modelos pequenos no desenvolvimento;
- MongoDB para eventos, documentos, chunks e vetores;
- camada semântica reaproveitada e adaptada do projeto `C:\Projetos\Manutencao-prescritva`;
- ingestão de documentos com chunking e vetorização;
- benchmark operacional dos modelos.

## 2. Estratégia de desenvolvimento

Para reduzir custo e manter aderência à prova:

- usar `llama-3.1-8b-instant` como modelo default de desenvolvimento;
- permitir benchmark com `llama-3.3-70b-versatile` apenas em cenários controlados;
- concentrar o uso de tokens nas respostas finais e benchmarks curtos;
- manter o agente como orquestrador central;
- deixar busca histórica, chunking, vetorização e taxonomia como tools locais chamadas pelo fluxo.

## 3. Etapas de implementação

### 1. Fundação do projeto

Escopo:

- criar estrutura de pastas da app e do `src`;
- configurar tema, settings e contratos básicos;
- proteger segredos com `.env`;
- alinhar `.env.example`.

Teste desta etapa:

1. importar os módulos principais sem erro;
2. validar leitura do `.env`;
3. validar que a app sobe sem quebrar por dependência ausente.

### 2. Camada semântica

Escopo:

- portar/adaptar o léxico de falhas;
- criar canonicalização dos rótulos;
- expor catálogo para uso em ingestão, páginas e agente.

Teste desta etapa:

1. rótulos equivalentes devem cair na mesma família;
2. rótulos com erro comum devem ser reconhecidos;
3. estados operacionais devem ser distinguidos de falhas.

### 3. Ingestão do histórico de eventos

Escopo:

- carregar `banner.csv`;
- normalizar campos;
- derivar `canonical_fault`;
- preparar amostras e estatísticas para BI e busca histórica;
- persistir no MongoDB.

Teste desta etapa:

1. ingestão cria registros na coleção histórica;
2. `canonical_fault` é preenchido;
3. métricas da base batem com o CSV original.

### 4. Ingestão documental

Escopo:

- ler os PDFs de `data/raw`;
- extrair texto;
- dividir em chunks;
- gerar vetores;
- persistir documentos e chunks vetorizados no MongoDB.

Teste desta etapa:

1. cada PDF gera ao menos um chunk útil;
2. cada chunk persiste com texto, metadados e vetor;
3. busca por família de falha retorna documentos relacionados.

### 5. Busca histórica

Escopo:

- criar tool de recuperação de eventos por contexto;
- considerar `rpm`, falha canônica e similaridade numérica;
- devolver evidências de forma compacta para o agente.

Teste desta etapa:

1. evento de entrada retorna vizinhos relevantes;
2. filtro por `rpm` funciona;
3. a resposta da tool é serializável para prompt.

### 6. Busca vetorial documental

Escopo:

- criar vetores locais para chunks;
- tentar consulta vetorial no Mongo quando disponível;
- manter fallback local por similaridade cosseno;
- devolver documentos, trechos e score.

Teste desta etapa:

1. consulta textual simples retorna chunks coerentes;
2. consulta por família melhora a precisão;
3. fallback local funciona mesmo sem índice vetorial configurado no Atlas.

### 7. Motor do agente

Escopo:

- criar o pipeline do agente;
- montar toolbelt:
  - normalização do evento;
  - taxonomia;
  - recuperação histórica;
  - recuperação documental;
  - benchmark logger;
- produzir resposta final com evidências e prescrição.

Teste desta etapa:

1. evento válido gera resposta completa;
2. evento sem documento gera recusa controlada;
3. evento inválido é bloqueado;
4. a resposta cita fontes recuperadas.

### 8. Interface Streamlit

Escopo:

- implementar páginas:
  - `Home`
  - `BI de Inferências`
  - `Diagnóstico Prescritivo`
  - `Base Documental`
  - `Histórico Operacional`
  - `Benchmark de Modelos`
  - `Observabilidade`
- aplicar tema CSS consistente.

Teste desta etapa:

1. todas as páginas carregam;
2. nenhum import quebra a navegação;
3. os gráficos renderizam;
4. páginas exibem dados reais e não placeholders vazios.

### 9. Benchmark de modelos

Escopo:

- comparar modelos `Groq` em poucos cenários;
- registrar latência, qualidade percebida e aderência documental;
- exibir os resultados no app.

Teste desta etapa:

1. benchmark roda com modelo default;
2. benchmark roda com modelo alternativo;
3. resultados ficam persistidos para visualização.

### 10. Observabilidade e logs

Escopo:

- registrar entrada, tools acionadas, tempo, documentos retornados e modelo usado;
- exibir tudo em tela técnica.

Teste desta etapa:

1. cada inferência gera log;
2. benchmark também gera log;
3. o painel consegue listar execuções recentes.

## 4. Cenários de teste finais

### Cenário A. Falha documentada

Entrada:

- evento coerente de uma falha com procedimento disponível.

Resultado esperado:

- o agente identifica hipótese provável;
- recupera histórico;
- recupera chunks documentais;
- entrega prescrição com fonte.

### Cenário B. Falha sem documento

Entrada:

- evento ligado a família sem cobertura documental atual.

Resultado esperado:

- o agente reconhece limitação documental;
- evita prescrição forte;
- orienta investigação adicional.

### Cenário C. Evento inválido

Entrada:

- JSON com inconsistência física clara.

Resultado esperado:

- o fluxo é bloqueado;
- a interface mostra erro de validação.

### Cenário D. Busca documental

Entrada:

- termo/consulta de falha na página documental.

Resultado esperado:

- chunks relevantes aparecem com score e origem.

### Cenário E. BI operacional

Entrada:

- navegação na página BI.

Resultado esperado:

- KPIs, gráficos e ranking carregam com base real.

## 5. Critério de pronto

O MVP só será considerado pronto quando:

1. todas as páginas carregarem sem erro;
2. a ingestão histórica funcionar;
3. a ingestão documental com chunking e vetores funcionar;
4. o agente responder com `Groq` e tools locais;
5. benchmark e observabilidade estiverem acessíveis na interface;
6. existir um fluxo demonstrável fim a fim.
