# Inventário de acessos — 03/11/2026

Escopo: árvore local `feature/pickyourpic-saas-mainline`, base `6af538ec` com o diff SaaS preservado. Inventário de fontes, sem consultar registros, segredos, fotografias ou backups. Não descreve publicação.

## Identidade e permissões

| Fonte | Escrita | Leituras e contrato preservado |
| --- | --- | --- |
| `system_monitor/models.py`: `PlatformOwner` | `system_monitor/grants.establish_owner`: CLI offline, confirmação de administrador verificado + e-mail, vínculo ativo, singleton, referência; transferência recusada | `system_monitor/access.is_owner`: UUID + e-mail verificado. Monitor exige ainda seus grants; carteira e MP locais usam a identidade por decisão comercial explícita. |
| `MonitorGrant` | `grants.change_grants`: upsert offline de `metrics/tree/incidents/export`, dry-run padrão, revogação explícita | `system_monitor/routes`, `access.permissions`, coleta/export e capabilities. Grant técnico não concede gestão comercial, mesmo para operador. |
| `auth.InstallationOperator` | `provision_installation_operator`: grant/revoke offline e evento `installation_operator.*`; nenhuma criação de tenant | `installation_operator.operator_is_active`, `main.require_installation_operator`, `/admin/installation-capabilities`, capacidade e observabilidade facial; exige também proprietário. |
| Proprietário comercial local | Não há concessão automática por `MonitorGrant` nem `InstallationOperator` | `main._require_credit_owner`, `photographer_credits._require_owner`, `mercadopago_credit_purchases.receiver_tenant_id`: pacotes, concessões/revogações e recebedor do proprietário. Esta implementação das fases anteriores substitui o diagnóstico inicial de ausência de autoridade comercial. |
| Homologação/reset | `homolog_cleanup` classifica tabelas do monitor como protegidas; `scripts/reset_homolog_owner.py` inventaria propriedade/operador e preserva contas | Não reutilizar limpeza ou reset como revogação, onboarding ou suspensão. |

Paths da tabela acima são relativos a `backend/app`, exceto `scripts/`. Migrations anteriores criam tabelas técnicas e não concedem automaticamente autoridade. `0070/0071` e migrations do monitor/operador mantêm seus contratos; `0094/0095` implementam carteira/compras somente locais.

## Estado do tenant e fronteiras

- `auth.Tenant` no baseline: UUID, `status IN ('active','suspended')`, host canônico e criação. A prova local de cadastro acrescentou nome opcional em 0097, somente do fotógrafo que o informou, sem backfill. `TenantAdmin` guarda vínculos ativos; status do tenant não revoga nem remove o vínculo.
- `tenancy.require_admin_tenant/require_single_tenant`, `acervo_context.require_active_owner`, `main.directory_tenant_id` e `auth.current_session` recusam contexto suspenso, ausente ou ambíguo; o guard `before_commit` revalida owners e vínculos. Sessão expirada/revogada continua recusada.
- `tenant_hosts`, `public_gallery_access`, `private_membership` e produtores de URLs exigem tenant ativo. Suspender não apaga cookies/sessões nem os torna autorizados; reativar pode tornar uma sessão ainda válida novamente utilizável segundo o contrato existente. Invalidação definitiva precisa de decisão própria.
- Consumidores assíncronos de status: `worker` (mídia, WhatsApp, outboxes, limpeza e retenção), `notification_delivery`, `membership_notifications`, `private_upload_batches`, `gallery_lifecycle`, `preview_adjustment/service`, `facial/{engine,indexing,jobs,lifecycle,notifications}`, `capacity_observability/queues` e `mercadopago_webhook`.
- `mercadopago_credit_purchases` verifica recebedor ativo; compras de crédito e compra de fotografias têm inboxes e referências separadas. Pausar tenant pode impedir conciliação em caminhos que filtram `active`. Não habilitar uma rota de suspensão sem definir e testar essa fronteira.
- `photographer_credits` lista estado, verifica conta na reserva/reconciliação e preserva ledger; bloqueio financeiro após chargeback é conceito distinto de `Tenant.status`.
- Escritas normais de criação: `provision_photographer`/`seed_admin`, migrations e fixtures sintéticas. Não foi localizada rota operacional global de alteração de status nesta base. Testes alteram status deliberadamente para provar recusa; não representam API de produto.

## Provisionamento

`provision_photographer.plan_provisioning` valida e-mail, destino, vínculo único e conta ativa sem escrever. `provision_photographer` só escreve com `apply`, trava tabelas no PostgreSQL e valida credenciais externas para administrador novo. Cria tenant, carteira finita vazia, administrador verificado e vínculo; preserva credenciais existentes em replay. CLI exige confirmação do mesmo UUID. `seed_admin` reutiliza o serviço. Nenhuma dessas funções representa verificação de e-mail ou convite de onboarding web. Não expor senha/TOTP do CLI no console.

## Auditoria e retenção

`auth.AuditEvent` contém `id`, `tenant_id` opcional, `event`, `subject` e `created_at`; `auth.audit` é o wrapper central. Não possui ator/resultado/origem estruturados nem proteção append-only de banco. Não apresentá-lo como novo log global completo.

Escritores diretos: `auth`, `client_lifecycle`, `commercial_removal`, `commercial_retention`, `gallery_cleanup`, `provision_installation_operator`, `facial/{calibration,policy,purge,retention,representation,rollout,rollout_operation,search,search_worker}`. Chamadores do wrapper incluem autenticação/segurança em `main`, grants/rotas do monitor, carteiras/compras, integrações e fluxos operacionais. A semântica de `subject` é heterogênea: não exportar seu conteúdo bruto na futura UI global.

Leituras: rate limit em `auth.enforce_rate_limit`, inventário/preservação de `homolog_cleanup`, reset e testes. Exclusões: `homolog_cleanup` remove auditoria operacional somente em sua limpeza autorizada e preserva padrões administrativos; novo log global deve ser explicitamente protegido nesse inventário. As migrations também precisam preservar o histórico legado.

## Verificação reproduzível

Busca de símbolos/aliases e revisão de consumidores: `rg -n 'PlatformOwner|MonitorGrant|InstallationOperator|Tenant.status|tenant.status|owner.status|provision_photographer|AuditEvent|\baudit\(' backend/app backend/migrations scripts -g '*.py'`; revisão adicional de nomes físicos `platform_owner/system_monitor_grant/installation_operator/audit_event` e testes correspondentes.

Cobertura existente a executar antes de fechar esta task: `test_system_monitor`, `test_tenant_installation_operator`, `test_tenant_provisioning`, `test_tenant_credit_browse` e negativas comerciais de `test_photographer_credits`. Não remover nenhum consumidor/grant; não há refatoração segura necessária para o inventário.

## Índice de referências diretas (sem conteúdo de dados)

Busca estática em Python de runtime, migrations e scripts; leituras indiretas seguem os resolvedores descritos acima. Linhas correspondem ao estado local desta retomada. Testes têm evidência própria em validation.md.

| Grupo | Arquivo | Linhas |
| --- | --- | --- |
| Identidade/grants | `backend/app/auth.py` | 254, 256, 3478, 3479, 3597, 3667, 3696 |
| Identidade/grants | `backend/app/homolog_cleanup.py` | 54, 61, 135 |
| Identidade/grants | `backend/app/installation_operator.py` | 9, 14, 15, 16 |
| Identidade/grants | `backend/app/main.py` | 1019, 1020, 3199, 3214, 3216, 3229, 3242 |
| Identidade/grants | `backend/app/mercadopago_credit_purchases.py` | 33, 129 |
| Identidade/grants | `backend/app/ownership_schema.py` | 15, 16, 18 |
| Identidade/grants | `backend/app/provision_installation_operator.py` | 13, 29, 42, 43, 55, 65 |
| Identidade/grants | `backend/app/system_monitor/access.py` | 8, 12, 14, 26, 27, 28 |
| Identidade/grants | `backend/app/system_monitor/grants.py` | 12, 24, 28, 43 |
| Identidade/grants | `backend/app/system_monitor/models.py` | 13, 15, 23, 24 |
| Identidade/grants | `backend/migrations/versions/20261001_0071_installation_operator.py` | 14 |
| Identidade/grants | `backend/migrations/versions/20261009_0072_system_monitor.py` | 12, 18 |
| Identidade/grants | `backend/migrations/versions/20261031_0094_photographer_credit_wallet.py` | 18, 22, 68, 112, 116, 219 |
| Identidade/grants | `backend/migrations/versions/20261101_0095_mercadopago_credit_purchases.py` | 95, 114 |
| Identidade/grants | `scripts/orders_pilot_release.py` | 1142 |
| Identidade/grants | `scripts/reset_homolog_owner.py` | 66, 72, 118, 120, 156, 157 |
| Status/provisionamento | `backend/app/acervo_context.py` | 15 |
| Status/provisionamento | `backend/app/auth.py` | 3409, 4062 |
| Status/provisionamento | `backend/app/capacity_observability/queues.py` | 150, 209 |
| Status/provisionamento | `backend/app/client_identity.py` | 17 |
| Status/provisionamento | `backend/app/facial/engine.py` | 303 |
| Status/provisionamento | `backend/app/facial/indexing.py` | 326 |
| Status/provisionamento | `backend/app/facial/jobs.py` | 158 |
| Status/provisionamento | `backend/app/facial/lifecycle.py` | 309, 352 |
| Status/provisionamento | `backend/app/facial/notifications.py` | 110, 127 |
| Status/provisionamento | `backend/app/gallery_lifecycle.py` | 320 |
| Status/provisionamento | `backend/app/main.py` | 1038 |
| Status/provisionamento | `backend/app/membership_notifications.py` | 88 |
| Status/provisionamento | `backend/app/mercadopago_credit_purchases.py` | 138, 646 |
| Status/provisionamento | `backend/app/mercadopago_webhook.py` | 96, 118, 211 |
| Status/provisionamento | `backend/app/notification_delivery.py` | 201, 216 |
| Status/provisionamento | `backend/app/photographer_credits.py` | 157, 274, 807 |
| Status/provisionamento | `backend/app/platform_console.py` | 82, 108, 192, 208 |
| Status/provisionamento | `backend/app/preview_adjustment/service.py` | 304 |
| Status/provisionamento | `backend/app/private_membership.py` | 65, 113 |
| Status/provisionamento | `backend/app/private_upload_batches.py` | 118 |
| Status/provisionamento | `backend/app/provision_photographer.py` | 52, 57, 65, 89, 105, 134 |
| Status/provisionamento | `backend/app/public_gallery_access.py` | 220 |
| Status/provisionamento | `backend/app/seed_admin.py` | 11 |
| Status/provisionamento | `backend/app/system_monitor/activity.py` | 50, 84 |
| Status/provisionamento | `backend/app/tenancy.py` | 31, 64, 96 |
| Status/provisionamento | `backend/app/tenant_hosts.py` | 68, 75, 100, 107 |
| Status/provisionamento | `backend/app/worker.py` | 288, 300, 422, 446, 723, 812, 847, 957, 997, 1022 |
| Status/provisionamento | `backend/migrations/versions/20261103_0096_platform_admin_audit.py` | 30 |
| Status/provisionamento | `scripts/reset_homolog_owner.py` | 128 |
| Auditoria legada | `backend/app/admin_account.py` | 182, 215, 219, 250, 258, 296, 327, 337, 362 |
| Auditoria legada | `backend/app/auth.py` | 3392, 3393, 3940, 3941, 3951, 3952, 3953, 3959, 3964, 3996, 4047, 4094, 4098, 4118, 4141, 4146, 4159, 4215, 4254, 4265, 4348 |
| Auditoria legada | `backend/app/checkout.py` | 392, 434, 458, 501 |
| Auditoria legada | `backend/app/client_lifecycle.py` | 20, 605, 608 |
| Auditoria legada | `backend/app/commercial_removal.py` | 12, 134 |
| Auditoria legada | `backend/app/commercial_retention.py` | 12, 150 |
| Auditoria legada | `backend/app/facial/calibration.py` | 12, 76 |
| Auditoria legada | `backend/app/facial/policy.py` | 12, 106, 158, 217, 252, 284 |
| Auditoria legada | `backend/app/facial/purge.py` | 16, 110, 280, 389 |
| Auditoria legada | `backend/app/facial/representation.py` | 16, 112, 223, 383 |
| Auditoria legada | `backend/app/facial/retention.py` | 12, 97 |
| Auditoria legada | `backend/app/facial/rollout.py` | 14, 370 |
| Auditoria legada | `backend/app/facial/rollout_operation.py` | 13, 172 |
| Auditoria legada | `backend/app/facial/search.py` | 15, 286, 438, 614, 656 |
| Auditoria legada | `backend/app/facial/search_worker.py` | 15, 604 |
| Auditoria legada | `backend/app/folder_processing_api.py` | 114, 133, 165 |
| Auditoria legada | `backend/app/gallery_cleanup.py` | 10, 213, 293 |
| Auditoria legada | `backend/app/homolog_cleanup.py` | 19, 74, 135, 136, 137, 138, 139, 140, 196, 197, 214, 215, 314 |
| Auditoria legada | `backend/app/main.py` | 1401, 1583, 1598, 1611, 1623, 1628, 1652, 1703, 1709, 1738, 1773, 1777, 1807, 1818, 1832, 1873, 1885, 1892, 1913, 1919, 1926, 1941, 1960, 1981, 1987, 2011, 2018, 2042, 2050, 2051, 2054, 2095, 2114, 2237, 2269, 2286, 2351, 2444, 2509, 2532, 2569, 2593, 2708, 2735, 2764, 2916, 3286, 3307, 3833, 3926, 3941, 3993, 4093, 4426, 4481, 4739, 4861, 4926, 4970, 4997, 5032, 5208, 5368, 5457, 5527, 5584, 5585, 5668, 5699, 5720, 5780, 5812, 5839, 6048, 6086, 6153, 6232, 6535, 6579, 6676, 6892, 6910, 6934, 7002, 7025, 7414, 7416, 7483, 7513, 7692, 7727, 7749, 7766, 8007, 8140, 8256, 8477, 8535, 8725, 8741, 8761, 8796, 8869, 9150, 9196, 9356, 9374, 9492, 9932, 9941, 9963, 9969, 10549, 10592, 10646, 10666, 10692, 10766, 10798, 10822, 10834, 10837, 10843, 11217, 11372, 11412, 11457, 11482, 11539, 11595, 11623, 11625, 11751, 11837, 11957, 11959, 12025, 12113, 12229, 12279, 12389, 13135, 13261, 13284, 13315, 13362, 13412 |
| Auditoria legada | `backend/app/mercadopago_api.py` | 171 |
| Auditoria legada | `backend/app/mercadopago_checkout.py` | 173, 398 |
| Auditoria legada | `backend/app/mercadopago_credit_purchases.py` | 240, 575, 698 |
| Auditoria legada | `backend/app/mercadopago_settings.py` | 159 |
| Auditoria legada | `backend/app/order_delivery.py` | 130, 148 |
| Auditoria legada | `backend/app/ownership_schema.py` | 24 |
| Auditoria legada | `backend/app/photographer_credits.py` | 377, 409, 462, 534 |
| Auditoria legada | `backend/app/platform_console.py` | 242 |
| Auditoria legada | `backend/app/preview_adjustment/api.py` | 60, 151 |
| Auditoria legada | `backend/app/provision_installation_operator.py` | 13, 65 |
| Auditoria legada | `backend/app/system_monitor/grants.py` | 29, 47 |
| Auditoria legada | `backend/app/system_monitor/routes.py` | 73, 98 |
| Auditoria legada | `backend/app/unified_checkout.py` | 388, 542, 596 |
| Auditoria legada | `backend/app/whatsapp_channel.py` | 147, 164 |
| Auditoria legada | `backend/migrations/versions/20260825_0001_unified_authentication.py` | 70, 76, 81 |
| Auditoria legada | `backend/migrations/versions/20260930_0070_photographer_isolation_schema.py` | 187, 820, 959, 1170 |
| Auditoria legada | `scripts/reset_homolog_owner.py` | 73, 148, 161 |
