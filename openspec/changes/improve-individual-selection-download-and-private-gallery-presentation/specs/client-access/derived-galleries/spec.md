# client-access/derived-galleries Specification

## ADDED Requirements

### Requirement: Pastas privadas liberadas com apresentação herdada

O sistema SHALL permitir ao fotógrafo liberar uma pasta própria da galeria privada após o processamento. A cliente SHALL visualizar as fotos liberadas dessa pasta na galeria privada, usando o `folder_display_mode` herdado da Galeria pública de origem.

#### Scenario: Pasta privada publicada

- **WHEN** o fotógrafo libera uma pasta própria com prévias prontas
- **THEN** a pasta aparece para a cliente na seção “Coleções” ou em sequência cronológica conforme a configuração da origem

#### Scenario: Pasta ainda em preparação

- **WHEN** a pasta privada ainda não foi liberada ou suas prévias não estão prontas
- **THEN** ela não aparece como conteúdo disponível para a cliente e a administração mostra seu estado operacional

#### Scenario: Herança visível na administração

- **WHEN** o fotógrafo abre o detalhe da galeria privada
- **THEN** a tela informa qual organização de pastas está sendo herdada da Galeria pública, sem criar uma configuração divergente
