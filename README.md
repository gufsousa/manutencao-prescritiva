# Manutenção Prescritiva

Projeto base para estudo e prototipação de um pipeline de manutenção prescritiva aplicado a máquinas rotativas, usando dados de sensores, histórico de falhas e documentação técnica de manutenção.

## Objetivo

Construir a base analítica e documental para uma solução capaz de:

1. receber um novo evento de sensores;
2. localizar eventos historicamente semelhantes;
3. inferir a família de falha mais provável;
4. recuperar procedimentos técnicos relevantes;
5. apoiar uma resposta prescritiva rastreável e segura.

## Estrutura do repositório

- `data/raw/`: base histórica de sensores e documentos técnicos de falha.
- `docs/`: material de referência do case, arquitetura e análises em Markdown.
- `notebooks/`: análises exploratórias e experimentos.
- `scripts/`: utilitários de apoio à geração de artefatos analíticos.

## Status atual

Na data de **4 de agosto de 2026**, o repositório já contém:

- inventário e síntese dos documentos do projeto;
- AED concluída sobre `data/raw/banner.csv`;
- notebook executável com análise de qualidade, falhas, `rpm`, cobertura documental e prontidão prescritiva;
- documentação inicial em Markdown com visão geral, CRISP-DM e insights.

## Principais achados da AED

- o dataset principal (`banner.csv`) está estruturalmente íntegro, sem faltantes e sem duplicidade de `id`;
- a principal fragilidade está na coluna `fault`, que mistura defeito, contexto experimental e erros de digitação;
- os `151` rótulos originais se consolidam em `17` famílias canônicas;
- cerca de `72,82%` dos registros já pertencem a famílias com documentação técnica associável no acervo atual;
- a rotação (`rpm`) precisa ser tratada como variável de contexto obrigatória para similaridade e modelagem.

## Documentação produzida

- [Visão geral do repositório](docs/analise_markdown/01_visao_geral_repositorio.md)
- [CRISP-DM detalhado](docs/analise_markdown/02_crisp_dm_detalhado.md)
- [Análise exploratória e insights](docs/analise_markdown/03_analise_exploratoria_insights.md)
- [Confronto com a literatura web](docs/analise_markdown/04_confronto_literatura_web.md)
- [Resumos por arquivo](docs/analise_markdown/resumos)

## Próximos passos recomendados

1. padronizar a taxonomia de `fault`;
2. mapear cada família de falha ao documento técnico correspondente;
3. criar baseline de similaridade condicionado por `rpm`;
4. estruturar recuperação documental com rastreabilidade de fonte;
5. implementar política de recusa para falhas sem cobertura documental.

## Observações de versionamento

- os arquivos da prova prática foram mantidos fora do versionamento por `.gitignore`;
- o script auxiliar que gera o notebook/relatório também foi deixado fora do versionamento para manter o primeiro commit mais limpo.
