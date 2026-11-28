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

### Requirement: Apresentação responsiva das ações da conta do fotógrafo

A interface SHALL mostrar o estado atual da recuperação, os campos exigidos pelo fluxo e os próximos passos dependentes da resposta. O redesign SHALL preservar o tratamento do token de link, dos fatores e da revogação de sessão.

#### Scenario: Fotógrafo recupera o acesso

- **WHEN** o fotógrafo solicita recuperação no login
- **THEN** a tela informa a etapa atual e mantém os caminhos existentes por WhatsApp ou e-mail

#### Scenario: Fotógrafo abre um link de conta

- **WHEN** o fotógrafo abre um link de redefinição, confirmação de e-mail ou recuperação assistida
- **THEN** a tela informa se a ação está disponível, em andamento, concluída ou indisponível, com os controles correspondentes
- **AND** a recuperação assistida concluída continua pendente de execução pelo proprietário
