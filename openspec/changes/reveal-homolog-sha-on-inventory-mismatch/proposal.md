# Proposal

## Why

O inventário remoto bloqueia corretamente qualquer consulta quando o `HEAD` do checkout de homologação diverge do SHA esperado, mas não informa qual SHA encontrou. Isso impede identificar a origem da divergência e reconcilia-la com o histórico de deploy sem recorrer a acesso remoto fora do procedimento previsto.

## What Changes

- Em divergência, o inventário SHALL imprimir somente o SHA esperado e o SHA observado no checkout fixo da Markina.
- Depois de informar a divergência, SHALL encerrar antes de consultar Compose, containers, banco, volumes ou endpoints públicos.
- SHA inválido continua sem acessar o checkout; SHA correspondente continua seguindo o inventário read-only existente.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `deployment-operations`: diagnóstico sanitizado da divergência de revisão no inventário de homologação.

## Impact

Afeta `scripts/inventory-homolog-readonly.sh`, `scripts/test_readonly_homolog_inventory_policy.py` e a spec `deployment-operations`. O ajuste não altera o servidor, arquivos, containers, dados, configuração, credenciais, deploy ou migration.

## Non-goals

- Não aceitar divergência para prosseguir com inventário.
- Não trocar automaticamente o checkout para `develop`, `main` ou qualquer outro SHA.
- Não corrigir a revisão remota nem publicar a change de produto.

## Revisão

Esta proposta e a delta spec SHALL ser revisadas e aceitas pelo proprietário antes de qualquer alteração de código, conforme o fluxo OpenSpec do repositório.
