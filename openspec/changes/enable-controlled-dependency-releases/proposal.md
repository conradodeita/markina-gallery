# Proposal

## Why

Os manifests corrigidos não são classificados como impacto de release. O web-only também confunde checkout compartilhado com origem da API, impedindo publicar um frontend isolado quando existem requisitos Python pendentes no mesmo SHA.

## What Changes

- Calcular impacto por serviço/imagem a partir dos contextos Compose/Dockerfile e includes de requisitos, distinguindo dependências, código protegido e infraestrutura operacional.
- Exigir prova do contexto de build e proveniência web antes de admitir requisitos Python pendentes; preservar a identidade independente da API e o snapshot não-web.
- Gerar plano de dependências a partir de inventário explícito, com IDs/digests/arquitetura, serviços ativos, bloqueios de homologação e rollback. Workers sem executor seguro permanecem bloqueados.
- Disponibilizar coletor somente leitura para o SSH já autorizado, sem consultar segredos ou dados de clientes.
- Manter dependências em escopo próprio que não aciona jobs de deploy em merges; preservar todos os gates existentes.

## Capabilities

### New Capabilities

- Nenhuma.

### Modified Capabilities

- `deployment-operations`: classificação e preparação de dependências por imagem, isolamento web e inventário manual restrito.

## Impact

Scripts de classificação, política web-only, coletor de inventário, testes, CI e runbook. Sem alteração de dependências, Compose, Dockerfiles, modelos ou dados. Autorização do proprietário no pedido de 20/10/2026 abrange planejamento, implementação, testes, PR e merge condicionado; não abrange publicação ou alteração da Oracle.
