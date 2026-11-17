# Inventário de consumidores de hostname

Data: 2026-11-07. Escopo deste documento: busca estática local no código atual. A inspeção externa posterior está separada em `operations-inventory.md`.

| Contrato | Consumidores encontrados | Efeito da ativação |
|---|---|---|
| Normalização e resolução exata | `backend/app/tenant_hosts.py:45-82`; `backend/app/main.py:1534,1639` | Usa o cabeçalho `Host` da requisição e resolve somente correspondência exata do banco. Host reservado retorna sem tenant. A origem pública só serve o tenant único sem host explícito; hostname desconhecido não cai no proprietário. |
| Sessão de cliente/host canônico | `backend/app/auth.py:current_session`, ramo `Role.CLIENT` | Revalida `Host` contra o hostname canônico na sessão de cliente. A sessão administrativa usa vínculo administrativo ativo; não se atribui tenant administrativo pelo host recebido. |
| URLs de compra/galeria | `backend/app/tenant_hosts.py:99-125`; `backend/app/order_delivery.py:163-167`; `backend/app/notification_settings.py:345-388` | Links públicos são gerados a partir do tenant e hostname persistidos; reserva bloqueia URL até prontidão. Inclui entrega/notificações. |
| Reserva e interface do fotógrafo | `backend/app/photographer_subdomain.py:43-85`; `backend/app/photographer_onboarding.py:248-255`; `frontend/app/admin/tenant-address.ts`; `frontend/app/admin/settings/tenant-address-panel.tsx` | O fotógrafo escolhe uma vez e recebe estado `reserved`, sem URL pública ou autoativação. |
| Sessões/cookies | `backend/app/auth.py:create_session` e `current_session`. O `Set-Cookie` define `HttpOnly`, `Secure` fora de development, `SameSite=Lax` e `Path=/`, sem atributo `Domain`; portanto permanece host-only. | Preservar o escopo host-only; não introduzir `Domain=pickyourpic.com.br`, compartilhamento de sessão ou token em URL. |

Busca estática por `tenant_for_host`, `tenant_id_for_host`, `canonical_host_for_tenant`, `purchase_url_for_tenant`, `public_gallery_url_for_tenant`, `request_hostname` e `canonical_host_status` encontrou os consumidores acima em `backend/app` e `frontend/app`; não encontrou chamada direta adicional em workers. `order_delivery` e `notification_settings` são consumidores indiretos em fluxos de entrega/comunicação. A API pública e a sessão de cliente leem `request.headers.get("host")`; a busca não encontrou uso de `X-Forwarded-Host` para selecionar tenant.

Compatibilidade importante: `backend/app/tenant_hosts.py:68,100` mantém comportamento para hostname legado com status nulo. O novo estado `ready` é necessário para hosts SaaS reservados; não se deve apertar essa condição e quebrar o hostname legado `markina`. A reserva já falha fechada. Não há oportunidade segura de remover ou consolidar código nesta área; a implementação deve reutilizar esses helpers e acrescentar somente a ativação explícita e suas verificações.

Limite da evidência: inventário estático não comprova configuração efetiva de NPM, DNS, portas ou headers enviados pelo proxy. O snapshot operacional separado registra essas observações e os gates ainda pendentes; ele não comprova uma publicação futura do runtime SaaS.
