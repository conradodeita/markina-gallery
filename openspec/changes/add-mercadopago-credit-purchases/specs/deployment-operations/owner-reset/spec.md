# deployment-operations/owner-reset Specification

## ADDED Requirements

### Requirement: Preservação da carteira na limpeza de conteúdo de homologação

As rotinas SHALL classificar explicitamente as tabelas da carteira, pacote, ledger, operação/alocação de upload e compra de créditos. A limpeza de conteúdo SHALL preservá-las e incluí-las no inventário somente como contagens. Schema ou tabela não classificados MUST manter a recusa fail-closed.

#### Scenario: Limpeza de conteúdo preserva carteira e compra

- **WHEN** há registros de carteira, ledger, operação ou compra durante a limpeza de conteúdo
- **THEN** as linhas permanecem íntegras e aparecem somente como contagens no inventário

#### Scenario: Schema desconhecido

- **WHEN** uma tabela do modelo ou do banco não tem classificação de limpeza
- **THEN** inventário e limpeza recusam antes de qualquer mutação

### Requirement: Reset não apaga configuração do proprietário nem histórico de crédito

O reset integral SHALL preservar o catálogo global de pacotes e a carteira do tenant proprietário. MUST adquirir bloqueios nas tabelas financeiras e recusar antes de mutação no banco ou na mídia se existir qualquer ledger, operação/evento/alocação ou compra/evento, independentemente do estado.

#### Scenario: Histórico de créditos impede reset integral

- **WHEN** existe uma entrada, operação, evento, alocação ou compra de créditos
- **THEN** o reset é recusado e as evidências financeiras permanecem íntegras

#### Scenario: Configuração da carteira do proprietário é preservada

- **WHEN** não existe histórico de créditos e o reset integral é executado
- **THEN** o catálogo global e a carteira ilimitada do proprietário permanecem; carteiras de tenants removidos são excluídas com seus tenants

#### Scenario: Schema desconhecido

- **WHEN** o modelo ou banco contém uma tabela de compra de créditos sem classificação correspondente
- **THEN** inventário e limpeza recusam a operação antes de qualquer mutação
