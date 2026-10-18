## ADDED Requirements

### Requirement: Carregamento progressivo das prévias da grade da cliente
A interface autenticada da cliente SHALL carregar inicialmente as prévias da grade que estão próximas da área visível e SHALL solicitar as demais conforme a cliente percorre a galeria. A interface SHALL preservar a autorização e as URLs de mídia existentes.

#### Scenario: Cliente abre uma pasta com muitas fotos
- **WHEN** uma cliente autenticada abre uma pasta cuja grade contém muitas fotos
- **THEN** as prévias próximas da área visível começam a carregar sem aguardar a transferência das prévias mais distantes

#### Scenario: Cliente percorre a grade
- **WHEN** a cliente rola a grade em direção a fotos ainda distantes da área visível
- **THEN** as prévias que se aproximam da área visível são solicitadas progressivamente e permanecem sujeitas às mesmas autorizações existentes

#### Scenario: Fotógrafo usa a interface administrativa
- **WHEN** o fotógrafo autenticado abre uma grade administrativa
- **THEN** o comportamento de carregamento dessa grade permanece inalterado por este requisito
