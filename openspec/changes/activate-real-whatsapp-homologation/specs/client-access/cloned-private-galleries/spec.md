## Purpose

Condicionar o primeiro cadastro de cliente ao link não listado de uma galeria-fonte sem transformar esse link em autorização para o acervo coletivo.

## MODIFIED Requirements

### Requirement: Entrada por link não listado e vínculo individual

O sistema SHALL tratar um link de galeria-fonte ativa como não listado e insuficiente para conceder acesso a fotografias. O visitante SHALL informar nome e telefone, concluir OTP e ter uma relação individual autorizada antes de visualizar conteúdo privado. Um telefone desconhecido SHALL ser cadastrado somente depois do OTP iniciado por esse link; a entrada direta sem contexto SHALL NOT criar cliente ou sessão.

#### Scenario: Nova cliente entra pelo link compartilhado

- **WHEN** uma pessoa ainda não cadastrada abre um link não listado de galeria-fonte ativa e conclui o OTP com sucesso
- **THEN** o sistema cria sua conta, registra o vínculo individual com estado pendente e encaminha somente para uma galeria privada já autorizada ou para o estado de aguardando aprovação

#### Scenario: Cliente entra pelo link compartilhado

- **WHEN** uma pessoa abre um link não listado e conclui o OTP com sucesso
- **THEN** o sistema registra o vínculo da pessoa com a galeria-fonte e encaminha apenas para uma galeria privada autorizada ou para um estado de aguardando aprovação

#### Scenario: Cliente existente recebe outro link

- **WHEN** uma cliente cadastrada conclui o OTP a partir de outro link não listado válido
- **THEN** o sistema reutiliza sua identidade, cria ou reutiliza o vínculo com essa galeria-fonte e encaminha para a galeria privada correspondente ou para o estado de aguardando aprovação

#### Scenario: Entrada direta de pessoa desconhecida

- **WHEN** uma pessoa ainda não cadastrada conclui o OTP sem ter iniciado por um link válido de galeria
- **THEN** o sistema não cria conta, vínculo ou sessão e orienta a pessoa a usar um link compartilhado

#### Scenario: Evento coletivo protegido

- **WHEN** o acervo-fonte representa evento coletivo protegido
- **THEN** o sistema não apresenta grade coletiva após o OTP e exige criação ou aprovação de resultado privado antes de exibir fotografias
