# Proposal

## Why

A reserva local do link do fotógrafo distingue corretamente `reserved` de `ready`, mas a zona Cloudflare ainda não publica hosts de tenant e o Nginx Proxy Manager não possui rota/certificado wildcard. Depois da migração DNSSEC validada, é necessário definir um caminho operacional que habilite esses links sem mudar o tráfego atual da raiz ou de `markina` e sem encaminhar tenants para runtime SaaS incompatível.

## What Changes

- Preparar a ativação operacional de `*.pickyourpic.com.br` como DNS-only, apontando ao endereço de origem confirmado no inventário prévio; registros exatos da raiz e de `markina` permanecem inalterados.
- Emitir e renovar certificado wildcard Let's Encrypt pelo desafio DNS-01 do Cloudflare, com token de menor privilégio restrito à zona e custodiado por emissor operacional isolado do Nginx Proxy Manager; o NPM recebe somente o certificado pelo helper restrito.
- Configurar uma rota wildcard no Nginx Proxy Manager para o upstream da aplicação confirmado no inventário, somente depois de o runtime SaaS integrado atender o contrato de host e isolamento.
- Oferecer ao PlatformOwner uma ação explícita para promover um host reservado a `ready` somente após os gates de infraestrutura e isolamento, reautenticada por senha + TOTP, idempotente e auditada.
- Manter hosts reservados, desconhecidos, inativos ou suspensos sem contexto de tenant e sem fallback para a conta proprietária.
- Exigir inventário atualizado, plano de impacto zero, validações e autorização humana específica antes de qualquer mudança pública em DNS, certificado ou Nginx. Esta change não autoriza execução externa.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `tenant-subdomain-onboarding`: especifica o gate operacional para provisionar TLS/rota wildcard e promover o host reservado somente após comprovar DNSSEC, isolamento e compatibilidade de todos os consumidores de tenant.
- `platform-admin/owner-console`: define a ação administrativa segura e auditável que habilita um hostname validado.
- `deployment-operations`: define a publicação wildcard DNS-only, certificado DNS-01, rota no Nginx Proxy Manager, custódia mínima do token e operação com preservação dos hosts existentes.

## Impact

Afeta a zona `pickyourpic.com.br` no Cloudflare, o Nginx Proxy Manager compartilhado, a renovação Let's Encrypt, a ação do PlatformOwner e a resolução de `Host` do runtime Pick-your-Pic. O plano preserva os apontamentos e o caminho atual de `pickyourpic.com.br` e `markina.pickyourpic.com.br`, não altera recursos de outros projetos e não muda o ambiente externo nesta etapa. Um emissor operacional separado do NPM foi implementado e validado localmente em `archive/2026-11-08-prepare-operational-wildcard-certificate-issuer`; isso não comprova instalação no Oracle, custódia real, emissão pública, renovação operacional ou rota. A instalação no host, o token real, o upstream, portas, rede, consumidores de host e compatibilidade do runtime ainda precisam de inventário e autorização específicos.
