# Plano Inicial do MVP LLM-First com Streamlit

Data de referência: **4 de agosto de 2026**

## 1. Objetivo do MVP

Construir uma demonstração aderente à prova, com foco em:

- interface em `Streamlit`;
- arquitetura modular por páginas;
- `Groq` como proxy para simular o comportamento de um LLM local dentro da limitação de estação de trabalho;
- `MongoDB` como base operacional e camada de busca vetorial;
- fluxo prescritivo centrado no LLM, com ferramentas técnicas chamadas pelo agente.

## 2. Princípio de Arquitetura

Para esta prova, a solução deve ser apresentada como um sistema **LLM-first**:

- o LLM é o cérebro da aplicação;
- o histórico de sensores, a base documental e as heurísticas técnicas são ferramentas acessadas pelo LLM;
- a resposta final é construída como raciocínio prescritivo, não como saída bruta de um classificador isolado;
- a execução deve parecer compatível com uma estação de trabalho industrial, mesmo usando `Groq` neste MVP para benchmark e validação rápida.

## 3. Stack definida

### Frontend / aplicação

- `Streamlit`
- navegação multipágina nativa
- componentes modulares por responsabilidade

### LLM / inferência

- `Groq API`
- modelo padrão inicial:
  - `llama-3.1-8b-instant` para fluxo rápido
- modelos para benchmark:
  - `llama-3.1-8b-instant`
  - `llama-3.3-70b-versatile`

### Persistência e busca

- `MongoDB Atlas`
- coleção de eventos históricos
- coleção documental
- índice vetorial para chunks de documentos

### Backend lógico

- Python
- camada de serviços local
- ferramentas auxiliares invocáveis pelo agente

## 4. Leitura estratégica do uso do Groq

O `Groq` não será posicionado como arquitetura final de produção da planta. Neste MVP ele cumpre três papéis:

1. validar a experiência conversacional e prescritiva;
2. permitir benchmark de modelos sob uma narrativa de estação de trabalho limitada;
3. acelerar a prova enquanto a arquitetura continua sendo apresentada como compatível com migração para LLM local/on-premise.

Na narrativa da entrega:

- o **design da solução** é local-first;
- o **benchmark prático** usa `Groq` para simular escolhas de modelo e custo/latência;
- a futura troca para um runtime local pode ser apresentada como etapa seguinte.

## 5. Fluxo funcional do MVP

### Fluxo principal

1. usuário informa um evento de sensores em JSON ou formulário;
2. aplicação normaliza e exibe o evento;
3. agente LLM recebe o evento e decide quais ferramentas chamar;
4. ferramenta de histórico busca eventos relevantes no MongoDB;
5. ferramenta documental consulta o índice vetorial de procedimentos;
6. agente consolida evidências;
7. interface retorna:
   - falha provável;
   - justificativa;
   - documentos consultados;
   - ação prescritiva sugerida;
   - ressalvas e nível de confiança.

### Fluxo de recusa

1. evento não encontra base documental suficiente;
2. agente sinaliza limitação;
3. resposta recomenda investigação/registro adicional em vez de prescrição assertiva.

## 6. Estrutura modular proposta

### Estrutura de diretórios

```text
app/
  Home.py
  pages/
    1_Entrada_de_Evento.py
    2_Diagnostico_Prescritivo.py
    3_Base_Documental.py
    4_Historico_e_Similaridade.py
    5_Benchmark_de_Modelos.py
    6_Observabilidade.py
src/
  config/
  services/
  agents/
  prompts/
  tools/
  repositories/
  models/
  ingestion/
  benchmark/
tests/
```

### Papel de cada página Streamlit

#### `Home`

- visão geral do projeto;
- arquitetura resumida;
- status da base carregada.

#### `Entrada de Evento`

- upload/cola de JSON;
- formulário alternativo;
- validação e preview do evento.

#### `Diagnóstico Prescritivo`

- chat principal do agente;
- execução do fluxo LLM-first;
- exibição da resposta final com fontes.

#### `Base Documental`

- inspeção dos documentos indexados;
- teste de busca vetorial;
- visualização dos chunks recuperados.

#### `Histórico e Similaridade`

- consulta a eventos históricos;
- comparação por contexto operacional;
- tela de evidências que o agente pode usar.

#### `Benchmark de Modelos`

- comparação entre modelos Groq;
- latência;
- qualidade percebida;
- aderência da resposta;
- custo estimado por execução.

#### `Observabilidade`

- logs de chamadas do agente;
- ferramentas acionadas;
- documentos retornados;
- rastreabilidade da resposta.

## 7. Componentes internos do agente

### Agente principal

Responsabilidades:

- interpretar evento;
- decidir quais ferramentas chamar;
- consolidar histórico + documentação;
- produzir resposta prescritiva final.

### Ferramentas auxiliares do agente

#### `historical_events_tool`

- consulta eventos históricos relevantes no MongoDB;
- filtra por `rpm`, família ou janela temporal quando aplicável.

#### `document_retrieval_tool`

- busca chunks vetoriais dos procedimentos técnicos;
- retorna texto, origem e metadados.

#### `fault_taxonomy_tool`

- traduz rótulos variantes para famílias canônicas;
- evita que a resposta do agente fique inconsistente.

#### `event_context_tool`

- resume o contexto do evento recebido;
- prepara representação compacta para prompt.

#### `benchmark_logger_tool`

- registra latência, modelo usado, tamanho de prompt e retorno.

## 8. Estratégia de MongoDB vetorial

### Coleção `historical_events`

Objetivo:

- armazenar eventos históricos e metadados de operação.

Campos esperados:

- `event_id`
- `created_at`
- atributos de sensores
- `fault`
- `canonical_fault`
- `rpm`
- `context_tags`

### Coleção `documents`

Objetivo:

- armazenar chunks de manuais/procedimentos com embedding e metadados.

Campos esperados:

- `doc_id`
- `source_file`
- `title`
- `fault_family`
- `section`
- `chunk_text`
- `embedding`
- `tags`

### Índices

- índice textual/metadados para filtros rápidos;
- índice vetorial para busca semântica dos chunks;
- índice por `fault_family` para recuperação híbrida.

## 9. Variáveis de ambiente necessárias

As credenciais já existentes devem ficar fora do versionamento. O `.gitignore` precisa cobrir `.env`.

Variáveis mínimas para o MVP:

- `GROQ_API_KEY`
- `DEFAULT_LLM_MODEL`
- `FALLBACK_LLM_MODELS`
- `MONGO_CONNECTION_STRING`
- `MONGO_DATABASE`
- `MONGO_HISTORY_COLLECTION`
- `MONGO_DOCUMENTS_COLLECTION`
- `MONGO_ENABLED`

Variáveis recomendadas para complementar:

- `APP_ENV`
- `STREAMLIT_SERVER_PORT`
- `BENCHMARK_ENABLED`
- `EMBEDDING_PROVIDER`
- `EMBEDDING_MODEL`
- `TOP_K_DOCUMENTS`
- `TOP_K_HISTORY`

## 10. Benchmark inicial

### Objetivo

Comparar modelos `Groq` para sustentar a narrativa de escolha de modelo sob restrição de estação de trabalho.

### Métricas

- latência total por resposta;
- tempo de primeira resposta;
- número de tokens;
- consistência do diagnóstico;
- aderência ao documento recuperado;
- qualidade da prescrição;
- taxa de recusa correta.

### Cenários de teste

1. falha com forte cobertura documental;
2. falha com histórico forte e documento moderado;
3. falha sem cobertura documental;
4. evento ambíguo entre duas famílias;
5. evento em `rpm` diferente do padrão dominante.

### Resultado esperado

Definir:

- modelo default para a demo;
- modelo fallback para respostas mais complexas;
- trade-off entre velocidade e profundidade da resposta.

## 11. Fases de implementação

### Fase 1. Fundamentos do projeto

- estruturar pastas da aplicação;
- configurar `.env.example`;
- preparar dependências;
- definir contratos de dados.

### Fase 2. Base de dados e ingestão

- normalizar `banner.csv`;
- construir taxonomia canônica;
- carregar eventos no MongoDB;
- extrair/chunkar documentos e indexar embeddings.

### Fase 3. Serviços internos

- criar cliente Groq;
- criar cliente MongoDB;
- implementar ferramentas do agente;
- implementar camada de benchmark e logging.

### Fase 4. Aplicação Streamlit

- montar páginas modulares;
- implementar fluxo de entrada de evento;
- integrar chat prescritivo;
- exibir fontes e evidências.

### Fase 5. Avaliação da demo

- rodar benchmark;
- revisar prompts;
- validar respostas com documentos;
- ajustar política de recusa.

## 12. Primeira entrega de commit recomendada

O primeiro commit coerente com esta direção pode conter:

- `README.md` atualizado;
- `.gitignore` protegido para segredos;
- plano arquitetural em Markdown;
- estrutura inicial de pastas da app;
- `.env.example` alinhado ao stack Streamlit + Groq + MongoDB.

## 13. Próximo passo prático recomendado

Se seguirmos imediatamente para implementação, a ordem ideal é:

1. alinhar `.env.example` ao stack final;
2. criar a estrutura de pastas do app Streamlit;
3. definir o contrato do agente e das tools;
4. modelar ingestão para MongoDB;
5. subir a primeira página funcional da aplicação.
