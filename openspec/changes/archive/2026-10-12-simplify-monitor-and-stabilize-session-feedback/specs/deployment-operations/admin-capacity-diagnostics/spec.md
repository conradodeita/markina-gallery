# Spec Delta

## ADDED Requirements

### Requirement: Dica de interpretação do diagnóstico de capacidade
O card de capacidade SHALL oferecer dica acessível por toque/teclado que explique leitura pontual das conexões e filas, atualização manual e possibilidade de copiar o relatório para suporte. A dica SHALL informar que esse snapshot não determina capacidade máxima e não altera autorização, coleta ou serialização existentes.

#### Scenario: Proprietário consulta a dica
- **WHEN** o proprietário abre a ajuda do card de capacidade
- **THEN** recebe a explicação em linguagem simples, mantendo as ações Consultar diagnóstico e Copiar relatório e seus contratos existentes
