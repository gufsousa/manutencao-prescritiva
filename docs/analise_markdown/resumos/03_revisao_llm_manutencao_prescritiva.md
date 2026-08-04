# Resumo do Arquivo `docs/Revisão LLM Manutenção Prescritiva.pdf`

## Do que se trata

É uma revisão sistematizada de literatura sobre o uso de modelos de linguagem de grande escala em cenários de classificação multivariada e manutenção prescritiva.

## Conteúdo central

- diferencia manutenção reativa, preventiva, preditiva e prescritiva;
- relaciona manutenção prescritiva com séries temporais multivariadas;
- discute limites do uso de LLMs em inferência numérica bruta;
- reforça que LLMs são mais adequados para raciocínio textual, síntese e interface com conhecimento;
- ajuda a justificar arquiteturas híbridas, com separação entre análise numérica e geração de linguagem.

## Papel no projeto

Oferece a fundamentação teórica para defender por que o sistema deve usar:

- métodos determinísticos/estatísticos para diagnóstico;
- LLM para explicação, orquestração e suporte prescritivo.

## Observações

- é útil para embasar decisões arquiteturais na documentação final;
- serve como argumento contra uma solução baseada apenas em prompting sobre dados crus.
