# Resumo do Arquivo `docs/Arquitetura Manutenção Prescritiva Local.pdf`

## Do que se trata

É uma proposta de arquitetura local e neuro-simbólica para manutenção prescritiva em borda, sob restrições de infraestrutura e sem dependência de APIs externas.

## Conteúdo central

- defende execução on-premise;
- separa o sistema em motor simbólico e motor neural;
- posiciona a análise estatística/similaridade na CPU;
- posiciona o LLM como camada de geração e explicação;
- destaca soberania dos dados, latência e confiabilidade operacional.

## Papel no projeto

É o melhor documento para orientar uma arquitetura robusta e justificável tecnicamente, especialmente se a entrega precisar simular ambiente industrial real.

## Observações

- converge com a revisão teórica e com o guia de RAG;
- reforça a tese de que o LLM não deve ser o decisor único do diagnóstico.
