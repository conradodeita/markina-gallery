## ADDED Requirements

### Requirement: Guards de downgrade protegidos contra gravações concorrentes
Downgrades Alembic que consultam dados para preservar estado antes de remover tabelas, colunas ou largura de campos MUST tentar adquirir, antes do primeiro guard, locks PostgreSQL ACCESS EXCLUSIVE NOWAIT sobre todas as tabelas consultadas ou alteradas. Os locks e o DDL SHALL permanecer na mesma transação. Se qualquer lock não puder ser adquirido, a transação SHALL abortar antes do guard e do DDL, preservando schema e dados.

#### Scenario: Escritor ou leitura mantém uma tabela alvo ocupada
- **WHEN** um downgrade protegido tenta adquirir os locks e uma transação concorrente mantém lock conflitante em uma tabela consultada ou alterada
- **THEN** NOWAIT faz o downgrade falhar antes do guard e de qualquer DDL, e a transação libera todos os locks já tentados

#### Scenario: O guard encontra dados protegidos
- **WHEN** todos os locks são obtidos e a consulta encontra histórico, credencial, recibo, checkpoint ou outro estado protegido
- **THEN** o downgrade recusa a operação e preserva as linhas e a revisão Alembic

#### Scenario: O guard não encontra dados protegidos
- **WHEN** todos os locks são obtidos e os guards confirmam que as estruturas podem ser removidas sem perder estado
- **THEN** o downgrade pode executar o DDL na mesma transação, mantendo os locks até commit

#### Scenario: Rollback de aplicação
- **WHEN** um release exige retornar a versão da aplicação
- **THEN** o fluxo de rollback não executa downgrade de schema automaticamente; downgrade manual requer janela autorizada com API e workers escritores parados e conferidos
