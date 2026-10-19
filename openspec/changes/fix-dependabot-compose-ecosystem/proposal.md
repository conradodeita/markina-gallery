# Proposal

## Why

A entrada Dependabot `docker` aponta para `/docker`, que contém Docker Compose e overlays, mas não Dockerfiles nem manifests Kubernetes. A verificação real falha e deixa as imagens declaradas nos arquivos Compose sem monitoramento.

## What Changes

- Alterar somente a entrada de `/docker` para o ecossistema suportado `docker-compose`.
- Preservar as entradas `docker` de `/backend` e `/frontend`, limite de PRs, grupos, agenda semanal e revisão humana sem automerge.
- Proteger por teste a cobertura dos cinco manifests Compose nomeados e overlays encontrados no diretório.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `deployment-operations/external-dependency-monitoring`

## Non-goals

- Atualizar versões de dependências ou imagens.
- Alterar imagens, serviços, overlays, workflows de deploy, Oracle ou ambientes.
- Integrar qualquer PR de atualização aberto pelo Dependabot.
