# Design

## Context

Ver `proposal.md` para o motivo. A especificação `deployment-operations` já define migrations explícitas no deploy. `scripts/deploy-homolog.sh` reconstrói a imagem `migrate`, executa-a por `compose run --rm --no-deps` e inicia os serviços por `compose up --no-deps`; o acionamento manual de `compose start` no ensaio recente seguiu as dependências e tentou iniciar um contêiner one-shot antigo. O DB permaneceu em `20260929_0069`, e os serviços foram recuperados iniciando apenas os contêineres existentes.

## Goals / Non-Goals

**Goals:**

- Tornar o procedimento de retomada explícito, repetível e testado para os serviços existentes da aplicação.
- Garantir que retomar a aplicação não execute Alembic nem inicie o serviço `migrate`.
- Verificar saúde dos serviços selecionados e endpoints locais/públicos e falhar com diagnóstico claro.

**Non-Goals:**

- Alterar ou executar migration, reconstruir imagens, trocar a release ou modificar o schema neste procedimento de retomada.
- Fazer deploy remoto, editar `.env`/secrets, limpar dados ou reiniciar PostgreSQL, Redis, Evolution ou recursos de terceiros.

## Decisions

- O caminho de retomada usará o projeto e arquivos Compose explícitos da Markina e iniciará os serviços-alvo sem acompanhar dependências (`--no-deps`). Ao retomar contêineres existentes, não reconstruirá nem recriará imagens/contêineres (`--no-recreate`), preservando exatamente a versão já configurada.
- A lista de serviços será construída a partir do inventário/estado do próprio projeto Markina. Serviços opcionais só entram se já estiverem ativos; Evolution e vizinhos nunca são incluídos.
- Antes do start, o procedimento exige banco e Redis Markina saudáveis e a revisão Alembic observável. Ele não executa migration para tentar corrigir ausência ou divergência de revisão; nesse caso aborta e registra diagnóstico.
- Após iniciar, aguarda healthchecks de todos os serviços selecionados e status HTTP 200 nos endpoints de saúde local e público configurados. Timeout falha fechado sem recorrer a `compose start`, Alembic, `down`, prune ou rollback de dados.
- O deploy autorizado continua sendo caminho separado: constrói a migration do SHA escolhido, aplica Alembic explicitamente e então inicia código compatível.

Alternativa descartada: remover indiscriminadamente as dependências `migrate` do Compose principal. Isso poderia mudar o comportamento de primeira inicialização local e permitir início da API antes do schema esperado.

## Risks / Trade-offs

- [Containers ausentes ou configuração Compose incompatível] → a retomada não os recria; aborta e encaminha para deploy/repair explicitamente autorizado.
- [Revisão Alembic ausente no checkout local] → trata como incompatibilidade; não carimba nem altera a revisão do banco.
- [A lista de serviços opcionais não reflete os perfis ativos] → deriva a seleção do estado atual do projeto e testa cenários de worker habilitado/desabilitado.

## Migration Plan

1. Implementar e testar o procedimento localmente com Compose/containers simulados, verificando argumentos, ordem, bloqueios e ausência de chamada a migration.
2. Atualizar o runbook de homologação com o comando de retomada e separar retomada de deploy/migration.
3. Só executar um ensaio remoto após inventário somente-leitura, portas/subdomínio e plano de impacto zero apresentados e autorização humana específica; confirmar healthchecks, endpoints, revisão invariável, Evolution e vizinhos.

Rollback da mudança documental/script: restaurar o procedimento anterior no Git; não há migração de dados.
