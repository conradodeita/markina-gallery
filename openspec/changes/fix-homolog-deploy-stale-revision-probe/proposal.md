# Proposal

## Why

O deploy de homologação para antes de trocar serviços porque consulta a revisão Alembic com a imagem antiga do serviço `migrate`, que pode não reconhecer a revisão já aplicada no banco. O probe precisa ler o estado persistido diretamente e manter o deploy restrito ao projeto Markina.

## What Changes

- Consultar a revisão atual do banco sem depender da imagem antiga de `migrate`.
- Comparar o schema após a migration com a revisão-alvo do código novo.
- Expor diagnóstico sanitizado quando a leitura da revisão falhar, preservando o comportamento de interromper antes de alterar os serviços.
- Registrar regressões para o probe pré-deploy e para a confirmação pós-migration.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

Nenhuma. Esta correção ajusta a implementação do deploy; não altera comportamento funcional do produto nem o contrato operacional existente.

## Impact

Afeta `scripts/deploy-homolog.sh`, suas validações automatizadas e este change OpenSpec. Não altera APIs, dependências, dados ou recursos do servidor até o deploy autorizado. Nenhuma migration nova é necessária.
