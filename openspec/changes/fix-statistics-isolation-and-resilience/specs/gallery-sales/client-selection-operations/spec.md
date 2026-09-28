# Spec Delta

## MODIFIED Requirements

### Requirement: Exportação de identificadores da seleção

O sistema SHALL permitir ao fotógrafo exportar a lista de identificadores das fotos selecionadas em formato TXT e CSV, sem expor URLs de originais nem dados de outros clientes. Quando a seleção ou compra possuir somente referência histórica, o sistema SHALL usar o identificador e nome congelados disponíveis no registro comercial.

#### Scenario: Separação no fluxo externo do fotógrafo

- **WHEN** o fotógrafo solicita exportação de uma seleção
- **THEN** o sistema gera um arquivo com os identificadores das fotos daquela seleção e registra a operação de exportação

#### Scenario: Referência operacional removida

- **WHEN** o fotógrafo exporta uma seleção ou compra cuja foto operacional não existe mais
- **THEN** o arquivo preserva o identificador histórico válido e o nome congelado, sem URL quebrada ou valor nulo
