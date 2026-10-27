# Proposal

## Why

A PR #296 já integrou o limite de intensidade de prévias até 100% e a migration Alembic `20261026_0090`, mas o release API/web existente recusa migrations e o classificador as marca como `protected`. Sem uma rota específica e verificável, a interface e o backend novos não podem ser publicados com o schema compatível.

## What Changes

- Criar operações manuais distintas para instalação do wrapper read-only, inventário e release protegido, limitadas ao fluxo da migration `20261026_0090` e ao avanço validado de `20261025_0089`.
- Fixar como candidato de aplicação o SHA integrado `0dd015a62447e0c8d4c6af16b381140c8118f2ec`, que inclui a melhoria de prévias e as alterações revisadas das PRs #295 e #297. O CI do push à `main` para esse SHA ainda deve estar concluído com sucesso antes do release. O preflight SHALL confirmar o runtime `c1944189761799be96eeeb921cad9906484d8b09` e schema `20261025_0089` ou falhar fechado.
- Exigir SHA completo integrado na `main`, CI verde, fingerprint do estado observado e aprovação humana vinculada ao inventário exato antes de qualquer mutação.
- Verificar backup restaurável, identidade/saúde do projeto Markina, schema de origem, alvo e escopo exato; interromper somente os escritores Markina necessários, executar a migration aprovada e iniciar os runtimes compatíveis.
- Validar schema, saúde e smoke tests após a operação, preservar evidências e não executar downgrade/restauração automática após o início da migration.
- Manter o release API/web comum recusando migrations e não alterar serviços, dados ou infraestrutura de terceiros.
- Reconciliar históricos encerrados fora dos alvos Compose com identidade no fingerprint e verificações de preservação antes/depois das operações, mediante prova real do Compose 2.35.1 em runner descartável; manter recusa de duplicidade ativa e de históricos selecionáveis.

## Capabilities

### New Capabilities

### Modified Capabilities

- `deployment-operations`: permitir somente um release protegido e dedicado à migration `20261026_0090`, com preflight, backup, aprovação exata, escopo limitado e recuperação segura.

## Impact

Afeta o workflow CI do GitHub, scripts de classificação/preflight/release, allowlists e testes de produção, o runbook de release e a spec consolidada `deployment-operations`. A migration aplica apenas novas CHECK constraints às tabelas de configuração do ajuste de prévias. O deploy pode causar indisponibilidade temporária da API e do worker Markina; nenhuma operação remota será iniciada sem inventário atual, plano de impacto e aprovação protegida do fingerprint exato.
