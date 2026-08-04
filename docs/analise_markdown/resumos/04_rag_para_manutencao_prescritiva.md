# Resumo do Arquivo `docs/RAG para Manutenção Prescritiva.pdf`

## Do que se trata

É um guia de arquitetura e implementação de um sistema de manutenção prescritiva com IA, com forte ênfase em RAG, avaliação prática e governança da resposta.

## Conteúdo central

- descreve ingestão de dados de sensores em JSON;
- propõe busca semântica em documentação técnica;
- inclui uso de LLM para diagnóstico assistido e recomendação;
- destaca a importância de recusar prescrição quando não houver documentação;
- considera restrições computacionais e necessidade de persistência do histórico conversacional.

## Papel no projeto

É o documento mais diretamente conectado à camada de RAG do case. Ele ajuda a estruturar:

- indexação documental;
- recuperação de contexto;
- política de segurança contra alucinação;
- fluxo de resposta ao usuário.

## Observações

- combina visão de produto e visão técnica;
- é uma boa ponte entre o enunciado do case e a implementação esperada.
