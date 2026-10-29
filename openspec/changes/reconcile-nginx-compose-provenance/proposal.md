# Proposal

## Why

O inventário APP_ENV está bloqueado porque o Nginx ativo ainda referencia um Compose RAW aposentado e ausente. A inspeção somente-leitura de 29/10/2026 isolou essa fonte no Nginx; remover a referência da consulta não resolve a configuração antiga, que também contém um serviço Gemma sem imagem/build e diverge do hash do container.

## What Changes

- Preparar configuração durável e restrita ao Nginx, derivada de fontes verificadas e comparada com a operação atual antes de qualquer publicação.
- Preservar imagem imutável, configuração efetivamente carregada, montagem, rede, porta e políticas do Nginx; apresentar divergências em vez de aceitá-las automaticamente.
- Preparar atualização e recuperação limitadas ao Nginx, com inventário/fingerprint, backup verificável, revisão humana do plano e execução protegida.
- Conservar todos os demais containers, dados e integrações. Não restaurar nem ativar RAW/Gemma e não ignorar fontes ausentes no coletor APP_ENV.

## Capabilities

### New Capabilities

- `deployment-operations/compose-provenance`: origem durável e verificável do Compose usado pelo serviço de entrada preservado entre releases.

### Modified Capabilities

Nenhuma.

## Impact

O alvo operacional proposto é somente `markina-gallery/nginx`, publicado em `127.0.0.1:8080 → 80/tcp`, atendendo `https://markina.pickyourpic.com.br` pelo proxy externo existente. Recriação pode interromper brevemente o tráfego e exige plano específico antes de execução. Não modifica o proxy externo, DNS, certificados, API, web, workers, banco, segredos, pagamentos ou gates financeiros. Desbloqueia uma pré-condição de `transition-app-env-bound-integrations`, que continua pendente de seu inventário e aprovação próprios. A manutenção é limitada aos helpers de publicação/origem diretamente afetados; nenhuma limpeza geral faz parte desta change.
