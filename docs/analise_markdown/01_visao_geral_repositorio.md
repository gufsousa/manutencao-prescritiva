# Visão Geral do Repositório

## 1. Revisão

Este repositório concentra a base de um case de manutenção prescritiva com foco em máquinas rotativas. O material está dividido em três blocos principais:

- documentos orientadores do desafio em `docs/`;
- base de dados e procedimentos técnicos em `data/raw/`;
- um notebook inicial de análise exploratória em `notebooks/`.

O documento mais importante para entendimento do problema é `docs/11 - prova prtica.docx`, que descreve o desafio: receber eventos de sensores industriais, localizar padrões similares no histórico, consultar documentação técnica associada e devolver uma orientação prescritiva para manutenção.

Os PDFs em `docs/` cumprem papéis complementares:

- `Revisão LLM Manutenção Prescritiva.pdf` traz fundamentação conceitual e limitações do uso direto de LLMs em séries temporais multivariadas.
- `RAG para Manutenção Prescritiva.pdf` descreve uma arquitetura de avaliação/implementação com recuperação documental e controle de alucinação.
- `Arquitetura Manutenção Prescritiva Local.pdf` propõe uma abordagem neuro-simbólica local, separando diagnóstico numérico e geração textual.

Os PDFs em `data/raw/` são a base documental operacional do RAG. Eles representam procedimentos de diagnóstico/correção para falhas físicas específicas:

- rolamentos;
- desalinhamento;
- desbalanceamento;
- correias;
- polias;
- rotor inclinado (`cocked rotor`).

O dataset `data/raw/banner.csv` possui `166.796` registros e `26` colunas. Os dados cobrem leituras entre `2026-04-30` e `2026-06-16`, com medições de vibração, aceleração, temperatura, frequência e rotação (`rpm`), além da coluna-alvo `fault`.

Pontos fortes do acervo:

- problema de negócio está bem definido;
- há base histórica de sensores;
- há documentação técnica para apoiar prescrição;
- existe alinhamento claro entre sinais de máquina e procedimentos de manutenção.

Lacunas identificadas:

- o notebook está muito inicial e ainda não executa a AED prometida;
- não há código de ingestão, modelagem, API, interface ou pipeline RAG implementados;
- os rótulos de falha no CSV estão pouco padronizados;
- não há mapeamento explícito entre cada `fault` do dataset e o documento técnico correspondente.

## 2. Escopo

O escopo implícito do projeto, a partir dos documentos, é construir um pipeline de manutenção prescritiva com os seguintes blocos:

1. Ler um novo evento de sensores em JSON.
2. Comparar esse evento com o histórico para encontrar casos semelhantes.
3. Estimar qual falha ou grupo de falhas melhor explica o padrão observado.
4. Consultar a documentação técnica relacionada à falha detectada.
5. Gerar uma resposta orientativa com diagnóstico, evidências e ação recomendada.
6. Registrar o histórico de consultas e permitir evolução incremental da base.

O case também sugere entregáveis de engenharia além do modelo:

- arquitetura técnica para ambiente industrial;
- tratamento documental;
- visualização por dashboard, relatório ou aplicação interativa;
- organização de repositório e documentação;
- justificativa técnica das decisões tomadas.

Escopo realista deste repositório hoje:

- preparação e limpeza dos dados;
- taxonomia de falhas;
- construção de um baseline de recuperação por similaridade;
- indexação documental;
- protótipo de resposta prescritiva com regras de segurança;
- documentação de arquitetura e plano de execução.

## 3. Plano Proposto

### Fase 1. Organização e diagnóstico do acervo

- consolidar o inventário de documentos, dados e artefatos;
- padronizar nomes de falhas;
- mapear `fault -> documento(s) técnico(s) -> ação recomendada`.

### Fase 2. Qualidade e preparação dos dados

- validar tipos, faixas e unidades;
- corrigir inconsistências de rótulos;
- separar condições normais, falhas conhecidas e falhas novas;
- definir estratégia de particionamento por tempo, rotação e classe.

### Fase 3. Baseline analítico

- construir busca por similaridade entre eventos históricos;
- comparar estratégias simples, como distância euclidiana padronizada, cosseno e k-NN;
- medir top-k, estabilidade por faixa de rpm e robustez a ruído.

### Fase 4. Camada documental

- transformar os PDFs procedurais em base consultável;
- indexar por tipo de falha, sintomas, causas, instrumentos e passos de correção;
- definir política de resposta quando não houver documento correspondente.

### Fase 5. Motor prescritivo

- combinar diagnóstico numérico + recuperação documental;
- gerar resposta estruturada com: falha provável, evidências, documentos usados, ações sugeridas e ressalvas;
- bloquear prescrição para falhas sem cobertura documental.

### Fase 6. Interface e entrega

- expor um fluxo mínimo por notebook, API ou app interativo;
- incluir exemplos de consulta;
- registrar limitações, hipóteses e próximos passos.

## 4. Informações Complementares

### Leitura do dataset

Distribuição relevante de classes:

- maior volume em `rolamento_inner`, `eccentric_rotor`, `desbalanceado_1parafuso`, `cocked_rotor`, `rolamento_outer`, `rolamento_combination`, `polia`, `ventoinha` e `correia`;
- presença de famílias com sufixos como `_2`, `_3`, `_4`, `_pos_2`, `_carga`, `_novo`, `_adxl`;
- presença de registros de `motor_desligado` e condições normais.

Principais riscos de qualidade:

- erros de digitação em rótulos, como `desabalanceado_3`, `desbanlanceado_carga_3_2`, `normla_carga_3_3`, `cockecocked_adxl_0`;
- coexistência de padrões antigos e novos, como `desbalanceado_*` e `new_desbalanceado_*`;
- mistura de variações de contexto no próprio rótulo em vez de atributos separados;
- provável necessidade de normalização semântica antes de qualquer modelagem séria.

### Sobre o arquivo `banner.xlsx`

Embora aparente ser a mesma base do CSV, os valores amostrados sugerem problemas de escala/formatação em colunas numéricas. Para análise e modelagem, o CSV parece ser a fonte mais confiável.

### Sobre o notebook

O notebook tem boa intenção documental, mas ainda está incompleto:

- a introdução está escrita;
- as bibliotecas foram importadas;
- não há carregamento da base;
- não há visualizações, tratamento ou conclusões implementadas.

### Leitura arquitetural recomendada

Entre os documentos conceituais, há uma convergência útil:

- o diagnóstico da falha não deve ser delegado diretamente ao LLM;
- a parte numérica deve ser tratada por método determinístico/estatístico;
- o LLM deve atuar principalmente na orquestração e na redação da resposta prescritiva;
- o sistema precisa de mecanismos de recusa para casos sem suporte documental.

## 5. Conclusão

O repositório já possui os insumos certos para um protótipo forte de manutenção prescritiva, mas ainda está em estágio de base documental e exploração inicial. O caminho mais promissor é tratar o projeto como um sistema híbrido:

- busca de similaridade para identificar eventos comparáveis;
- taxonomia de falhas para estabilizar o vocabulário;
- RAG sobre procedimentos técnicos para justificar a prescrição;
- interface mínima para demonstrar o fluxo fim a fim.
