# Proposal

## Why

O objetivo imediato do planejamento é preparar o isolamento necessário para operar com fotógrafos independentes. O proprietário quer validar com poucos fotógrafos e clientes assim que o sistema estiver tecnicamente pronto e, nessa ocasião futura, aproveitar para testar o monitor durante as jornadas; não solicitou executar esse ensaio agora. A fundação atual bloqueia uma segunda conta e mantém clientes e configurações globais; habilitar várias contas sem completar o isolamento permitiria misturar pessoas, acervos e pagamentos.

## What Changes

Correção da fixture da PR136 após falha de CI em04/10: criar o schema dos novos testes de prévia a partir de `MetaData` privado, sem alterar o catálogo ORM compartilhado. Compilar/criar PostgreSQL primeiro com o metadata global altera regras de emissão de constraints no SQLAlchemy e enfraquece o DDL SQLite das suítes seguintes. Reproduzir as duas negativas existentes em sequência PostgreSQL→SQLite e adicionar regressão dessa fronteira; não remover asserts, desabilitar FKs, mudar dependências, autenticação ou aplicação além das duas remoções já autorizadas. Correção permanece no arquivo de testes da PR e nos registros correspondentes; sem merge/deploy enquanto CI não for novamente informado verde.

Publicação seletiva autorizada em 04/10/2026: após revisão do escopo e impacto, o proprietário respondeu “autorizado” à nova PR e publicação condicionada ao CI verde que ele próprio informará. Incluir somente a correção das duas prévias administrativas, suas regressões e registros OpenSpec; preservar e excluir as outras alterações locais. Sem upload antecipado, nova migration, alteração de pool/quota/segredo ou terceiros. Plano operacional: `admin-preview-pool-release-plan-20261004.md`.

Correção LOCAL autorizada em03/10/2026 após APIunhealthy/pooltimeouts nas prévias administrativas antes da rodada50: reproduzir concorrência com pool sintético pequeno, delimitar aquisição aninhada de autenticação e corrigir somente as rotas administrativas de prévia afetadas, sem mudar tamanho do pool, autenticação/isolamento/auditoria ou entrega privada. Validar sessões revogadas, conta/vínculo inativo, e-mail não verificado e recursos de outra conta com cookies reais. A autorização não inclui commit/push/deploy nem liberação antecipada dos uploads; logs remotos e latches permanecem preservados.

- Permitir operação controlada de duas contas de fotógrafo após completar e testar o isolamento do domínio, sem cadastro público de fotógrafos.
- **BREAKING**: tornar a identidade da cliente e a unicidade do telefone próprias de cada fotógrafo. Conforme decisão explícita do proprietário em 30/09/2026, o mesmo telefone pode identificar cadastros independentes, sem fusão ou compartilhamento automático de nomes, sessões, galerias, seleções, pedidos ou histórico.
- Resolver o fotógrafo no backend a partir do vínculo administrativo ou do link autorizado da galeria; vincular desafios OTP, sessões e convites ao mesmo contexto.
- Isolar acervo, clientes, comércio, PIX, branding, configurações, notificações, jobs, caches, arquivos e operações de manutenção. Dados técnicos de infraestrutura continuam próprios da instalação.
- Separar a permissão do dono da instalação para consultar o monitor agregado da permissão de um fotógrafo comum. Essa permissão permite diagnóstico sanitizado e não acesso implícito aos acervos de outros fotógrafos.
- Manter roteiro futuro de ensaio pequeno proposto: 2 fotógrafos × 3 clientes, 1 galeria e até 6 JPEGs sintéticos por fotógrafo; repetir um telefone nas duas contas e exercitar acesso concorrente limitado, comércio e negativas de acesso cruzado. Sua execução depende de isolamento completo, testes de engenharia aprovados e prontidão registrada; a intenção de validar assim que possível não autoriza ativação antecipada de contas.
- Na ocasião desse ensaio futuro, comparar relatórios `capacity-report/v1` antes, durante e depois. Filas faciais sem atividade continuam identificadas como tal; o ensaio não comprova desempenho facial nem capacidade máxima.

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

Preparação de canais após publicação: completar entrega do contrato de bindings aos consumidores de WhatsApp via arquivo Compose opcional raw e não versionado. Sem criação de arquivo real/segredos, alteração do canal existente ou recursos remotos na implementação local.

Backend FastAPI/SQLAlchemy/Alembic, resolvedores de identidade e autorização, rotas e workers do domínio, índices/constraints, configuração PIX/branding/notificações, caches e acesso à mídia, frontend de autenticação e capacidade, fixtures e testes PostgreSQL. A migration deve preservar o legado único e ser ensaiada em banco descartável antes de liberação autorizada.

Esta proposta substitui a restrição arquitetural de fotógrafo único somente depois de revisão e aceite explícitos. Não altera código, roadmap consolidado, banco, credenciais ou homologação nesta fase. A fundação `add-tenant-ownership-foundation` está no código e seu PR #115 foi integrado; suas evidências e pendências documentais de liberação precisam ser reconciliadas antes de iniciar esta implementação.

## Non-goals

Cadastro público/SaaS, cobrança da plataforma, quotas/fairness, aumento de workers, capacidade máxima, SLO novo, painel por fotógrafo, histórico automático do monitor, domínio novo, infraestrutura de terceiros, provisionamento automático Evolution/Drive, troca de criptografia ou autorização para processamento biométrico real. O piloto remoto e eventual limpeza dos dados criados exigem inventário e autorização próprios.

## Review

Decisões confirmadas: clientes independentes por fotógrafo, mesmo com telefone igual; validação pequena somente assim que o sistema estiver pronto, aproveitando essa ocasião para testar o monitor. A prioridade é completar a preparação e o isolamento; o ensaio não é uma ação imediata. Quantidade 2 × 3, provisionamento controlado, permissão do operador da instalação e detalhes do roteiro futuro são propostas para revisão. O aceite dos artefatos precede código; deploy e uso de canais externos têm autorização operacional separada.
