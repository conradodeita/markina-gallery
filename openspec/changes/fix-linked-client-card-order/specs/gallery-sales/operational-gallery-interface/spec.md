## ADDED Requirements

### Requirement: Cards de clientes vinculadas por atividade

O sistema SHALL apresentar os cards de clientes vinculadas a uma Galeria pública em uma única coluna e ordená-los pela atividade de acesso mais recente primeiro. A ordem SHALL usar a última visualização de prévia protegida registrada para a Galeria pública ou galeria privada correspondente e, quando inexistente, a data de criação do vínculo. O menu recolhível e os demais controles existentes SHALL permanecer disponíveis.

#### Scenario: Cliente retorna à galeria

- **WHEN** uma cliente visualiza uma prévia protegida depois das demais clientes
- **THEN** seu card aparece no topo após a próxima consulta à lista

#### Scenario: Cliente ainda não abriu prévias

- **WHEN** não há visualização protegida registrada para uma cliente vinculada
- **THEN** o sistema ordena seu card pela data de criação do vínculo, mantendo clientes sem data no final

#### Scenario: Lista em telas largas

- **WHEN** o fotógrafo consulta clientes vinculadas em uma tela larga
- **THEN** cada card ocupa uma linha e mantém o menu recolhível e os demais controles
