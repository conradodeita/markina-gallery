# Proposal

## Why

Cada fotógrafo precisa escolher um endereço próprio sob pickyourpic.com.br. Em 05/11/2026 o proprietário definiu a escolha no primeiro acesso após verificar o e-mail, mantendo o ingresso leve e markina reservado. O resolvedor de host já existe, mas não há reserva self-service nem distinção entre endereço escolhido e infraestrutura pronta.

## What Changes

- Solicitar a escolha no painel após a verificação, com prévia do domínio e etapa em Configurações.
- Identificar a escolha como link/URL da marca e alinhar visualmente o aviso do primeiro acesso à área de conteúdo do painel.
- Evitar que a consulta opcional de elegibilidade do link apresente aviso global de acesso negado a contas do proprietário/legadas, preservando a negação da API.
- Reservar atomicamente um prefixo válido por tenant, com nomes de infraestrutura protegidos, idempotência e autorização pela sessão verificada.
- Reusar a unicidade de Tenant.canonical_host, acrescentando estado reservado que não habilita resolução de clientes nem geração de links públicos.
- Preservar tenants/hosts legados e não alterar gates financeiros/WhatsApp existentes.
- Provar escolha, conflito, isolamento e UI localmente. Publicação DNS curinga, TLS, proxy e promoção operacional do host terão gate próprio; não emitir credencial Cloudflare nem alterar produção.

## Capabilities

### New Capabilities

- `tenant-subdomain-onboarding`: escolha inicial, reserva e indicação de prontidão.

### Modified Capabilities

Nenhuma spec consolidada é sincronizada automaticamente. Compatibilidade do resolvedor existente será preservada para hosts legados.

## Impact

Tenant, migration aditiva local, resolvedor canônico, rotas autenticadas de onboarding e UI administrativa. Sem reatribuir contas, cookies compartilhados, troca autônoma posterior de endereço ou redirecionamento entre hosts. Sem deploy, DNS/TLS/proxy externo, secrets ou dados reais. Refatoração proporcional: reaproveitar contexto de onboarding e unicidade existentes; nenhuma limpeza fora do escopo.
