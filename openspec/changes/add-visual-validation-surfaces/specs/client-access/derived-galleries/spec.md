## ADDED Requirements

### Requirement: Revisão visual de galeria derivada

O sistema SHALL apresentar à cliente autorizada uma grade visual de suas fotos derivadas, com estados explícitos de seleção, favorito, comentário, prazo e indisponibilidade, todos baseados no backend.

#### Scenario: Cliente revisa fotos autorizadas

- **WHEN** a cliente abre uma galeria derivada ativa
- **THEN** a interface mostra somente as prévias autorizadas e diferencia visualmente as fotos selecionadas e favoritadas

#### Scenario: Prazo ou permissão bloqueia interação

- **WHEN** o backend informa prazo expirado ou recurso desabilitado
- **THEN** a interface explica a restrição e não oferece ação local que possa contorná-la

### Requirement: Orientação de validação para a cliente

O sistema SHALL apresentar estados de carregamento, vazio, erro e sucesso de forma compreensível na biblioteca e na galeria privada, permitindo que a cliente descreva a etapa observada durante a validação.

#### Scenario: Falha de consulta

- **WHEN** a consulta autorizada da biblioteca ou galeria falha
- **THEN** a interface mostra uma mensagem de erro clara sem revelar detalhes internos ou dados de terceiros
