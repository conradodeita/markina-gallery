# Inventário da aposentadoria InfinitePay

## Base e limites da verificação

Inventário estático feito em 22/10/2026 na worktree `codex/prepare-payments-release-0086`. A worktree estava limpa antes desta change. A busca cobriu backend, frontend, migrations, CI, scripts operacionais, Compose, instruções, roadmap e OpenSpec; identificou 84 arquivos com ocorrências relevantes, incluindo mudanças históricas. Não foram lidos `.env`, segredos, banco local/remoto ou produção. O proprietário confirmou que só existe um fotógrafo, duas compras InfinitePay concluídas e as demais tentativas foram feitas por ele; não é necessário consultar essas tentativas.

## Remover da operação

| Área | Arquivos/contratos encontrados | Ação |
|---|---|---|
| Configuração administrativa | `frontend/app/admin/settings/infinitepay-panel.tsx`, teste e import em `settings/page.tsx`; `/admin/settings/infinitepay*` em `backend/app/main.py`; lógica `infinitepay_settings.py` | Remover card, schemas, rotas, desafios e lógica de configuração. Preservar controles PIX. |
| Emissão e retorno | `payment_provider.py`, `provider_checkout.py`, `provider_callback.py`; `/library/cart/prepare-card`, `/infinitepay/return`, `/infinitepay/webhook` | Remover criação de link e mutações financeiras iniciadas por retorno/webhook. |
| Cofre específico | `infinitepay_credentials.py`, `infinitepay_binding.py`, `rotate_infinitepay_secrets.py`; `InfinitePayCredential`, `InfinitePaySettings` em `auth.py`; purpose `change_infinitepay_otp`; `INFINITEPAY_BINDINGS_ENV_FILE` em `docker/docker-compose.yml` | Remover somente configuração/segredos InfinitePay e binding exclusivo. Preservar o cofre genérico `integration_secrets` para integrações atuais/futuras. |
| Retomada e recuperação | `provider_pending_cart.py`, `provider_cart_recovery.py`, funções/rotas de recuperação em `main.py`; ações `CartRecoveryActions` e componente `cart-recovery.tsx` | Remover retomada/reemissão e atalhos que dependem da operação InfinitePay. |
| Interface cliente | fluxos InfinitePay em `frontend/app/library/cart/page.tsx`, `checkout-navigation.ts`, `frontend/app/library/purchases/page.tsx` | Remover CTA, links e retomada. Manter a projeção de compras antigas sem ação de pagamento. |
| Configuração/CI/ops | jobs InfinitePay em `.github/workflows/ci.yml`; `scripts/provision_infinitepay_binding.py`, keyring e testes; allowlists/scripts de ingress/emergency que expõem rotas InfinitePay; `infinitepay_settings` e `infinitepay_credential` em `scripts/reset_homolog_owner.py` | Remover os fluxos exclusivos e atualizar consumidores. Manter gates genéricos de release, sem autorizar deploy/migration. |
| Documentação ativa | referências operacionais em `INSTRUCOES_EXECUTOR_CLAUDE_CODE.md` e `ROADMAP_ARQUITETURA.md`; instruções de credencial em docs ativos | Substituir InfinitePay por “cartão indisponível até integração Mercado Pago em change posterior”. Preservar artefatos antigos de OpenSpec como trilha de auditoria e marcá-los como supersedidos, sem reescrever migrations ou decisões antigas. |

## Manter para histórico e compatibilidade financeira

- `ProviderPayment`, `ProviderPaymentAttempt`, `ProviderPaymentReceipt` e `ProviderPaymentCorrection`, seus pedidos/itens relacionados e as projeções de histórico usadas por Compras, estatísticas, notificações e administração.
- A proveniência `provider = infinitepay`, NSU, valor, estado confirmado, snapshots comerciais, datas, recibos e correções; exibição com rótulo “InfinitePay (legado)” e consulta somente leitura.
- O vínculo `SaleOrder.provider_payment_id` e tabelas/constraints necessários ao histórico. Remover apenas FK/coluna `credential_id` e a coluna operacional `checkout_url` na migration aprovada; segredos/transient challenges InfinitePay podem ser apagados.
- Configuração, grupos, snapshots, confirmação manual, histórico, endpoints e UI do PIX próprio.
- `integration_secrets` e demais bindings/variáveis de Evolution, e-mail e facial.
- Migrations históricas `20261012_0075`, `20261012_0076`, `20261014_0080`, `20261020_0085` e `20261021_0086`, que compõem a cadeia instalada e não podem ser editadas/removidas.
- Changes OpenSpec antigas, fixtures e relatórios históricos necessários à auditabilidade; não são código operacional.

## Pontos que exigem validação durante a implementação

1. `main.py` consulta ProviderPayment em endpoints de compras administrativas e do cliente; separar essas leituras da criação/retomada e preservar contratos da projeção histórica.
2. `notification_delivery.py` e `statistics_report.py` usam o agregado para notificações e receita; manter leitura consistente e evitar contagem dupla.
3. `admin_account.py` e a constraint de `AdminSecurityChallenge` incluem `change_infinitepay_otp`; remover a finalidade sem afetar `change_pix_otp` ou outros desafios.
4. `scripts/check_prod_app_release_scope.py`, `prepare_emergency_api_image.py` e `render_payments0086_ingress.py` conhecem paths/URLs InfinitePay; comprovar se são consumidos por workflows ativos antes de remover ou ajustar.
5. A migration nova deve provar em banco descartável que as compras confirmadas e relações financeiras persistem, enquanto tabelas/segredos e URLs operacionais são removidos. Nenhuma migration será executada em produção nesta change.

## Resultado aplicado

- Rotas de configuração, emissão, retorno, webhook e recuperação foram removidas; o endpoint de carrinho continua servindo apenas o fluxo manual de PIX.
- Componentes exclusivos InfinitePay, cofre/binding dedicado, challenge OTP, scripts de provisionamento/rotação e seus testes foram removidos. O serviço genérico `integration_secrets` e o mount genérico continuam.
- `ProviderPayment` e suas tabelas de tentativas, recibos e correções permanecem mapeadas, mas sem credencial ou URL de checkout. As projeções administrativas e de Compras mostram o estado registrado como histórico somente leitura.
- Migration `20261022_0087` remove configurações e credenciais, a FK/coluna `credential_id`, `checkout_url` e desafios OTP InfinitePay. Sua reversão exige restauração de backup anterior.
- Os arquivos e secrets externos de uma instalação não foram lidos nem alterados. O deploy autorizado deverá remover `INFINITEPAY_BINDINGS_ENV_FILE` e o arquivo dedicado antigo do host após validar a versão; o Compose desta change já não monta essa variável.
- URLs previamente emitidas não foram consultadas nem revogadas remotamente. A aplicação não as expõe mais; a validade externa não foi verificada nesta change.
- Referências restantes de `InfinitePay` no runtime são deliberadas: provenance/status do registro histórico, rótulos somente leitura, estatísticas históricas e a constraint do modelo que assegura que `ProviderPayment` representa somente pagamentos antigos. Migrations anteriores, changes OpenSpec, gates que incluem a migration nova e seus relatos também são trilha de auditoria imutável.
