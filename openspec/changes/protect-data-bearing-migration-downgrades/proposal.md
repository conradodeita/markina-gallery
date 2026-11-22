# Proposal

## Why

Downgrades que verificam se há estado protegido e depois removem tabelas, colunas ou largura de campos deixam uma janela para uma gravação concorrente. O guard pode observar a ausência de dados e permitir a remoção de uma linha ou valor confirmado logo depois da consulta.

## What Changes

- Tornar atômicos os guards de downgrade das migrations locais que recusam a remoção de histórico, credenciais, prazos, checkpoints, recibos ou estados recuperáveis.
- Tentar locks PostgreSQL ACCESS EXCLUSIVE NOWAIT sobre todas as tabelas consultadas ou alteradas antes do primeiro guard, na mesma transação Alembic.
- Interromper a migration antes do guard e do DDL quando qualquer transação ainda usar uma tabela bloqueada.
- Manter o rollback de release API/web sem downgrade automático; qualquer downgrade manual permanece sujeito a uma janela autorizada com API e workers escritores parados e conferidos.

## Capabilities

### New Capabilities
- Nenhuma.

### Modified Capabilities
- deployment-operations: guards de downgrade de schema que protegem dados tornam-se atômicos e falham fechados quando há transações concorrentes.

## Impact

Afeta somente o código de downgrade em migrations Alembic que já possuem guards de preservação e a validação de engenharia correspondente. Não altera o schema produzido por upgrade, não executa migration, não modifica dados e não autoriza uma operação de produção.
