# Proposal

## Why

O inventário somente leitura confirmou que homologação está no commit `0779b3e`, descendente da linha `main`, enquanto `develop` está em `71be3b2` mais a change de fotos privadas. A diferença entre as linhas é de 43 commits. Publicar o `develop` atual substituiria uma versão mais nova do app e encontraria duas migrations diferentes com a revisão `20261016_0082`; o banco já registra a migration facial nessa revisão.

## What Changes

- Integrar à linha `develop` a base já presente em homologação, preservando a change de fotos privadas.
- Encadear a migration de escopo das pastas privadas depois da revisão facial `20261016_0082`, com um identificador novo e único.
- Manter a aprovação de revisores do ambiente `homolog` e permitir a publicação controlada por `develop` sem abrir acesso para outras branches.
- Registrar o inventário, a reconciliação e as validações antes de repetir o deploy.

## Capabilities

### Modified Capabilities

- `deployment-operations`: garantir que homologação receba uma revisão descendente do código já instalado e que o grafo Alembic corresponda ao banco observado.

## Impact

Integração de branches, migration PostgreSQL preservadora, testes de regressão do grafo Alembic e configuração de elegibilidade do ambiente `homolog`. Nenhuma ação em produção, alteração de dados, secrets, canais externos ou infraestrutura compartilhada.
