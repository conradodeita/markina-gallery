# Proposal

## Why

O proprietário quer validar o sistema com poucos fotógrafos e clientes, usando o monitor de capacidade durante as jornadas. A fundação atual bloqueia uma segunda conta e mantém clientes e configurações globais; habilitar várias contas sem completar o isolamento permitiria misturar pessoas, acervos e pagamentos.

## What Changes

- Permitir operação controlada de duas contas de fotógrafo após completar e testar o isolamento do domínio, sem cadastro público de fotógrafos.
- **BREAKING**: tornar a identidade da cliente e a unicidade do telefone próprias de cada fotógrafo. Conforme decisão explícita do proprietário em 30/09/2026, o mesmo telefone pode identificar cadastros independentes, sem fusão ou compartilhamento automático de nomes, sessões, galerias, seleções, pedidos ou histórico.
- Resolver o fotógrafo no backend a partir do vínculo administrativo ou do link autorizado da galeria; vincular desafios OTP, sessões e convites ao mesmo contexto.
- Isolar acervo, clientes, comércio, PIX, branding, configurações, notificações, jobs, caches, arquivos e operações de manutenção. Dados técnicos de infraestrutura continuam próprios da instalação.
- Separar a permissão do dono da instalação para consultar o monitor agregado da permissão de um fotógrafo comum. Essa permissão permite diagnóstico sanitizado e não acesso implícito aos acervos de outros fotógrafos.
- Preparar ensaio pequeno proposto: 2 fotógrafos × 3 clientes, 1 galeria e até 6 JPEGs sintéticos por fotógrafo; repetir um telefone nas duas contas e exercitar acesso concorrente limitado, comércio e negativas de acesso cruzado.
- Comparar relatórios `capacity-report/v1` antes, durante e depois do ensaio. Filas faciais sem atividade continuam identificadas como tal; o ensaio não comprova desempenho facial nem capacidade máxima.

## Capabilities

### New Capabilities

- `client-access/photographer-isolation`: propriedade e isolamento do domínio, clientes independentes e execução assíncrona delimitada por fotógrafo.
- `deployment-operations/small-multi-photographer-pilot`: provisionamento controlado e ensaio reproduzível pequeno com leituras reais do monitor.

### Modified Capabilities

- `auth`: contexto de fotógrafo em autenticação, OTP, sessões e autorização.
- `client-access/admin-client-directory`: diretório e unicidade de telefone restritos à conta do fotógrafo.
- `gallery-sales/global-pix-configuration`: PIX global dentro de cada conta e checkout com recebedor da mesma conta.
- `client-access/folder-audiences`: avisos usam configurações e destinatárias da conta proprietária.
- `deployment-operations/admin-capacity-diagnostics`: diagnóstico agregado exclusivo do dono/operador autorizado da instalação, sem concedê-lo aos demais fotógrafos.

## Impact

Backend FastAPI/SQLAlchemy/Alembic, resolvedores de identidade e autorização, rotas e workers do domínio, índices/constraints, configuração PIX/branding/notificações, caches e acesso à mídia, frontend de autenticação e capacidade, fixtures e testes PostgreSQL. A migration deve preservar o legado único e ser ensaiada em banco descartável antes de liberação autorizada.

Esta proposta substitui a restrição arquitetural de fotógrafo único somente depois de revisão e aceite explícitos. Não altera código, roadmap consolidado, banco, credenciais ou homologação nesta fase. A fundação `add-tenant-ownership-foundation` está no código e seu PR #115 foi integrado; suas evidências e pendências documentais de liberação precisam ser reconciliadas antes de iniciar esta implementação.

## Non-goals

Cadastro público/SaaS, cobrança da plataforma, quotas/fairness, aumento de workers, capacidade máxima, SLO novo, painel por fotógrafo, histórico automático do monitor, domínio novo, infraestrutura de terceiros, provisionamento automático Evolution/Drive, troca de criptografia ou autorização para processamento biométrico real. O piloto remoto e eventual limpeza dos dados criados exigem inventário e autorização próprios.

## Review

Decisão já confirmada: clientes independentes por fotógrafo, mesmo com telefone igual. Quantidade 2 × 3, provisionamento controlado, permissão do operador da instalação e detalhes do ensaio são propostas para revisão. O aceite dos artefatos precede código; deploy e uso de canais externos têm autorização operacional separada.
