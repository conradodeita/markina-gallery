# Mercado Pago Integration — Checkout Transparente Orders (Brasil · Python 3.6.0 · desenvolvimento)

## 1. Install

O SDK oficial `mercadopago==3.6.0` foi adicionado a `backend/requirements.txt` e instalado no venv deste worktree após autorização explícita. O frontend carrega diretamente `https://sdk.mercadopago.com/js/v2`; não adiciona biblioteca alternativa de coleta de cartão. Inventário: `docs/THIRD-PARTY-INVENTORY.md`, itens 69–70.

```powershell
# No ambiente de desenvolvimento isolado, com Python 3.12:
./backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
```

## 2. Credentials

Usar o ambiente **Teste** de uma aplicação brasileira para a validação externa. Dashboard: https://www.mercadopago.com.br/developers/panel/app. O prefixo não prova ambiente: Orders usa credenciais `APP_USR-`, inclusive em teste. O servidor verifica identidade/site e a marca `test_user` em `/users/me`; conta real continua bloqueada pelo gate operacional, que não foi habilitado.

Reconsulta oficial de 24/10: o teste básico não exige criar contas adicionais nem login de comprador; credenciais Teste e dados de cartão oficiais bastam. A página de cartões permite qualquer e-mail válido. Contas extras servem a cenários específicos de papéis/marketplace. Essa orientação atual prevalece sobre o trecho genérico antigo da skill que exigia comprador de teste para todo Orders. A criação de contas extras não foi executada.

Cada fotógrafo cadastra Public Key, Access Token e segredo de assinatura em Configurações → Meios de pagamento, com senha atual e OTP. Token/segredo são cifrados com o cofre já existente e AAD de ambiente/tenant/versão; não são retornados pela API. Não enviar segredos pelo chat nem incluí-los no Git. Nenhum `.env` foi alterado nesta execução.

O cofre exige `INTEGRATION_SECRET_ENV`, `INTEGRATION_SECRET_ACTIVE_KEY_ID` e `INTEGRATION_SECRET_KEYS`, coerentes com `APP_ENV`, fornecidos pelo servidor. Este documento não inclui valores. O cadastro não instala nem modifica essas chaves automaticamente. O Compose entrega o binding genérico somente à API e ao worker financeiro; nenhum segredo vai ao frontend ou migrate.

PIX manual e Mercado Pago têm flags independentes. A configuração de MP começa desabilitada; PIX mantém seu comportamento anterior. Uma nova versão não apaga a anterior nem muda o recebedor dos pedidos históricos.

## 3. Server code

`mercadopago_provider.py` usa o SDK oficial com transporte limitado ao host oficial, sem redirects/retries automáticos, timeout de 15 segundos e resposta de até 128 KiB. Operações implementadas:

| Operação | Contrato |
|---|---|
| Identificar recebedor | `GET /users/me` |
| Criar | `POST /v1/orders`, `type=online`, `processing_mode=automatic` |
| Consultar | `GET /v1/orders/{id}` |
| Recuperar ID perdido | `GET /v1/orders`, referência e janela de datas |
| Cancelar | `POST /v1/orders/{id}/cancel`, seguido de consulta |

Criação usa UUID persistido em `external_reference` e `X-Idempotency-Key`, total calculado no servidor e decimal textual. Uma parcela para cartão; MP Pix usa `pix`/`bank_transfer`. Não há chamada a preferences, Checkout Pro ou Payments API.

`mercadopago_checkout.py` reutiliza cotação, direitos de acesso e snapshots comerciais existentes. Persiste tentativa, pedidos/itens congelados e estado de envio antes da rede. Resposta desconhecida exige reconciliação; busca vazia não autoriza nova cobrança. O frontend não informa preço, tenant, conta recebedora ou status financeiro confiável.

| Estado interno MP | Efeito nos pedidos |
|---|---|
| prepared / abandoned | Preparação local; não representa cobrança |
| sending / verification_required | Resultado precisa de conferência; nova emissão bloqueada |
| initiated / pending / processing | Acompanha a mesma tentativa |
| confirmed | Orders e transação acreditadas, com referências/valores consistentes; permite entrega existente |
| rejected / canceled / expired | Falha terminal confirmada; restaura seleção ainda válida |
| refunded | Preserva histórico e bloqueia entrega interna |
| partially_refunded / charged_back / duplicate_review | Revisão financeira, sem liberação de fotos |

Status/detail externos de order e transação são armazenados separadamente. Eventos atrasados não rebaixam aprovação. Compra antiga aprovada confirma apenas seu snapshot; sobreposição com outro pedido congelado gera revisão, sem alterar o valor ou confirmar o pedido novo.

## 4. Client code (if applicable)

O CTA efetivo fica no carrinho e leva a `/library/checkout`. A tela mantém total e quantidade visíveis, lista de fotos, métodos, loading/erro/pendência, retorno ao carrinho e retomada por UUID próprio. Card Payment Brick coleta/tokeniza cartão; campos financeiros próprios não foram criados. CPF/e-mail de pagamento transitam sem serem persistidos neste módulo.

O componente oficial é desmontado ao sair/trocar método. Guardas de envio no navegador somam-se à idempotência e locks do servidor. Falha de rede não é apresentada como recusa definitiva e não libera reenvio.

Compras e Vendas e pagamentos apresentam provedor, método, estado comercial e financeiro. Não existe confirmação manual de MP. Os filtros novos preservam filtros de cliente/galeria/data/entrega e o histórico PIX/InfinitePay. CSV padrão conserva quatro colunas; CSV financeiro detalhado é uma opção explícita.

## 5. Webhook receiver

Configurar o tópico online **`order`**, conforme documentação específica Orders. URL pública:

```text
https://<origem-HTTPS-de-desenvolvimento>/api/mercadopago/webhooks/<UUID-da-versao-da-conta>
```

A UI apresenta a URL completa e permite copiá-la, com dicas de credenciais/assinatura e status da própria conta. A configuração retorna esse caminho com `/api`, necessário ao proxy existente. Não usar o caminho interno FastAPI diretamente na origem Next/Nginx. Registrar a URL e o segredo da mesma aplicação; a hospedagem/túnel HTTPS de desenvolvimento ainda precisa ser definida pelo proprietário.

Validação HMAC-SHA256 com `data.id` da query em minúsculas, `x-request-id` e `ts`; exige IDs query/corpo iguais e recebedor coerente. Inbox mínima durável é gravada antes do ACK. O worker consulta Orders, não confia no status do callback, usa deduplicação, lease com fencing, locks e backoff. Credenciais da nova versão podem tratar compras antigas apenas do mesmo recebedor e tenant, preservando a FK original.

Polling continua em tentativas enviadas após estados finais, para recuperar callbacks ausentes. Estados ativos voltam em dois minutos; estados finais/hold, em 24 horas. Inconsistências/falhas têm backoff. O ciclo continua passando pelas filas existentes. Tenants suspensos não são processados.

## 6. Test

Evidências locais estão em `validation.md`; o ensaio externo efetivamente executado está em `external-validation.md`, com SDK/tokenização oficiais, Orders aprovadas/recusadas/pendentes, refund parcial/integral, Pix/cancelamento e duas notificações genuínas assinadas. A matriz local de contratos continua usando dados sintéticos/fronteiras simuladas; as duas classes de evidência estão separadas.

O ensaio PostgreSQL usa somente o container dedicado `markina-gallery-mp-orders-test`, loopback `127.0.0.1:55888`, banco descartável e schemas aleatórios por teste. Não usa Oracle ou dados de clientes.

Sequência reproduzível do teste externo, usando apenas configuração segura do ambiente Teste:

1. Confirmar aplicação brasileira no ambiente Teste; não usar credenciais Produção. Criar contas adicionais somente se um cenário específico exigir.
2. Configurar credenciais no ambiente isolado e verificar `/users/me`, sem imprimir segredos.
3. Montar o Brick oficial; testar cartão aprovado (`APRO`), recusado (`FUND`) e pendente (`CONT`) com cartões oficiais brasileiros.
4. Conferir order/transação por GET e correspondência no banco, Compras e painel; mensagem do navegador não é prova financeira.
5. Testar MP Pix conforme fluxo oficial, cancelamento e atualização assinada em endpoint HTTPS.
6. Confirmar refund/parcial na conta de teste, conferindo suspensão interna de entrega; não executar operações financeiras reais.
7. Repetir revisão com as evidências externas. Não publicar automaticamente.

## 7. Docs (country-specific)

- [Integração Orders](https://www.mercadopago.com.br/developers/pt/docs/checkout-api-orders/overview)
- [Cartões e Card Payment](https://www.mercadopago.com.br/developers/pt/docs/checkout-api-orders/payment-integration/websites/cards)
- [Pix Orders](https://www.mercadopago.com.br/developers/pt/docs/checkout-api-orders/payment-integration/websites/pix)
- [Notificações Orders](https://www.mercadopago.com.br/developers/pt/docs/checkout-api-orders/notifications)
- [Compra de teste com cartões](https://www.mercadopago.com.br/developers/pt/docs/checkout-api-orders/integration-test/cards)
- [Compra de teste com Pix](https://www.mercadopago.com.br/developers/pt/docs/checkout-api-orders/integration-test/pix)
- [Contas de teste](https://www.mercadopago.com.br/developers/pt/docs/checkout-api-orders/resources/test-accounts)
- [Credenciais e seletor Teste/Produção](https://www.mercadopago.com.br/developers/pt/docs/your-integrations/credentials)
- Outras referências e divergências com instruções genéricas: `analysis.md`.

## 8. Gotchas

- A versão de credencial e o snapshot de compra são imutáveis. Editar carrinho não edita cobrança; retorno ao carrinho não cancela automaticamente uma transação.
- Aprovação tardia ou estorno pode chegar depois de outra tentativa: manter IDs antigos e processar somente prova do provedor.
- Não habilitar split/OAuth de marketplace ou recursos de outra API presumindo equivalência com Orders. Foi adotada aplicação individual por fotógrafo; não há comissão de plataforma nesta change.
- O histórico marca revisão financeira em parcial/contestação. Indicadores comerciais não são um extrato de liquidação líquido e não repartem estorno parcial por fotografia.
- Bloquear entrega interna/ocultar link não revoga um compartilhamento externo já conhecido no Google Photos/Drive. A revogação no serviço externo continua uma ação operacional do fotógrafo.
- Não há botão de estorno, parcelamento adicional, cartão salvo ou desafio 3DS próprio. Estados que exigem ação permanecem pendentes; não são aprovados pelo frontend.
- Migration 0088 é aditiva e foi ensaiada em banco descartável; downgrade recusa perda de evidência. Não aplicar em ambiente operacional sem autorização.
- Não existe certificação/homologação externa comprovada nesta etapa. A documentação MCP atual aceita order_id em quality_evaluation, mas exige pagamento produtivo; a medição não será realizada nesta missão de desenvolvimento. A indicação Orders-only incompatível da skill instalada foi superada por essa fonte oficial.

## 9. Ensaio operacional solicitado pelo proprietário

Em 24/10/2026 o proprietário escolheu validação final na instalação de produção, exclusivamente com conta de teste e seu próprio cliente. Publicação não executada/autorizada concretamente nesta preparação; plano e gates em `release-plan.md`. Fora de `APP_ENV=development|test`, conta de teste exige `MERCADOPAGO_TEST_CUSTOMERS` no servidor como lista JSON de pares `{tenant_id, client_id}` UUID. Ausência/valor inválido nega emissão; carrinho e submit aplicam a mesma restrição, sem impedir conciliação/cancelamento de tentativas enviadas. Não trocar APP_ENV para contornar o gate ou invalidar o cofre.

Compras/painel identificam TESTE pelo recebedor verificado da tentativa. Simulações não entram em receita/vendas reais nem no CSV padrão. O CSV detalhado mantém as doze colunas e identifica TESTE na descrição. Cada fotógrafo continua configurando sua aplicação individual pela UI; a política operacional não contém credenciais de recebedor.

A escolha do cliente exibe thumbnails locais Pix/Mercado Pago com texto acessível. Fontes/diretrizes dos assets estão em `frontend/public/payments/README.md`; imagens não determinam confirmação financeira.
