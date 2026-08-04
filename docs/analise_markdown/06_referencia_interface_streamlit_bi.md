# Referência de Interface para o MVP Streamlit

Data de referência: **4 de agosto de 2026**

## 1. Objetivo

Definir uma direção visual e funcional para a interface do MVP em `Streamlit`, aproveitando:

- referências atuais de dashboards modernos em `Streamlit` e GitHub;
- a linguagem visual já existente no projeto React em `C:\Projetos\Manutencao-prescritva\frontend`;
- a necessidade da prova de apresentar uma solução profissional, funcional e orientada a decisão.

## 2. Referências externas encontradas

### Referência principal de estilo Streamlit

- `arnaudmiribel/neat-streamlit-dashboard`
  - GitHub: https://github.com/arnaudmiribel/neat-streamlit-dashboard

Motivo da escolha:

- é explicitamente descrito como um dashboard analítico moderno em `Streamlit`;
- prioriza clareza visual, cards, espaçamento, hierarquia e gráficos;
- serve bem como base conceitual para um app profissional sem excesso de esforço em UI.

### Referência complementar de utilitários visuais

- `streamlit-extras`
  - GitHub: https://github.com/arnaudmiribel/streamlit-extras
  - Docs: https://arnaudmiribel.github.io/streamlit-extras/

Uso esperado:

- containers estilizados;
- melhorias de layout;
- pequenos recursos visuais para elevar acabamento do app.

## 3. Referência local aproveitável

Projeto consultado:

- `C:\Projetos\Manutencao-prescritva\frontend`

Arquivos mais úteis como base visual:

- `frontend/src/index.css`
- `frontend/src/MainCanvas.jsx`
- `frontend/src/pages/EventAnalysisPage.jsx`
- `frontend/src/pages/DataLakePage.jsx`
- `frontend/src/pages/ReportsPage.jsx`
- `frontend/src/components/canvas/SurfaceCards.jsx`

## 4. O que vale a pena reaproveitar do React

### Linguagem visual

- fundo escuro técnico com contraste alto;
- cards com borda discreta e cantos arredondados;
- detalhes em ciano, azul e âmbar para destaque de estados;
- blocos densos, mas bem hierarquizados;
- tom de “centro de operações” em vez de “landing page”.

### Padrões funcionais

- cards de métricas;
- seções com título, descrição e ícone;
- agrupamento de evidências;
- painéis de relatório;
- página de dados com tabela e KPIs;
- gráficos de inferência com barras e comparativos.

### O que não vamos manter

- a lógica de canvas/chat como eixo dominante da navegação;
- a cara de workspace horizontal com sidebar retrátil como componente principal;
- qualquer traço de layout “canva-first”.

## 5. Tradução proposta para Streamlit

Em vez de reproduzir a UI React literalmente, a adaptação ideal para `Streamlit` é:

- navegação multipágina lateral;
- páginas com cara de BI e operação técnica;
- uso de `st.columns`, `st.container`, `st.tabs`, `st.metric`, `plotly` e CSS customizado;
- blocos de decisão e rastreabilidade integrados às páginas.

## 6. Direção de layout recomendada

### Estilo geral

- fundo principal escuro: azul-grafite / petróleo;
- superfícies levemente mais claras;
- borda fina azul-ardósia;
- cor de destaque:
  - ciano para inferência e tecnologia;
  - âmbar para alerta/risco;
  - verde para documento/rastreabilidade;
- tipografia limpa e sóbria;
- espaçamento mais generoso que o padrão do Streamlit.

### Sensação desejada

- parecer uma plataforma técnica de manutenção e decisão industrial;
- parecer mais “BI operacional + copiloto técnico”;
- não parecer protótipo acadêmico simples.

## 7. Estrutura de páginas recomendada

### 1. `Home`

Função:

- visão executiva do projeto;
- KPIs gerais da base;
- status do LLM, Mongo e benchmark;
- resumo do pipeline.

Conteúdo visual:

- hero técnico curto;
- 4 a 6 cards de métricas;
- gráfico resumido de distribuição de falhas;
- bloco “arquitetura atual”.

### 2. `BI de Inferências`

Função:

- substituir o foco “canvas” por uma página de BI orientada à prova;
- mostrar desempenho, distribuição e leitura das inferências.

Conteúdo visual:

- KPIs de inferência;
- barras de famílias de falha;
- pizza ou barra empilhada por cobertura documental;
- heatmap ou scatter por `rpm` e variável vibracional;
- ranking de documentos mais acionados;
- histórico de respostas do agente.

Esta é a página que entra no lugar da sensação “canva-first”.

### 3. `Diagnóstico Prescritivo`

Função:

- permitir entrada de evento e resposta do agente;
- concentrar a experiência principal da prova.

Conteúdo visual:

- formulário/JSON de entrada;
- cards do evento;
- resposta estruturada do agente;
- evidências usadas;
- documentos relacionados.

### 4. `Base Documental`

Função:

- exibir os documentos indexados;
- demonstrar busca vetorial e rastreabilidade.

Conteúdo visual:

- tabela documental;
- filtros por família;
- resultados de busca;
- chunks retornados;
- score/relevância.

### 5. `Histórico Operacional`

Função:

- explorar o `banner.csv` e/ou eventos persistidos no MongoDB.

Conteúdo visual:

- KPIs da base;
- distribuição por falha;
- distribuição por `rpm`;
- amostra tabular;
- filtros operacionais.

### 6. `Benchmark de Modelos`

Função:

- comparar respostas dos modelos do `Groq`;
- sustentar a discussão de latência e aderência.

Conteúdo visual:

- tabela comparativa;
- barras de latência;
- score de aderência;
- custo estimado;
- melhor modelo por cenário.

### 7. `Observabilidade`

Função:

- dar rastreabilidade técnica à decisão do agente.

Conteúdo visual:

- tools acionadas;
- tempo por etapa;
- documentos usados;
- logs resumidos;
- status de execução.

## 8. Componentes visuais que devemos replicar em Streamlit

### Cards de métrica

Inspirados em:

- `MetricPill`
- `HighlightCard`
- `SectionCard`

Tradução em Streamlit:

- containers com CSS customizado;
- `st.metric` estilizado;
- blocos HTML leves para rotular e destacar.

### Seções com cabeçalho

Inspiradas em:

- `SectionCard` do React

Tradução em Streamlit:

- containers com ícone, título e descrição;
- grid com blocos internos;
- uso de bordas e sombra leve.

### Painéis de BI

Inspirados em:

- `DataLakePage`
- blocos da `EventAnalysisPage`

Tradução em Streamlit:

- `Plotly` para barras, scatter, heatmap e séries;
- tabelas filtráveis;
- painéis laterais com resumo textual.

## 9. Biblioteca visual recomendada no app

### Base principal

- `streamlit`
- `plotly`
- `pandas`

### Complementos desejáveis

- `streamlit-extras`
- CSS customizado via `st.markdown(..., unsafe_allow_html=True)`

## 10. Regras de design para evitar perda de tempo

1. Não tentar reproduzir React pixel a pixel.
2. Reaproveitar a hierarquia visual, não a implementação.
3. Priorizar telas de BI e diagnóstico, não animação.
4. Manter todos os componentes em um sistema de estilo único.
5. Fazer o app parecer deliberado e técnico desde o primeiro commit.

## 11. Decisão final de interface

A direção recomendada para implementação é:

- `Streamlit` multipágina;
- estilo escuro técnico inspirado no React local;
- referência externa de acabamento visual em `neat-streamlit-dashboard`;
- página central de **BI de Inferências** no lugar de uma experiência “canvas-first”;
- chat/agente presente apenas onde agrega valor, sem dominar a navegação.

## 12. Próximo passo de implementação

Ao começar a app, o ideal é criar primeiro:

1. um tema CSS global;
2. a `Home`;
3. a página `BI de Inferências`;
4. a página `Diagnóstico Prescritivo`.

Essas três páginas já devem estabelecer a cara profissional do MVP.
