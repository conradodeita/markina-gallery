# Proposal

## Why

A atualização de Vendas e pagamentos precisa entregar em produção o código correspondente da interface e da API; atualizar somente `web` deixa chamadas novas sem suporte. O procedimento atual, ainda local, restringe-se a `web`, portanto precisamos de um fluxo aprovado que publique os dois serviços como uma versão coordenada sem tocar dados e dependências do host.

## What Changes

- Acrescentar um modo de release da aplicação composto por `api` e `web`, ambos oriundos do mesmo commit aprovado de `main`.
- Permitir inventário e registro aprovado do baseline inicial de API e das imagens reais API/web, sem recriar serviços.
- Verificar a identidade e a saúde de ambos os contêineres, configurações Compose, portas e domínio antes da execução.
- Construir e preservar imagens de API e web, atualizar somente esses dois serviços, e validar as duas healthchecks e as rotas HTTPS.
- Registrar a versão anterior e a tentativa/versão saudável da aplicação em conjunto, com rollback coordenado das duas imagens.
- Impedir concorrência com o procedimento web-only, preservando seu modo existente para alterações exclusivas de `web`.
- Documentar explicitamente que Compose não torna a troca dos dois serviços atômica e que a operação pode causar interrupção breve.
- Manter inventário somente-leitura, checkout limpo, SHA alcançável por `origin/main`, gate por configuração/código de aprovação, revisão e aprovação humana por execução.
- Recusar a primeira publicação coordenada até reconciliar e aprovar o SHA-base da API e um snapshot dos IDs reais das imagens de API e web.
- Não executar migrations neste fluxo; a presença de migrations ou alteração de configuração Compose invalida sua elegibilidade e exige procedimento separado.

## Capabilities

### New Capabilities

### Modified Capabilities

- `deployment-operations`: acrescenta release coordenado de produção para a aplicação `api` + `web`, com rollback do par, além do fluxo web-only existente.

## Impact

- Nova automação/runbook para produção e revisão do procedimento web-only apenas para exclusão mútua do release coordenado.
- Serviços afetados: `api` (FastAPI) e `web` (Next.js) do projeto Compose `markina-gallery`, no host e domínio de produção já documentados.
- PostgreSQL, Redis, workers, Nginx, volumes, redes, proxy, DNS, firewall, certificados, secrets e arquivos de ambiente não são mutados. Nenhuma migration será executada.
- Impacto permitido limita-se à atualização dos dois serviços: pode ocorrer indisponibilidade breve durante a troca; zero downtime não é garantido.
- Esta change prepara automação verificável e runbook, mas não autoriza acessar ou publicar em produção. A execução seguirá sujeita a inventário remoto atual e aprovação específica do SHA, inventário, impacto e código.
