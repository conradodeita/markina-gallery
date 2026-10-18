# Design

## Context

See `proposal.md`. O estado observado é `origin/develop` no commit `c9eaf6381cb95f53a1c88206f7b9d4fb638f7ef9`, checkout e serviços de homologação no SHA `0779b3e4400f8511980c2d18e79ef8eea586a341`, banco na revisão `20261016_0082` e health checks públicos HTTP 200. A tentativa de deploy criou backup lógico e o log terminou na primeira etapa após o backup, antes de selecionar o SHA alvo, preservar branding ou recriar containers. O próximo comando do script consulta a revisão usando `compose run ... migrate alembic current` antes de reconstruir a imagem `migrate`; o stderr desse probe é descartado, portanto o detalhe interno do erro não ficou registrado. A regressão de política adicionada falha contra esse caminho antigo antes da implementação.

## Goals / Non-Goals

**Goals:**

- Ler a revisão aplicada diretamente de `alembic_version` no PostgreSQL isolado do projeto.
- Comparar o valor do banco com a única revisão head lida pela imagem `migrate` construída a partir do SHA alvo.
- Falhar com diagnóstico sanitizado se a consulta não for possível, antes de interromper writers ou alterar serviços.
- Cobrir a política do probe por teste automatizado executado no CI.

**Non-Goals:**

- Alterar o contrato de deploy, o schema do produto ou o conteúdo do banco.
- Remover containers órfãos, recriar serviços de terceiros ou fazer prune.
- Aplicar manualmente migration fora do fluxo aprovado de homologação.

## Decisions

- A revisão corrente será consultada com `psql` no container `db`, limitado pelo wrapper Compose ao projeto `markina-gallery`; assim, ela não depende de uma imagem one-shot `migrate` antiga.
- O deploy construirá a imagem `migrate` para o SHA alvo, obterá `alembic heads` e exigirá exatamente uma head antes de parar writers. Depois do upgrade, comparará a versão no banco com essa head.
- Erros de consulta manterão o deploy fail-closed. O erro será reportado sem imprimir configuração, URL de banco, segredo ou dados de cliente.
- A execução no servidor continuará exclusiva do workflow `deploy-homolog`, após CI e gate do ambiente; o inventário e o backup existentes serão reaproveitados apenas como evidência, sem tentar restaurar ou remover dados.

## Risks / Trade-offs

- Uma base sem a tabela `alembic_version` fará o probe falhar antes de mudanças → manter o erro claro e exigir diagnóstico manual; não inferir uma revisão vazia.
- Mais de uma head no código alvo interromperá o deploy → detectar antes de parar writers e corrigir a árvore Alembic em CI.
- Uma revisão do banco ausente ou diferente da head fará o deploy falhar após a migration sem recriar serviços → preservar os containers antigos e registrar a revisão observada para análise.

## Migration Plan

1. Atualizar o script e os testes locais/policy.
2. Validar OpenSpec, política do deploy, sintaxe Bash e head Alembic.
3. Submeter PR para `develop`; aguardar CI verde e merge.
4. Executar o workflow de deploy autorizado em homologação, que fará backup antes de qualquer mudança, consultará o banco, aplicará migration 0083, recriará apenas os serviços da Markina e verificará saúde.
5. Confirmar SHA e revisão 0083 com inventário somente leitura.

Em falha antes de migration, manter checkout/containers antigos. Em falha após migration, não fazer downgrade automático; manter o banco e solicitar diagnóstico humano, conforme a política atual.

## Evidências

- O CI do PR #212 (run `39045028311`) passou em todos os checks obrigatórios; o PR foi mergeado em `develop` no commit `25cd338f7243a114e8151e6bda3d03204b12ae43`.
- O CI pós-merge e deploy de homologação (run `39046656588`) terminou com sucesso, registrou o backup lógico exclusivo, a migration `20261016_0082 → 20261017_0083`, o SHA implantado e containers Markina saudáveis.
- O inventário somente leitura pós-deploy (run `39049112709`) confirmou o SHA esperado, `alembic_revision=20261017_0083`, `/healthz: HTTP 200` e `/api/health: HTTP 200`. Nenhuma consulta de PII, alteração persistente ou ação de deploy ocorreu nesse inventário.
