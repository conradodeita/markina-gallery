## ADDED Requirements

### Requirement: Painel visual de validação administrativa

O sistema SHALL fornecer ao fotógrafo autenticado um painel visual que reúna operações disponíveis, estado recente de galerias e importações, e atalhos para validar os fluxos sem expor dados de clientes não autorizados.

#### Scenario: Fotógrafo inicia a validação

- **WHEN** o fotógrafo abre a área administrativa autenticada
- **THEN** o sistema apresenta um resumo backend-driven e atalhos claros para clientes, acervos, importações, galerias, estatísticas e compras

#### Scenario: Estado sem dados

- **WHEN** não houver dados operacionais compatíveis com o resumo
- **THEN** o painel explica o próximo passo de validação sem inventar contagens ou registros

### Requirement: Identificação de ambiente de validação

O sistema SHALL tornar visível que a interface está em homologação e exibir um identificador não sensível da versão apresentada, para permitir relatos de bugs reproduzíveis.

#### Scenario: Relato de bug

- **WHEN** o fotógrafo relata um comportamento inesperado durante a validação
- **THEN** ele consegue informar a tela, o ambiente e a versão visíveis sem expor credenciais ou dados privados
