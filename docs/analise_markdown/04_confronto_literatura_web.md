# Confronto da AED com a Literatura Web

Data da revisão: **4 de agosto de 2026**

## Síntese

O resultado da análise exploratória está alinhado com a literatura recente sobre manutenção preditiva/prescritiva, uso de LLMs em séries temporais e uso de RAG para recuperação de procedimentos técnicos. A convergência principal é esta:

- o diagnóstico sobre dados sensoriais não deve depender apenas de LLM;
- a camada documental com RAG é útil, mas precisa de rastreabilidade e validação humana;
- a etapa mais importante antes da modelagem é a preparação semântica do dado, especialmente taxonomia de falhas e contexto operacional.

Ao mesmo tempo, para **esta prova específica**, há uma adaptação estratégica importante: embora a literatura seja mais conservadora, a arquitetura da entrega deve priorizar um **LLM local como protagonista**, porque o enunciado e o documento `C:\Projetos\Manutencao-prescritiva-main\docs\Arquitetura Manutenção Prescritiva Local.pdf` sugerem fortemente esse direcionamento.

Em outras palavras:

- a literatura continua útil para evitar erros conceituais;
- mas a forma de empacotar a solução para avaliação deve ser **LLM-first**, rodando em estação local;
- ferramentas numéricas clássicas ainda podem existir, porém como capacidade interna do agente, e não como narrativa central da entrega.

## Onde a nossa AED bate com a literatura

### 1. LLM sozinho não é a melhor peça para o diagnóstico numérico

A nossa AED indicou que o problema depende fortemente de variáveis vibracionais, contexto de `rpm` e consistência taxonômica. Isso é consistente com a literatura mais recente sobre LLMs para séries temporais, que destaca potencial, mas também limitações práticas relacionadas a estrutura temporal complexa, escassez de dados anotados e custo computacional.

Referência:

- Feifei Shi et al., *Large Language Models for Time Series Analysis: Techniques, Applications, and Challenges* (arXiv, 21 de maio de 2025): https://arxiv.org/html/2506.11040v1

Leitura útil para o projeto:

- a revisão aponta que LLMs podem agregar contexto e multimodalidade;
- ao mesmo tempo, reforça que séries temporais continuam exigindo tratamento especializado;
- isso sustenta a decisão de separar diagnóstico numérico e geração textual.

### 2. Contexto temporal e padrão operacional importam muito

A nossa análise mostrou que `rpm` é uma variável estruturante e que comparações sem respeitar regime operacional podem distorcer a similaridade. Isso conversa com achados experimentais em literatura sobre LLMs para séries temporais: modelos se comportam melhor quando o padrão possui tendência/periodicidade clara e pioram em estruturas temporais mais complexas.

Referência:

- *Time Series Forecasting with LLMs: Understanding and Enhancing Model Capabilities* (arXiv, 16 de fevereiro de 2024): https://arxiv.org/html/2402.10835v1

Leitura útil para o projeto:

- padrões e estrutura importam;
- o modelo precisa de contexto;
- em nosso caso, isso reforça o particionamento por `rpm`, família de falha e condição operacional.

### 3. RAG é promissor para troubleshooting, mas não deve operar sem fonte e validação

A AED e os documentos do repositório já apontavam que a prescrição deve ser restrita a falhas com cobertura documental. Isso é muito coerente com experimentos recentes em sistemas industriais complexos, nos quais RAG melhora a recuperação de procedimentos, mas ainda exige devolução das fontes e checagem antes da execução.

Referência:

- Maria Teresa Rossi et al., *“Where is My Troubleshooting Procedure?”: Studying the Potential of RAG in Assisting Failure Resolution of Large Cyber-Physical System* (ICSE-SEIP 2026): https://arxiv.org/html/2601.08706v2

Leitura útil para o projeto:

- RAG ajuda operadores a encontrar procedimentos mais rápido;
- respostas precisam vir acompanhadas das fontes;
- a formulação da pergunta e a terminologia de domínio afetam a qualidade da recuperação.

### 4. O projeto está aderente ao movimento de manutenção prescritiva com RAG

Nosso direcionamento para um motor híbrido com diagnóstico histórico + recuperação documental + resposta estruturada também aparece em trabalhos recentes voltados explicitamente a manutenção prescritiva assistida por RAG.

Referência:

- Chitranshu Harbola e Anupam Purwar, *Prescriptive Agents based on RAG for Automated Maintenance (PARAM)* (arXiv, 20 de agosto de 2025): https://arxiv.org/html/2508.04714v2

Leitura útil para o projeto:

- a proposta combina classificação/anomalia com recuperação de manuais;
- a saída é estruturada em ações, checklist e medidas corretivas;
- isso é muito próximo do fluxo pretendido para este repositório.

### 5. A operação do RAG precisa de observabilidade e avaliação contínua

A nossa AED concluiu que ainda falta governança antes da prescrição. A literatura de operação de RAG reforça isso: qualidade do dado recuperado, atualização da base e observabilidade do pipeline são partes críticas da confiabilidade do sistema.

Referência:

- *RAGOps: Operating and Managing Retrieval-Augmented Generation Pipelines* (arXiv, 3 de junho de 2025): https://arxiv.org/html/2506.03401v1

Leitura útil para o projeto:

- não basta montar embeddings e responder;
- é preciso monitorar recuperação, qualidade e mudanças da base;
- isso reforça a necessidade de logging, avaliação e versionamento documental.

### 6. A necessidade de lidar com desbalanceamento, dimensionalidade e hibridização também aparece na literatura de PdM

Nossa análise encontrou forte heterogeneidade na coluna `fault`, classes raras e necessidade de consolidar famílias antes de modelar. Isso converge com revisões recentes de PdM, que destacam desequilíbrio de classes, alta dimensionalidade e valor de abordagens híbridas.

Referência:

- Ainaz Jamshidi et al., *A Survey of Predictive Maintenance Methods: An Analysis of Prognostics via Classification and Regression* (arXiv, 25 de junho de 2025): https://arxiv.org/pdf/2506.20090

Leitura útil para o projeto:

- classificação e regressão têm trade-offs diferentes;
- desbalanceamento e espaço de atributos são desafios centrais;
- abordagens híbridas são uma tendência consistente.

## O que a literatura sugere além da nossa AED

Sim, há espaço para **outra análise prévia** antes de partir para modelagem ou RAG em produção. As mais importantes são:

### 1. Análise semântica e taxonômica das falhas

Objetivo:

- converter variantes como `_2`, `_carga`, `_pos_2`, `_novo`, `_adxl` e erros de digitação em atributos estruturados.

Por que é necessária:

- reduz inflação artificial de classes;
- aproxima o dataset do vocabulário técnico da manutenção;
- melhora avaliação e recuperabilidade documental.

### 2. Matriz `família de falha -> documento técnico -> ação prescritiva`

Objetivo:

- deixar explícito quais falhas podem receber prescrição e quais devem gerar recusa.

Por que é necessária:

- a literatura de RAG industrial reforça necessidade de fonte rastreável;
- sem esse mapa, o motor prescritivo corre risco de responder fora do escopo documental.

### 3. Análise por regime operacional

Objetivo:

- verificar separação entre classes por `rpm`, carga e demais contextos de ensaio.

Por que é necessária:

- a similaridade entre assinaturas vibracionais depende do contexto;
- a literatura de séries temporais indica que estrutura do sinal muda bastante a dificuldade do problema.

### 4. Análise de ferramentas técnicas auxiliares para o agente

Objetivo:

- definir quais rotinas ou heurísticas o LLM poderá acionar localmente para apoiar a inferência.

Por que é necessária:

- permite manter aderência à expectativa de um sistema centrado em LLM;
- evita que a entrega pareça apenas um pipeline tradicional de ML;
- ajuda a transformar processamento técnico em capacidade do agente.

### 5. Análise de novidade e recusa

Objetivo:

- detectar quando o evento está fora das famílias documentadas ou fora do regime conhecido.

Por que é necessária:

- manutenção prescritiva segura depende de saber quando **não** recomendar;
- isso é coerente com o escopo do case e com a literatura.

## Conclusão prática

O confronto com a literatura não invalida a AED; pelo contrário, ele a fortalece. O que fizemos até aqui está bem alinhado com o estado da arte para este tipo de problema:

- usar a base de sensores para diagnóstico estruturado;
- tratar `rpm` e contexto operacional como parte do problema;
- usar RAG para localizar procedimento técnico;
- devolver respostas com fonte e política de recusa.

Para a estratégia desta prova, a conclusão prática precisa ser levemente ajustada:

- a solução deve ser apresentada como um **agente local baseado em LLM**;
- as rotinas técnicas entram como suporte à inferência do agente;
- a narrativa de arquitetura precisa enfatizar a execução em estação de trabalho, sem dependência de API externa.

O passo certo agora não é aumentar complexidade estatística isolada, e sim melhorar a base de decisão e a arquitetura do agente:

1. padronizar falhas;
2. mapear falha-documento;
3. definir ferramentas locais que o LLM poderá usar;
4. estruturar o RAG técnico;
5. só então avançar para o pipeline prescritivo fim a fim.
