# Spec Delta

## MODIFIED Requirements

### Requirement: Interface original por papel

O sistema SHALL fornecer uma interface visual coesa para fotógrafo e cliente, com navegação, hierarquia, componentes e estados próprios da Pick-your-Pic. A interface SHALL ser responsiva, acessível e não copiar componentes ou código de serviços concorrentes.

#### Scenario: Fotógrafo inicia a operação

- **WHEN** o fotógrafo autenticado abre a área administrativa
- **THEN** vê acesso claro a pendências, galerias únicas, clientes, pastas e operações disponíveis para seus dados autorizados

#### Scenario: Cliente retoma sua jornada

- **WHEN** uma cliente autenticada abre a biblioteca ou uma galeria
- **THEN** vê uma entrada por galeria e, em “Coleção”, as pastas comuns e atribuídas na navegação atual, além de sua seleção e histórico, sem controles administrativos nem dados de terceiros
