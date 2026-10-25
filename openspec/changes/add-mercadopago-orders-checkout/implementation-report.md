# Implementação — Checkout Transparente Mercado Pago Orders

## Resultado e limite da evidência

Implementação de desenvolvimento no worktree `mercadopago-orders`, branch `feature/mercadopago-orders`, base `origin/main` cef5bdf8. Checkout integrado por Orders, cartão oficial em uma parcela e MP Pix; PIX manual permanece independente. Não houve publicação, migration operacional, operação financeira real ou alteração de credenciais de produção.

Validação local concluída: matriz final de **42 testes Orders em PostgreSQL**, **4 testes de configuração**, **97 regressões aprovadas/7 skips**, **16 regressões adicionais**. Checkpoint frontend final de **84 testes em 13 arquivos**, build/typecheck/lint e matriz visual. Os detalhes e repetições estão em [validation.md](validation.md). Lint frontend completo tem 36 avisos e zero erros. Essas contagens não devem ser somadas como testes distintos.

Validação externa de desenvolvimento **executada**: identidade brasileira de teste verificada, montagem e tokenização no SDK oficial, cartão APRO/FUND/CONT, Pix/QR/cancelamento, Pix aprovado pelo simulador oficial, refund parcial/integral, recuperação de resposta perdida, projeções e CSV. **Duas notificações genuínas do Mercado Pago**, assinadas, foram concluídas em uma tentativa cada; o painel também confirmou HTTP 200. IDs e estados estão em [external-validation.md](external-validation.md). Não foi criada conta extra. Autenticações exigidas pelo Mercado Pago foram realizadas pelo proprietário. Túnel e servidores temporários foram encerrados. A URL encerrada permanece somente em Teste: o formulário não aceita apagá-la nem salvar sem eventos; substituir antes de novo ensaio. Esta evidência não autoriza publicação em produção nem substitui revisão humana.

## Seguimento autorizado pelo proprietário — 24/10/2026

O proprietário escolheu o aceite final na instalação de produção, exclusivamente com credenciais de teste e seu próprio administrador/cliente, e solicitou card de configuração mais claro e logos na escolha do cliente. A execução operacional permanece pendente do inventário/plano/aprovação específicos: [release-plan.md](release-plan.md).

Preparação validada: **58 testes PostgreSQL/contratos operacionais**, **5 de configuração** (incluindo dois fotógrafos por HTTP), **22 regressões SQLite** (sobreposição explícita com configuração), **87 frontend em 14 arquivos**, além das regressões anteriores. Não somar repetições. Visual dos componentes reais com dados sintéticos: **24 capturas** em três larguras e dois temas, sem overflow/erro JS/imagem ausente. Nenhum servidor/túnel foi reaberto para essa inspeção.

- Cada fotógrafo cadastra sua aplicação pela UI com senha/OTP; contas/flags/versões/webhooks e desafios não cruzam tenants.
- Conta de teste operacional requer par tenant/cliente no servidor. Carrinho e envio aplicam o gate; retirada da permissão preserva conciliação/cancelamento já iniciados. Cobrança real continua bloqueada.
- API e worker são os únicos consumidores do cofre genérico no Compose. Binding operacional ainda precisa ser verificado no alvo.
- Compras de teste são identificadas e excluídas de receita/vendas reais e CSV padrão; detalhes preservam TESTE. Conta real sintética conserva os indicadores/CSV anteriores.
- Card responsivo com dicas acessíveis, status, referências oficiais, segredos sem preenchimento e URL completa copiável. Escolhas do cliente exibem thumbnails locais Pix/Mercado Pago, com texto e fluxos anteriores preservados.
- Varredura de 69 arquivos revisados não encontrou os valores reais de token/assinatura externos; SVGs não contêm scripts/eventos/rede. Nenhum `.env`, segredo remoto, produção ou histórico operacional foi alterado.

## Decisões implementadas

1. Aplicação/conta individual por fotógrafo, verificada por `/users/me`; credenciais cifradas/versionadas com isolamento de ambiente e tenant. OAuth/split não foram presumidos a partir da Payments API. Flags independentes PIX/MP; contas reais bloqueadas por padrão.
2. Tentativa preparada não é cobrança. Submit recalcula direitos/cotação/revisão, cria snapshots por galeria e persiste intenção/UUID/idempotência antes da rede. Cartão/CPF/e-mail de pagamento não entram no snapshot ou log desse módulo.
3. Resultado desconhecido não permite reemissão. Tentativas enviadas mantêm fotos/valor imutáveis; cancelamento precisa de confirmação. Recusa/expiração/cancelamento confirmados restauram somente fotos ainda disponíveis e autorizadas.
4. Aprovação depende de Orders e transação coerentes com conta/referência/método/valor. Notificação atrasada não rebaixa confirmação. Sobreposição de aprovação tardia entra em revisão; não confirma o pedido novo.
5. Inbox assinada, deduplicada e durável antes de ACK; processamento com locks, lease/fencing/backoff e reconciliação periódica inclusive após estados finais. Rotação da mesma conta preserva a versão original e recusa outro recebedor.
6. Refund bloqueia liberação; parcial/contestação/duplicidade ficam em revisão, sem repartir reembolso por fotografia. Histórico e IDs permanecem. Compartilhamento externo já conhecido precisa de revogação operacional no serviço externo.
7. Compras, painel, filtros, indicadores e CSV usam projeção financeira comum. Não há confirmação manual de MP; CSV padrão de quatro colunas preservado e detalhes são opt-in.
8. Schema 0088 aditivo, sem alteração dos IDs legados; rollback destrutivo recusado. Exclusão de cliente/reset não podem apagar evidência Orders. Workers existentes continuam tendo passagem no ciclo.

O [design.md](design.md) detalha contratos, concorrência, estados e trade-offs; [analysis.md](analysis.md) registra arquitetura, fontes e divergências; [integration-guide.md](integration-guide.md) fornece configuração/testes; [review.md](review.md) contém a revisão de segurança estruturada da skill.

## Cobertura de regressão e experiência

Os testes comprovam PIX e contratos legados, criação/autorização, estados financeiros, concorrência de banco com um único POST, isolamento de tenant, notificações repetidas/atrasadas, recuperação, reembolsos, alteração/abandono do carrinho, aprovação tardia, rotação, suspensão, lifecycle, filtros/exportação/estatísticas e continuidade do worker.

A matriz visual local cobre 390, 768 e 1440 px nos temas claro/escuro, cartão, MP Pix pendente, Compras, painel parcial e erro do SDK, com componente sintético claramente identificado. Montagem/tokenização e checkout oficial também foram verificados em Edge a 390 px no teste externo. Resposta perdida expôs contador de carrinho desatualizado; corrigido e repetido com comprovação de Carrinho (0), sem reenvio financeiro. Foram preservadas as fronteiras de API e a confirmação autoritativa do servidor.

## Skills e contribuições reais

| Skill | Utilização |
|---|---|
| Jev ai / jev-codex-token-saver | Duas seleções de evidência em buscas amplas para localizar arquitetura/specs/fronteiras; leituras diretas completaram lacunas |
| ai-memory-retrieval | Consulta das instruções e memória local para decisões de preservação financeira/continuidade; confrontadas com código atual. MCP indisponível, sem instalar hooks ou gravar memória |
| Mercado Pago: mp-integrate | Contratos Orders, SDK oficial, CTA integrado, componentes, idempotência e guia; documentação oficial específica prevaleceu nas divergências |
| Mercado Pago: mp-webhooks | HMAC, inbox, deduplicação, consulta autoritativa e recuperação |
| Mercado Pago: mp-review | Checklist de nove itens, reavaliado após testes reais de desenvolvimento; sem pontuação de qualidade oficial inventada. Regra desatualizada da skill sobre quality_evaluation Orders corrigida pela documentação atual |
| Mercado Pago: mp-test-setup / mp-connect | Preparação externa e verificação de disponibilidade das ferramentas; criação/autenticação MCP indisponível. Orientação antiga sobre comprador obrigatório corrigida pela fonte oficial atual |
| OpenSpec apply | Execução verificável e rastreabilidade na change; specs principais e arquivamento aguardam revisão humana |

## Continuidade e itens pendentes

- Retirada da URL temporária de Teste bloqueada pelo formulário do provedor: URL vazia é recusada e sem eventos Salvar fica desabilitado; não há exclusão visível/MCP disponível. Túnel/servidores encerrados e URL indisponível; substituir por nova URL autorizada antes de outro ensaio. Histórico e PostgreSQL dedicado permanecem para revisão.
- CONT permanece processing no provedor de teste e cancelamento foi recusado. Manter resultado verdadeiro; não limpar/alterar artificialmente o histórico financeiro.
- Credenciais Teste continuam fora do Git e não se tornam credenciais de cobrança real. Seu uso futuro na instalação operacional fica restrito ao par autorizado pelo servidor, conforme release-plan.md; nenhum segredo aparece nos relatórios.
- Completar revisão externa/homologação e revisão humana dos artefatos. Não sincronizar specs principais nem arquivar antes dessa revisão.
- Publicação, migration operacional e uso de credenciais reais continuam exigindo autorização específica; não estão incluídos nesta entrega.

## Arquivos modificados e adicionados

Inventário revisado do diff, sem caches, credenciais ou artefatos locais:

- `backend/app/admin_account.py`
- `backend/app/auth.py`
- `backend/app/checkout.py`
- `backend/app/client_lifecycle.py`
- `backend/app/global_pix.py`
- `backend/app/homolog_cleanup.py`
- `backend/app/main.py`
- `backend/app/mercadopago_api.py`
- `backend/app/mercadopago_checkout.py`
- `backend/app/mercadopago_projection.py`
- `backend/app/mercadopago_provider.py`
- `backend/app/mercadopago_settings.py`
- `backend/app/mercadopago_webhook.py`
- `backend/app/notification_delivery.py`
- `backend/app/order_delivery.py`
- `backend/app/ownership_schema.py`
- `backend/app/payment_availability.py`
- `backend/app/payment_export.py`
- `backend/app/statistics_report.py`
- `backend/app/unified_checkout.py`
- `backend/app/worker.py`
- `backend/migrations/versions/20261024_0088_mercadopago_orders.py`
- `backend/requirements.txt`
- `backend/tests/test_gallery_lifecycle.py`
- `backend/tests/test_mercadopago_checkout.py`
- `backend/tests/test_mercadopago_operations.py`
- `backend/tests/test_mercadopago_projections.py`
- `backend/tests/test_mercadopago_schema.py`
- `backend/tests/test_mercadopago_settings.py`
- `backend/tests/test_mercadopago_webhook.py`
- `backend/tests/test_mercadopago_worker.py`
- `backend/tests/test_tenant_migration.py`
- `backend/tests/test_tenant_owner_reset.py`
- `backend/tests/test_tenant_photographer_migration.py`
- `docker/docker-compose.yml`
- `docs/THIRD-PARTY-INVENTORY.md`
- `frontend/app/admin/payments/order-delivery.tsx`
- `frontend/app/admin/payments/page.tsx`
- `frontend/app/admin/settings/page.tsx`
- `frontend/app/admin/settings/payment-providers-panel.test.tsx`
- `frontend/app/admin/settings/payment-providers-panel.tsx`
- `frontend/app/admin/settings/payment-providers.module.css`
- `frontend/app/library/cart/mercadopago-resume.tsx`
- `frontend/app/library/cart/page.tsx`
- `frontend/app/library/checkout/card-payment.tsx`
- `frontend/app/library/checkout/checkout.module.css`
- `frontend/app/library/checkout/checkout.test.tsx`
- `frontend/app/library/checkout/page.tsx`
- `frontend/app/library/mercadopago-product.test.tsx`
- `frontend/app/library/mercadopago.ts`
- `frontend/app/library/payment-logo.tsx`
- `frontend/app/library/payment-methods.module.css`
- `frontend/app/library/purchase-card.tsx`
- `frontend/app/library/purchases/page.tsx`
- `frontend/public/payments/README.md`
- `frontend/public/payments/mercadopago.svg`
- `frontend/public/payments/pix.svg`
- `frontend/scripts/mercadopago-visual-qa.cjs`
- `openspec/changes/add-mercadopago-orders-checkout/.openspec.yaml`
- `openspec/changes/add-mercadopago-orders-checkout/analysis.md`
- `openspec/changes/add-mercadopago-orders-checkout/design.md`
- `openspec/changes/add-mercadopago-orders-checkout/external-validation.md`
- `openspec/changes/add-mercadopago-orders-checkout/implementation-report.md`
- `openspec/changes/add-mercadopago-orders-checkout/integration-guide.md`
- `openspec/changes/add-mercadopago-orders-checkout/proposal.md`
- `openspec/changes/add-mercadopago-orders-checkout/release-plan.md`
- `openspec/changes/add-mercadopago-orders-checkout/review.md`
- `openspec/changes/add-mercadopago-orders-checkout/specs/deployment-operations/owner-reset/spec.md`
- `openspec/changes/add-mercadopago-orders-checkout/specs/gallery-sales/global-pix-configuration/spec.md`
- `openspec/changes/add-mercadopago-orders-checkout/specs/gallery-sales/mercadopago-orders/spec.md`
- `openspec/changes/add-mercadopago-orders-checkout/tasks.md`
- `openspec/changes/add-mercadopago-orders-checkout/validation.md`
- `scripts/reset_homolog_owner.py`
- `scripts/test_third_party_report.py`
- `scripts/third_party_report.py`
