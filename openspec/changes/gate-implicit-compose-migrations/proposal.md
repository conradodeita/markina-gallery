# Proposal

## Why

O Compose atual inicia `migrate` como dependência da API e dos workers e executa `alembic upgrade head`. Uma retomada comum pode, portanto, atravessar a migration contract TOTP `0093` sem o faseamento, inventário e autorização exigidos. O candidato SaaS não pode publicar esse comportamento.

## What Changes

- Retirar `migrate` do grafo de inicialização da aplicação e reservá-lo para operação explícita.
- Fazer a invocação padrão de `migrate` conferir, somente por leitura, se a revisão atual corresponde à única head do código; qualquer divergência falha fechada.
- Exigir revisão de destino explícita no script de homologação que antes dependia do comando padrão de `migrate`.
- Documentar bootstrap local, testes e o bloqueio operacional da sequência TOTP `0091`/`0093`.

## Impact

Afeta Compose principal e override do worker de prévias, o comando de inspeção Alembic, o script de homologação e testes operacionais. Um banco vazio ou atrasado não será migrado ao iniciar a aplicação. Nenhuma migração, deploy ou mudança de configuração real está incluída. A revisão da área afetada não encontrou limpeza segura além da remoção da dependência implícita.
