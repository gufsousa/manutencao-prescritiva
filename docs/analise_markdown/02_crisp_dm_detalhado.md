# CRISP-DM Detalhado para o Projeto de Manutenção Prescritiva

## 1. Entendimento do Negócio

### Objetivo de negócio

Construir uma solução capaz de apoiar manutenção prescritiva em máquinas rotativas a partir de dados de sensores e documentação técnica interna. O sistema precisa ir além de apontar anomalias: ele deve sugerir o que fazer, com base em casos históricos semelhantes e procedimentos já documentados.

### Problema central

Quando um novo evento vibracional chega ao sistema, a empresa quer:

1. localizar eventos historicamente semelhantes;
2. entender qual falha é mais provável;
3. consultar documentos técnicos relacionados;
4. devolver uma orientação operacional objetiva e auditável.

### Critérios de sucesso de negócio

- reduzir ambiguidade na triagem de falhas;
- acelerar a resposta da manutenção;
- apoiar técnicos com evidências e procedimento associado;
- evitar recomendações sem base documental;
- permitir evolução do sistema com novos eventos e novos documentos.

### Restrições identificadas

- o sistema deve priorizar problemas com documentação existente;
- falhas fora da base devem gerar recusa controlada ou encaminhamento;
- o ambiente-alvo pode exigir operação local e/ou com recursos limitados;
- a solução precisa ser explicável para avaliação técnica.

## 2. Entendimento dos Dados

### Fontes de dados

- `data/raw/banner.csv`: histórico de sinais industriais com rótulo de falha.
- `data/raw/banner.xlsx`: aparente versão paralela do dataset, com indícios de formatação inconsistente.
- `data/raw/Doc1.pdf` a `Doc6.pdf`: procedimentos técnicos de inspeção e correção.
- `docs/*.pdf` e `docs/*.docx`: documentação do problema, arquitetura e fundamentação.

### Estrutura principal do CSV

O dataset possui 26 colunas, incluindo:

- timestamp de aquisição (`created_at`);
- temperatura em Fahrenheit e Celsius;
- velocidades RMS e de pico nos eixos `x` e `z`;
- acelerações RMS, de pico e de alta frequência;
- curtose e crest factor;
- rotação (`rpm`);
- rótulo da falha (`fault`).

### Hipóteses iniciais sobre os dados

- a classificação depende fortemente de padrões vibracionais multivariados;
- a rotação influencia a assinatura da falha;
- parte dos rótulos representa subclasses ou contextos de operação;
- a coluna `fault` mistura tipo de defeito com condição experimental.

### Diagnóstico inicial de qualidade

- há muitos rótulos semanticamente equivalentes com grafias diferentes;
- há classes raras e possivelmente ruidosas;
- existem registros de motor desligado e condições normais que precisam de tratamento próprio;
- a planilha Excel não deve ser usada como fonte primária sem validação adicional.

### Perguntas analíticas prioritárias

1. Quais classes realmente representam o mesmo defeito?
2. Quais atributos mais separam falhas por faixa de rpm?
3. Há desequilíbrio severo de classes?
4. Quais classes possuem documentação procedural clara?
5. Como tratar classes novas ou pouco representadas?

## 3. Preparação dos Dados

### 3.1 Inventário e rastreabilidade

- criar dicionário de dados;
- registrar origem de cada arquivo;
- associar cada falha a um documento técnico, quando existir.

### 3.2 Limpeza e padronização

- corrigir erros de digitação em `fault`;
- separar o nome canônico da falha de seus modificadores de contexto;
- transformar sufixos como `_2`, `_3`, `_carga`, `_pos_2`, `_adxl`, `_novo` em metadados estruturados;
- verificar duplicidades e possíveis registros inconsistentes.

### 3.3 Engenharia de atributos

- normalizar sinais por faixa de rpm;
- derivar features agregadas por janela, caso o fluxo de produção use série curta e não só evento isolado;
- estudar razões entre eixos `x/z`, assimetria de picos, envelopes e agrupamentos por regime operacional;
- definir conjunto mínimo de atributos para baseline interpretável.

### 3.4 Particionamento

- criar separação treino/validação/teste sem vazamento temporal;
- avaliar também cortes por rpm;
- reservar subconjuntos para falhas novas e casos sem documento.

### 3.5 Preparação documental

- extrair texto e metadados dos PDFs de procedimento;
- quebrar documentos em chunks por seção: objetivo, sintomas, causas, ferramentas, segurança, diagnóstico, correção e validação;
- indexar cada chunk com tags de falha, componente e ação.

## 4. Modelagem

### Estratégia recomendada

Adotar arquitetura híbrida, em vez de delegar tudo a um LLM.

### 4.1 Camada numérica

Objetivo: apontar eventos similares e falha provável.

Possíveis abordagens:

- baseline com k-NN em dados padronizados;
- distância cosseno ou euclidiana ponderada;
- clustering exploratório por família de falha;
- classificador supervisionado interpretável como Random Forest ou XGBoost, se o foco for performance;
- métrica de confiança baseada em distância para detectar casos desconhecidos.

### 4.2 Camada simbólica/regras

Objetivo: controlar segurança e coerência.

- se a confiança do diagnóstico for baixa, devolver incerteza explícita;
- se não houver documento mapeado para a falha, bloquear prescrição;
- se o evento estiver fora da faixa de operação conhecida, sinalizar extrapolação;
- se houver conflito entre top-k vizinhos, apresentar hipóteses em vez de afirmação única.

### 4.3 Camada documental/RAG

Objetivo: recuperar o procedimento mais relevante.

- usar embeddings para busca semântica dos trechos;
- reordenar resultados por correspondência de falha e sintomas;
- priorizar seções operacionais sobre introduções longas;
- manter referência do documento e da seção usada.

### 4.4 Camada LLM

Objetivo: montar a resposta final, não decidir sozinho a falha.

Entradas do LLM:

- falha provável e score;
- eventos históricos mais parecidos;
- trechos documentais recuperados;
- regras de recusa e escopo.

Saída esperada:

- resumo do problema;
- evidências do diagnóstico;
- inspeções recomendadas;
- ação corretiva sugerida;
- riscos e cautelas;
- indicação de ausência de cobertura, quando aplicável.

## 5. Avaliação

### 5.1 Avaliação da camada numérica

- `top-1` e `top-k accuracy`;
- matriz de confusão por família de falha;
- análise por rpm;
- sensibilidade a classes raras;
- capacidade de separar normal x falha.

### 5.2 Avaliação da recuperação documental

- precisão dos chunks recuperados por falha;
- cobertura de documentos por classe;
- utilidade prática do trecho recuperado;
- latência de busca.

### 5.3 Avaliação da resposta prescritiva

- a resposta cita a falha correta?
- a recomendação está suportada por documento?
- a resposta evita inventar procedimento não documentado?
- o formato é claro para operador/técnico?

### 5.4 Critérios mínimos de aceite

- diagnóstico consistente para as classes principais;
- recusa correta para falhas sem documento;
- rastreabilidade entre entrada, diagnóstico e documento usado;
- demonstração fim a fim executável.

## 6. Implantação

### Produto mínimo viável

Um fluxo com:

1. entrada em JSON;
2. normalização e análise de similaridade;
3. recuperação documental;
4. geração da resposta prescritiva;
5. exibição em notebook, API ou app simples.

### Componentes sugeridos

- armazenamento local do dataset limpo;
- índice vetorial para documentos;
- serviço de inferência numérica;
- módulo de regras/segurança;
- camada de apresentação.

### Logging e governança

- registrar entrada, diagnóstico, score e documentos usados;
- registrar consultas recusadas e motivo;
- manter versionamento do dataset, taxonomia e base documental.

### Evolução futura

- incorporar feedback humano após execução da manutenção;
- criar reclassificação supervisionada com dados confirmados;
- versionar manuais e procedimentos;
- suportar novos tipos de falha e novos ativos.

## 7. Backlog Priorizado

### Prioridade alta

- padronizar `fault`;
- mapear falhas para documentos;
- construir baseline de similaridade;
- indexar PDFs técnicos;
- gerar resposta estruturada com recusa segura.

### Prioridade média

- completar a AED do notebook;
- criar dashboard de inspeção dos dados;
- medir desempenho por rpm e por família de falha;
- estruturar armazenamento de histórico de consultas.

### Prioridade baixa

- otimização fina de modelo;
- deploy industrial;
- interface multiusuário;
- aprendizado contínuo automatizado.

## 8. Síntese Final

Aplicando CRISP-DM a este repositório, o projeto deve ser conduzido menos como um classificador puro e mais como um sistema de apoio à decisão industrial. O valor não está só em prever a classe da falha, mas em conectar:

- padrão sensorial;
- histórico semelhante;
- procedimento técnico válido;
- resposta operacional segura.
