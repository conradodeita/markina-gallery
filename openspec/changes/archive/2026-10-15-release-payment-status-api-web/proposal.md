## Why

A melhoria aprovada de Vendas e pagamentos foi integrada à main pelos PRs #188/#189, mas o checkout de produção está em `71be3b29659143293351968e15fb4886c2d72bf0`, com correções de pagamentos, entrega e autenticação ausentes da main. O container API contém `tenant_hosts.py` e a migration `20261014_0081`, ambos ausentes da main. Publicar a main atual causaria regressão. O procedimento existente de produção é restrito ao web e não publica o contrato de classificação da API.

## What Changes

- Reconciliar a main com a versão já instalada, preservando seus comportamentos e acrescentando a melhoria aprovada de situações financeiras.
- Documentar uma execução manual específica de release de API e web, com imagens anteriores identificadas, configuração preservada, sem migrations e com validação e recuperação.
- Exigir nova conferência do inventário e aprovação do alvo final antes da troca dos containers. A aprovação recebida em 2026-10-15 autoriza preparar o plano; as autorizações anteriores de push/merge permanecem vigentes.

## Capabilities

### New Capabilities

### Modified Capabilities
- `deployment-operations`: procedimento pontual de publicação conjunta de API e web para esta melhoria.

## Impact

Integração Git dos comportamentos já publicados e documentação operacional. Produção: projeto Compose `markina-gallery`, `/opt/markina-gallery`, domínio `markina.pickyourpic.com.br`, nginx local `127.0.0.1:8080`. Apenas API/web serão reconstruídos/recriados; nginx da Markina poderá receber recarga de configuração, necessária para resolver novamente o endereço da API. Nenhum recurso de terceiros, ambiente, migration, dado, worker, fila ou banco será alterado. A troca pode causar breve indisponibilidade da Markina.
