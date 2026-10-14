## ADDED Requirements

### Requirement: Atalho para galeria privada recente

O sistema SHALL apresentar o nome de cada galeria privada recente da Visão geral autenticada como um link que abre a ficha administrativa da mesma galeria. O destino SHALL corresponder ao identificador opaco fornecido pelo backend e SHALL preservar a distinção visual entre nome, prazo e estado de acesso.

#### Scenario: Fotógrafo abre uma galeria recente

- **WHEN** o fotógrafo autenticado ativa o nome de uma galeria no card “Acesso recente · Galerias privadas”
- **THEN** o sistema abre diretamente a ficha administrativa correspondente, sem exigir passagem pela listagem completa

#### Scenario: Galeria recente com acesso bloqueado

- **WHEN** uma galeria recente está identificada como bloqueada na Visão geral
- **THEN** seu nome continua disponível ao fotógrafo como link para a ficha administrativa e o indicador de bloqueio permanece visível separadamente

