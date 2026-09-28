# Spec Delta

## MODIFIED Requirements

### Requirement: Público explícito por pasta

Cada pasta de conteúdo SHALL ter público `todos os clientes vinculados` ou `clientes escolhidos`. Uma pasta nova SHALL permanecer invisível às clientes até ser liberada com público definido explicitamente. Pastas restritas criadas no Acervo de uma cliente SHALL ser atribuídas exclusivamente àquela cliente. A API administrativa SHALL recusar a atribuição de uma segunda cliente a uma pasta restrita, inclusive quando chamada diretamente. Pastas que já possuírem múltiplas atribuições SHALL preservar acessos, fotos e históricos existentes, sem conversão ou revogação automática; a API SHALL permitir remover atribuições dessas pastas legadas, mas SHALL recusar novas atribuições.

#### Scenario: Pasta comum liberada

- **WHEN** o fotógrafo libera uma pasta para todos os clientes vinculados
- **THEN** cada cliente ativa e autorizada à galeria vê a pasta e suas fotos, sem acesso anônimo

#### Scenario: Pasta exclusiva liberada

- **WHEN** o fotógrafo cria uma pasta restrita no Acervo de uma cliente e libera suas fotos
- **THEN** somente essa cliente vê a pasta além das pastas comuns; outras clientes da galeria não recebem metadados nem fotos da pasta

#### Scenario: Segunda atribuição recusada

- **WHEN** o fotógrafo ou um cliente de API tenta atribuir uma pasta restrita existente a outra cliente
- **THEN** o backend recusa a operação sem alterar as atribuições ou o histórico

#### Scenario: Pasta para duas clientes

- **WHEN** uma pasta restrita já estava atribuída a duas clientes antes desta mudança
- **THEN** ambas conservam o acesso autorizado, mas nenhuma terceira cliente pode ser atribuída; uma atribuição existente pode ser removida explicitamente

#### Scenario: Pasta ainda em preparação

- **WHEN** a pasta não foi liberada ou seu público não foi definido
- **THEN** somente o fotógrafo autorizado pode consultá-la
