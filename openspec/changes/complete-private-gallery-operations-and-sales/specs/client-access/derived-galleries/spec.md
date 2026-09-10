## MODIFIED Requirements

### Requirement: Persistência do histórico privado

O sistema SHALL manter uma biblioteca visual para a cliente autorizada, onde ela retoma apenas galerias derivadas, pastas disponíveis, seleções, pedidos e histórico sem acesso indevido a outros acervos. A interface SHALL identificar fotos já compradas e preservar acesso a histórico permitido após a expiração da seleção. Quando a galeria expirar, o sistema SHALL bloquear novas alterações e finalização, explicar o congelamento e permitir solicitar reabertura controlada pelo fotógrafo.

#### Scenario: Biblioteca vazia

- **WHEN** a cliente autenticada não possui galeria derivada ativa nem entrega histórica
- **THEN** a interface mostra estado vazio claro sem sugerir ou revelar galerias de terceiros

#### Scenario: Nova pasta liberada

- **WHEN** o fotógrafo conclui o processamento de uma nova pasta exclusiva da privada
- **THEN** a biblioteca ou galeria apresenta a nova rodada separadamente das fotos já revisadas

#### Scenario: Histórico após expiração

- **WHEN** o prazo de seleção de uma galeria privada expira
- **THEN** a cliente continua acessando pedidos, entregas e identificação de fotos já compradas, sem selecionar ou finalizar, e pode solicitar reabertura

#### Scenario: Solicitação pendente

- **WHEN** a cliente retorna enquanto a reabertura aguarda decisão
- **THEN** a interface apresenta `Reabertura solicitada` sem habilitar controles comerciais
