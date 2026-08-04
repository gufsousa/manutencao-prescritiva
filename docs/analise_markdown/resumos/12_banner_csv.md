# Resumo do Arquivo `data/raw/banner.csv`

## Do que se trata

É a principal base histórica de dados de sensores do projeto.

## Conteúdo central

- possui `166.796` registros e `26` colunas;
- contém medições de vibração, aceleração, temperatura, frequência característica, velocidade de pico, curtose, crest factor, `rpm` e `fault`;
- cobre leituras entre `2026-04-30` e `2026-06-16`;
- inclui classes de condição normal, motor desligado e diversas famílias de falha mecânica.

## Papel no projeto

É a fonte central para:

- análise exploratória;
- modelagem preditiva/prescritiva;
- busca por similaridade;
- construção de baseline de diagnóstico.

## Observações

- há forte necessidade de padronização da coluna `fault`;
- os valores de `rpm` se concentram em `0`, `500`, `1000`, `2000` e `3000`;
- o dataset contém muitas variações de nome para defeitos semelhantes, o que impacta diretamente a qualidade da modelagem.
