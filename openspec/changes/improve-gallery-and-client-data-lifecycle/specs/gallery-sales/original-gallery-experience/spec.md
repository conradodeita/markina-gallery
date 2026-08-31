## MODIFIED Requirements

### Requirement: Interface original por papel

O sistema SHALL fornecer uma interface visual coesa para fotógrafo e cliente, com navegação, hierarquia, componentes e estados próprios da Markina Gallery. A interface SHALL ser responsiva, acessível e não copiar componentes ou código de serviços concorrentes. A experiência da cliente SHALL apresentar separadamente Galerias públicas autenticadas e autorizadas, galerias privadas derivadas e histórico comercial, preservando a relação entre cada privada e sua origem sem revelar conteúdo de terceiros.

#### Scenario: Fotógrafo inicia a operação

- **WHEN** o fotógrafo autenticado abre a área administrativa
- **THEN** ele vê acesso claro a pendências, Galerias públicas, clientes, pastas e operações disponíveis para seus dados autorizados

#### Scenario: Cliente retoma sua jornada

- **WHEN** uma cliente autenticada abre sua biblioteca
- **THEN** ela vê suas Galerias públicas abertas, galerias privadas ativas e histórico em grupos relacionados, sem controles administrativos ou dados de terceiros

#### Scenario: Cliente retorna à Galeria pública

- **WHEN** a cliente está em uma privada ativa e deseja escolher outra foto da mesma origem
- **THEN** a interface oferece retorno à Galeria pública correspondente e o backend encaminha a seleção à mesma privada

### Requirement: Estados visuais controlados pelo backend

O sistema SHALL apresentar carregamento, vazio, erro, sucesso, bloqueio, expiração, preparação, modo de acesso e estado comercial a partir de respostas autorizadas do backend. O frontend SHALL NOT preencher lacunas com autorizações, fotos, pedidos, vínculos ou estados simulados persistentes e SHALL NOT inferir `standard`, `invite_only` ou `collective_protected` por rota ou conteúdo recebido.

#### Scenario: Falha de consulta operacional

- **WHEN** uma consulta autenticada de galeria ou pasta falha
- **THEN** a interface informa a falha e oferece uma ação segura de nova tentativa sem exibir dados obsoletos como se fossem atuais

#### Scenario: Backend nega navegação fotográfica

- **WHEN** o backend informa que o modo ou convite não autoriza fotos
- **THEN** a interface apresenta o estado permitido sem tentar carregar prévias, criar vínculo ou revelar a existência de galerias privadas
