# gallery-visualization-and-watermark-controls Specification

## ADDED Requirements

### Requirement: Apresentação privada coerente com a origem

O sistema SHALL manter a organização de pastas da galeria privada coerente com a configuração da Galeria pública de origem. A administração SHALL exibir essa herança e a cliente SHALL receber a mesma organização na superfície privada autorizada.

#### Scenario: Organização lado a lado herdada

- **WHEN** a origem está configurada para pastas individuais
- **THEN** as coleções privadas liberadas são apresentadas lado a lado, com nome e contagem

#### Scenario: Sequência herdada

- **WHEN** a origem está configurada para sequência cronológica
- **THEN** as coleções privadas liberadas são exibidas em ordem com seu título antes das fotos
