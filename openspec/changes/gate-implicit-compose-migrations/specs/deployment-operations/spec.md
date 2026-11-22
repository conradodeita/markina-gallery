## ADDED Requirements

### Requirement: Gate explícito de revisão Alembic no Compose

A inicialização ou retomada da API, dos workers, inclusive o de ajuste de prévias, e do bootstrap administrativo SHALL NOT iniciar `migrate` por dependência. O comando padrão de `migrate` SHALL conferir as revisões do banco e do código sem escrita e MUST falhar quando não forem iguais e únicas. Migration SHALL ser invocada separadamente, com revisão de destino explícita e após os gates operacionais aplicáveis.

#### Scenario: Inicialização ou retomada da aplicação

- **WHEN** o operador inicia ou retoma serviços de aplicação pelo Compose
- **THEN** `migrate` não é iniciado como dependência e a revisão do banco não é alterada por esse ato

#### Scenario: Conferência de schema

- **WHEN** o operador invoca `migrate` sem substituir o comando
- **THEN** o serviço compara a revisão corrente com a head única do código sem escrita e retorna falha se estiver vazio, atrasado, divergente ou ambíguo

#### Scenario: Migration de homologação autorizada

- **WHEN** o fluxo autorizado de homologação precisa aplicar uma revisão após selecionar o SHA alvo
- **THEN** o script invoca Alembic upgrade com a revisão identificada explicitamente e confirma a revisão aplicada

#### Scenario: Bootstrap local sem schema

- **WHEN** a aplicação local precisa de um schema inicial
- **THEN** o operador executa a migration separadamente, com revisão escolhida, antes de iniciar os serviços dependentes
