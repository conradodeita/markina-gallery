# Spec Delta

## MODIFIED Requirements

### Requirement: Entrada por link não listado e vínculo individual

O sistema SHALL tratar um link de galeria como não listado e insuficiente para conceder acesso a fotografias. O visitante SHALL informar nome e telefone, concluir OTP e ter vínculo individual autorizado antes de visualizar pastas comuns ou atribuídas. Os modos operacionais SHALL ser `standard` e `invite_only`: o primeiro permite cadastro/vínculo por link válido após OTP; o segundo exige vínculo prévio ativo ou convite individual autorizado. Ambos SHALL aplicar o público de cada pasta e o bloqueio individual. Registros legados `collective_protected` SHALL continuar negando navegação até alteração explícita do modo pelo fotógrafo, sem conversão automática.

#### Scenario: Cliente entra pelo link compartilhado

- **WHEN** uma pessoa abre o link não listado e conclui o OTP com sucesso
- **THEN** o backend confirma seu vínculo antes de apresentar a visão autorizada da mesma galeria, ou um estado de aguardando aprovação

#### Scenario: Evento coletivo protegido

- **WHEN** uma galeria legada permanece com modo `collective_protected`
- **THEN** o backend mantém o estado pendente e a negação de grade, inclusive de pastas atribuídas, sem converter o modo nem liberar fotos automaticamente

#### Scenario: Nova cliente entra em modo Padrão

- **WHEN** uma nova cliente usa o link válido de uma galeria `standard` e conclui OTP
- **THEN** o backend pode criar seu cadastro/vínculo ativo e apresenta somente pastas comuns liberadas e exclusivas atribuídas a ela

#### Scenario: Link geral encaminhado em modo Somente convite individual

- **WHEN** uma pessoa sem vínculo ativo recebe o link geral de uma galeria `invite_only` e conclui OTP
- **THEN** o link geral não cria autorização nem revela fotos; acesso exige vínculo do fotógrafo ou convite individual válido para aquela identidade

#### Scenario: Cliente vinculada acessa em modo Somente convite individual

- **WHEN** uma cliente previamente vinculada ou convidada individualmente acessa uma galeria `invite_only` após OTP
- **THEN** ela vê pastas comuns liberadas e somente as exclusivas atribuídas a ela, mantendo seus estados e compras individuais
