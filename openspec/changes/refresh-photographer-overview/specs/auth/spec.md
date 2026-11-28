## ADDED Requirements

### Requirement: Apresentação responsiva da entrada e confirmação

A entrada SHALL organizar marca, contexto e campos autorizados para o cliente e o fotógrafo. A etapa de confirmação do cliente SHALL aceitar entrada ou colagem do código e preservar a resposta neutra do fluxo.

#### Scenario: Cliente abre um acesso por convite

- **WHEN** a cliente envia seus dados no contexto autorizado de um convite
- **THEN** a tela mostra o código de acesso e as ações de reenvio e retorno condicionadas ao fluxo existente
- **AND** mensagens, fatores e destinos usam os resultados já definidos pelo contrato de autenticação

#### Scenario: Cliente abre a entrada sem contexto de acesso

- **WHEN** a cliente abre a entrada sem convite ou retorno autorizado
- **THEN** a tela orienta a abrir o link enviado pelo fotógrafo, sem expor consulta de cadastro
