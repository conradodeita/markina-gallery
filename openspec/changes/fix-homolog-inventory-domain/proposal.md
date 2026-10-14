# Proposal

## Why

O workflow de inventário ainda valida o domínio antigo `markina-homolog.duckdns.org` tanto na configuração Compose quanto nos health checks públicos. A homologação atual usa `markina.pickyourpic.com.br`, o que causa falhas recorrentes e impede que o inventário produza evidência confiável.

## What Changes

- O workflow SHALL receber `HOMOLOG_PUBLIC_BASE_URL` do Environment `homolog` e validá-la como origem HTTPS sem caminho, query ou credenciais.
- O script remoto SHALL comparar essa origem com `PUBLIC_APP_ORIGIN` da configuração Compose, sem expor valores de ambiente.
- Os health checks públicos SHALL usar a mesma origem validada; logs podem apresentar somente o hostname.
- Os testes de política SHALL proteger origem ausente, inválida ou divergente e prevenir regressão para domínio fixo.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `deployment-operations`: o inventário manual usa a origem pública configurada para validar topologia e health checks.

## Impact

Afeta `.github/workflows/inventory-homolog-readonly.yml`, `scripts/inventory-homolog-readonly.sh`, `scripts/test_readonly_homolog_inventory_policy.py` e a spec de operações de deploy. Não altera serviços, dados, segredos ou configuração do servidor; utiliza o secret existente `HOMOLOG_PUBLIC_BASE_URL` apenas como valor de comparação e health check.
