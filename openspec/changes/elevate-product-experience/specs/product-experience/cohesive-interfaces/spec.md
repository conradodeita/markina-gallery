## Purpose

Definir uma experiência visual coesa, acessível e responsiva para as superfícies de cliente e fotógrafo.

## ADDED Requirements

### Requirement: Sistema visual consistente

O sistema SHALL usar tokens e componentes reutilizáveis para navegação, ações, formulários, estados e feedback, com foco visível e contraste acessível.

#### Scenario: Estado operacional

- **WHEN** uma tela carrega, falha ou não possui dados
- **THEN** ela apresenta estado claro, ação de recuperação quando aplicável e linguagem consistente

### Requirement: Jornada focada por papel

O sistema SHALL apresentar ao fotógrafo pendências e ações prioritárias, e à cliente uma jornada clara de galeria até entrega, sem expor controles do outro papel.

#### Scenario: Fotógrafo abre o painel

- **WHEN** o fotógrafo autenticado abre a área administrativa
- **THEN** ele encontra contexto, pendências e atalhos operacionais sem precisar navegar por telas técnicas
