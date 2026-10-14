# Spec Delta

## ADDED Requirements

### Requirement: Carregamento progressivo da grade privada

A apresentação da galeria privada SHALL adiar a transferência das imagens de cards fora da área visível por meio do carregamento nativo do navegador, sem reduzir as verificações de autorização ou a proteção da prévia. A ampliação SHALL continuar usando a prévia protegida existente.

#### Scenario: Pasta privada extensa

- **WHEN** a cliente abre uma pasta com mais fotos do que cabem na área visível
- **THEN** os cards de foto usam carregamento tardio, e a cliente continua podendo ampliar uma foto e navegar pela galeria
