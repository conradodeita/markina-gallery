# Spec Delta

## Purpose

Definir quais pastas de uma galeria autenticada cada cliente vinculada pode ver e usar, sem criar galerias derivadas nem expor o acervo de outras clientes.

## ADDED Requirements

### Requirement: Público explícito por pasta

Cada pasta de conteúdo SHALL ter público `todos os clientes vinculados` ou `clientes escolhidos`. Uma pasta nova SHALL permanecer invisível às clientes até ser liberada com público definido explicitamente. O fotógrafo SHALL poder atribuir uma pasta restrita a uma ou mais clientes vinculadas à mesma galeria.

#### Scenario: Pasta comum liberada

- **WHEN** o fotógrafo libera uma pasta para todos os clientes vinculados
- **THEN** cada cliente ativa e autorizada à galeria vê a pasta e suas fotos, sem acesso anônimo

#### Scenario: Pasta para duas clientes

- **WHEN** o fotógrafo libera uma pasta restrita para duas clientes vinculadas
- **THEN** apenas essas clientes veem a pasta além das pastas comuns; outras clientes da galeria não recebem metadados nem fotos da pasta

#### Scenario: Pasta ainda em preparação

- **WHEN** a pasta não foi liberada ou seu público não foi definido
- **THEN** somente o fotógrafo autorizado pode consultá-la

### Requirement: Autorização individual em todos os caminhos

O backend SHALL calcular o acervo de uma cliente pela união das pastas comuns e das pastas restritas atribuídas a ela. A autorização SHALL ser aplicada também a cada prévia, seleção, favorito, comentário, busca facial, carrinho e exportação; conhecer um identificador ou URL SHALL NOT conceder acesso.

#### Scenario: Coleção da cliente com pastas comuns e atribuídas

- **WHEN** uma cliente autenticada abre “Coleção” em uma galeria à qual está vinculada
- **THEN** a navegação de pastas existente mostra as pastas comuns liberadas e as pastas restritas liberadas atribuídas a ela, sem mostrar pastas atribuídas somente a outras clientes

#### Scenario: URL de foto exclusiva obtida por outra cliente

- **WHEN** uma cliente vinculada à galeria solicita diretamente a prévia de uma pasta restrita não atribuída a ela
- **THEN** o backend nega o acesso sem revelar a foto ou seu conteúdo

#### Scenario: Atribuição removida

- **WHEN** o fotógrafo remove a atribuição de uma pasta restrita a uma cliente
- **THEN** consultas e interações futuras deixam de expor essa pasta, preservando somente o histórico comercial que for legalmente devido
- **AND** seleções ainda pendentes da cliente nessa pasta são removidas para não bloquear compras posteriores de fotos que continuam autorizadas

#### Scenario: Acesso individual bloqueado

- **WHEN** o fotógrafo bloqueia o estado de uma cliente na galeria
- **THEN** a cliente não acessa nem pastas comuns nem restritas enquanto o bloqueio vigorar; pedidos e entregas históricos permanecem sujeitos às regras próprias de retenção e acesso

#### Scenario: Bloqueio de uma entre duas clientes

- **WHEN** o fotógrafo bloqueia ou libera o acesso individual no card “Acervo da cliente”
- **THEN** somente o estado daquela combinação de galeria e cliente muda; a outra cliente conserva suas pastas, seu prazo e seu histórico

### Requirement: Isolamento dos estados da cliente

Seleções, visualizações, favoritos, comentários, carrinho, pedidos, pagamento e entrega SHALL ser atribuídos à combinação de galeria e cliente autenticada. A visualização SHALL ser registrada quando a cliente abre a foto ampliada, não quando a miniatura é carregada.

#### Scenario: Duas clientes na mesma galeria

- **WHEN** duas clientes acessam uma pasta comum e uma pasta atribuída a ambas
- **THEN** cada uma vê apenas seus próprios estados e histórico comercial, sem receber os dados da outra

### Requirement: Aviso somente às destinatárias da pasta

O sistema SHALL preparar o aviso configurado de novas fotos somente para clientes com acesso efetivo à pasta recém-liberada ou atribuída. O aviso SHALL ser idempotente por cliente e rodada; falha de WhatsApp ou push SHALL NOT desfazer a liberação nem divulgar a pasta a outras clientes.

#### Scenario: Pasta restrita liberada

- **WHEN** o fotógrafo libera uma pasta restrita para duas de três clientes vinculadas
- **THEN** somente as duas destinatárias elegíveis podem receber aviso, conforme as configurações globais atuais

#### Scenario: Canal ativado após a liberação

- **WHEN** um canal de notificação é ativado depois que a pasta foi liberada
- **THEN** o sistema não reproduz automaticamente avisos históricos
