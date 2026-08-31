## ADDED Requirements

### Requirement: Identidade única por telefone verificado

O sistema SHALL resolver uma única identidade de cliente pelo telefone normalizado em E.164 e comprovado por OTP. Quando o telefone já pertencer a um cadastro ativo, o sistema SHALL reutilizar o mesmo `Client`, SHALL NOT criar duplicata nem sobrescrever seu nome com o valor informado no login. Link, nome isolado ou telefone ainda não comprovado SHALL NOT conceder acesso privado.

#### Scenario: Telefone já cadastrado

- **WHEN** uma pessoa comprova por OTP um telefone ativo já associado a uma cliente
- **THEN** o sistema cria sessão para o mesmo `Client`, preserva o nome cadastrado e não cria outra cliente

#### Scenario: Nome informado diverge

- **WHEN** uma pessoa comprova por OTP um telefone existente e informa nome diferente do cadastro
- **THEN** o sistema reutiliza a identidade determinada pelo telefone, não cria duplicata e não altera automaticamente o nome persistido

#### Scenario: Primeiro cadastro por link válido

- **WHEN** uma pessoa comprova telefone ainda desconhecido a partir de um link válido de Galeria pública e informa nome válido
- **THEN** o sistema cria um único `Client`, cria sua sessão e registra o vínculo com a origem sem criar galeria privada vazia

#### Scenario: Concorrência no primeiro cadastro

- **WHEN** duas requisições tentam cadastrar simultaneamente o mesmo telefone verificado
- **THEN** o sistema converge para um único `Client` e um único vínculo por Galeria pública

### Requirement: Vínculo de sessão existente por link

O sistema SHALL exigir autenticação de cliente ao abrir o link de uma Galeria pública. Quando já houver sessão `client` válida, o sistema SHALL aplicar no backend o modo de acesso e o escopo do token sem solicitar novo OTP, sem duplicar cadastro e sem modificar nome ou telefone. O vínculo automático SHALL ocorrer somente para link público válido em modo `standard`; `invite_only` SHALL exigir associação ou convite individual compatível, e `collective_protected` SHALL manter o registro pendente sem liberar fotos.

#### Scenario: Link aberto sem sessão

- **WHEN** uma pessoa sem sessão abre o link de uma Galeria pública válida
- **THEN** o sistema solicita login e preserva somente um destino interno seguro para retornar após a autenticação

#### Scenario: Link aberto com sessão de cliente

- **WHEN** uma cliente autenticada abre uma Galeria pública ainda não vinculada
- **THEN** o sistema valida token e modo, cria o vínculo aplicável para o mesmo `Client` somente quando autorizado e prossegue sem novo OTP nem novo cadastro

#### Scenario: Sessão existente sem convite em galeria restrita

- **WHEN** uma cliente autenticada abre link público de Galeria pública `invite_only` sem associação ou convite individual válido
- **THEN** o sistema não cria vínculo, não entrega prévias e responde sem revelar clientes ou galerias privadas existentes

#### Scenario: Vínculo já existente

- **WHEN** a cliente autenticada reabre uma Galeria pública à qual já está vinculada
- **THEN** o sistema reutiliza o vínculo existente sem duplicar registro ou alterar sua galeria privada

#### Scenario: Evento coletivo protegido

- **WHEN** a cliente autenticada abre o link de uma Galeria pública classificada como evento coletivo protegido
- **THEN** o sistema registra vínculo pendente e não libera grade ou resultado privado antes das aprovações exigidas

### Requirement: Minimização de dados em OTP sem convite

O sistema SHALL NOT criar cadastro de cliente, vínculo com galeria ou sessão quando uma pessoa concluir o OTP sem contexto válido de convite ou Galeria pública. O sistema MUST apagar nome e telefone em claro dos registros transitórios após a negação terminal, mantendo somente identificadores irreversíveis, estado, horários e metadados mínimos necessários a auditoria, antifraude e rate limit.

#### Scenario: OTP válido sem contexto de galeria

- **WHEN** uma pessoa valida corretamente o OTP iniciado fora de um link de galeria autorizado
- **THEN** o sistema nega o acesso, não cria cliente, vínculo ou sessão e remove nome e telefone em claro dos registros transitórios relacionados

#### Scenario: Desafio abandonado ou expirado

- **WHEN** um desafio OTP sem convite expira ou alcança estado terminal sem autenticação autorizada
- **THEN** o sistema elimina os dados pessoais em claro após a janela operacional documentada e preserva somente evidência não reversível necessária aos controles de segurança

#### Scenario: Entrada por convite válido

- **WHEN** uma pessoa conclui o OTP a partir de um contexto de Galeria pública válido
- **THEN** o sistema cria ou reutiliza pelo telefone um único cadastro de cliente e o vínculo autorizado, sem criar automaticamente uma galeria privada nem conceder acesso a galerias privadas de terceiros
