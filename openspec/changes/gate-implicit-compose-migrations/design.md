# Design

## Decisão

`migrate` terá perfil `maintenance` e não será dependência de API, seed ou workers. Serviços que precisam de PostgreSQL/Redis dependerão dos healthchecks correspondentes. A execução padrão será `python -m app.schema_revision_check`, usando `ScriptDirectory` e `MigrationContext` do Alembic para comparar as revisões; não usará `stamp`, `upgrade` ou DDL. Erros serão sanitizados para não imprimir URL ou credenciais.

O script de homologação já reconstrói a imagem do SHA alvo, identifica uma única head e para writers antes de migrar. Ele passará essa revisão ao comando explícito `alembic upgrade "$target_heads"`. Seu restante permanece condicionado às proteções existentes.

## Limites e recuperação

Um Compose local novo não cria schema sozinho. O procedimento local documentará a aplicação explícita de uma revisão após confirmação do alvo. A mudança não torna `0093` segura para produção: a cadeia linear `0091` → `0093` → `0098` ainda exige expand, troca compatível dos consumidores, drenagem, contract, backup/restore e autorização específicos. Nenhum script de produção é executado ou reescrito aqui. Reversão do código desta change não deve ser feita sobre schema incompatível; confirmar revision e compatibilidade antes.

## Validação

Testar inspeção com schema ausente/atrasado/head em banco descartável, assegurar ausência de escrita, validar grafo Compose e testes do script de homologação. Fazer revisão do diff e refatoração proporcional apenas dos trechos afetados.
