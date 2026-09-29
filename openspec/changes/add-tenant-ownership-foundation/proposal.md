# Proposal

## Why

O relatório de arquitetura identifica galerias, fotos e administração sem proprietário fotógrafo explícito. A primeira entrega precisa estabelecer essa propriedade e migrar o legado com segurança, antes de ampliar a operação para fotógrafos independentes, com uma explicação verificável após cada deploy.

## What Changes

- Introduzir uma conta de fotógrafo (`Tenant`) e vínculo explícito entre essa conta e os administradores atuais.
- Persistir `tenant_id` em `ParentGallery`, `DerivedGallery` e `PhotoAsset`, com integridade entre raiz, galeria privada e foto; atribuir o legado inteiro à única conta atual após conferir o inventário.
- Resolver o contexto administrativo no servidor, revalidando o vínculo ativo. Novos registros recebem propriedade explícita; contexto ausente ou ambíguo interrompe a operação, sem escolher uma conta arbitrariamente.
- Manter esta entrega limitada a uma conta de fotógrafo operacional. A criação ou ativação de uma segunda conta depende de outra change com isolamento completo, configurações, clientes, jobs e testes B01/B02.
- Registrar antes e depois de cada deploy: entrega prevista/efetiva, teste acessível ao proprietário, evidências, limitações, versão/schema e condição de reversão.
- Exigir reconciliação entre o checkout local (última migration presente `20260925_0061`) e a implantação registrada no BENCH (`20260928_0068`) antes de qualquer liberação remota.

## Capabilities

### New Capabilities

- `tenant-foundation`: propriedade explícita das raízes, vínculo administrativo e migração do legado único, com operação restrita a um fotógrafo.

### Modified Capabilities

- `auth`: adicionar resolução e revalidação de contexto administrativo, preservando senha, TOTP e sessão persistida.
- `deployment-operations`: acrescentar contrato de entrega por etapa e gate de paridade da versão/schema.

## Impact

Backend SQLAlchemy, Alembic, seed administrativo, autorização e todos os caminhos que criam as três entidades afetadas, incluindo workers e fixtures. A migration deve ser ensaiada em PostgreSQL descartável com dados sintéticos; mudança remota depende de inventário atualizado, backup, plano de impacto zero e autorização explícita.

A interface e a operação comercial do fotógrafo atual permanecem compatíveis. Não há nova infraestrutura prevista nesta change. O planejamento não autoriza alterar `.env`, segredos, comprar recursos, publicar em `develop` com deploy automático, nem executar deploy.

## Non-goals

Isolamento SaaS completo; onboarding de outros fotógrafos; decisão sobre identidade do cliente entre fotógrafos; PIX/carrinho com recebedores distintos; suporte global; quotas, fairness, billing, novos workers, Object Storage, nova versão criptográfica ou mudança dos gates de busca facial. São etapas próprias do roadmap e não resultados desta primeira entrega.

## Deployment Context

O proprietário confirmou em 2026-09-29 que utiliza `https://markina-homolog.duckdns.org/` e pretende adotar um domínio profissional após a prova do produto. As primeiras entregas serão planejadas para esse endereço atual, sujeito ao inventário operacional antes de cada deploy. A escolha e a migração do novo domínio ficam para uma etapa posterior; não bloqueiam a fundação de propriedade do acervo nem integram seu escopo.

A futura troca deverá conferir os links de convite/notificação, autenticação, HTTPS e integrações vinculadas ao endereço, para preservar o acesso. Nenhum novo domínio foi escolhido e esta decisão não autoriza alterações atuais de DNS, proxy, certificados ou ambiente.

## Review

O proprietário autorizou iniciar a implementação deste recorte. A fundação de propriedade foi implementada em checkout isolado; decisões comerciais multitenant e autorização operacional continuam em gates separados. Revisão humana da liberação e do resultado precede sincronização/arquivo.
