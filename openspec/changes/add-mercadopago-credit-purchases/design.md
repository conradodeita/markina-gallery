# Design: Compra de créditos via Mercado Pago

## Estado

Implementação local em validação, dependente dos contratos da carteira de créditos. A migration aditiva, o checkout Orders, a reconciliação e a revisão financeira foram acrescentados ao repositório. Nenhuma migration foi aplicada em homologação ou produção, nenhuma Order real foi criada e o gate de credenciais/contas de teste do Mercado Pago continua aberto.

## Fronteiras observadas

- Compra de fotografia: comprador cliente; recebedor fotógrafo tenant; Orders, pagamentos, configuração e confirmação pertencem ao tenant vendedor.
- Compra de créditos: comprador fotógrafo tenant; recebedor conta Mercado Pago configurada pelo proprietário no tenant associado à identidade global `PlatformOwner`. A identidade compradora e a conta recebedora são vínculos distintos e resolvidos pelo servidor.
- O webhook atual valida assinatura e conta, cuja propriedade continua tenant-bound. A confirmação de crédito deve mapear a Order autenticada para um registro próprio de compra de créditos, sem alterar o significado dos pagamentos ou pedidos de fotos.
- O checkout visível atual é transparente e ocorre dentro da plataforma; o servidor cria a Order via `OrdersProvider`. Não há redirecionamento para checkout hospedado externo.

## Desenho implementado

1. Resolver no servidor a conta ativa de Payment Providers no tenant vinculado ao `PlatformOwner`. O tenant comprador vem da sessão; o browser não fornece nem escolhe tenant, conta ou credencial recebedora.
2. Reutilizar `OrdersProvider`, a configuração existente e o cofre de segredos tenant-bound do proprietário. Não criar uma conta ou credencial global paralela nem consultar a conta do fotógrafo comprador.
3. Acrescentar entidade `CreditPurchase` imutável com tenant comprador, pacote/preço congelados e referência à conta recebedora do proprietário; ligar a um evento de crédito por chave idempotente. Não criar `MercadoPagoPayment`, `SaleOrder` nem `SaleOrderItem` para uma compra de créditos.
4. Manter a validação de assinatura e a consulta autoritativa da Order. O processamento separa eventos de compra de crédito dos pagamentos de fotografia; replay e callbacks fora de ordem não duplicam saldo.
5. Mercado Pago é o único provedor padrão para créditos quando a configuração do proprietário está ativa. O PIX interno do sistema não participa, sem alterar a configuração PIX ou os meios de pagamento das vendas de fotos. Meios nativos do Mercado Pago permanecem do próprio checkout Mercado Pago.
6. Manter pendência/rejeição sem saldo disponível. Aprovação confirmada gera exatamente um evento no ledger. Reembolso total/parcial ou chargeback confirmado abre revisão, bloqueia uploads e compras do tenant e gera evento próprio, sem apagar compra ou lançar débito automático pelos créditos consumidos.

## Registros e roteamento para o tenant comprador

A inspeção do código confirmou que o transporte Orders não depende do tenant comprador, mas o ciclo comercial atual de fotografia depende. O desenho aditivo fica assim:

1. `CreditPurchase` registra ID da compra, tenant comprador da sessão, fotógrafo admin iniciador, `PlatformOwner` autorizado, tenant recebedor, ID da conta Mercado Pago do recebedor, pacote e snapshot imutável de nome/quantidade/preço/moeda, chave de idempotência, `external_reference`, IDs da Order/pagamento, estado e marcos temporais. A chave de Order é única por conta recebedora e a chave de tentativa é única por tenant comprador. Uma edição posterior do pacote não reescreve a compra.
2. A conta recebedora é resolvida em servidor: localizar a identidade `PlatformOwner`, exigir exatamente um vínculo `TenantAdmin` ativo e um tenant ativo — a mesma regra fail-closed já usada pelo backfill da carteira em `20261031_0094` —, carregar `PaymentPreferences.account_id` desse tenant e validar a conta com `account_for(account_id, tenant_id)`. Zero ou mais de um vínculo, conta ausente, conta desativada ou credencial indisponível encerra a tentativa sem aceitar tenant/account do browser.
3. A tentativa durável é criada antes da chamada de rede. `OrdersProvider.create` recebe credencial decifrada da conta proprietária, payload de checkout validado pelo servidor e `external_reference` igual ao ID persistente da compra. O payer é o fotógrafo autenticado; pacote, valor, recebedor e quantidade nunca vêm como autoridade do browser. Repetição usa a mesma chave persistida; resposta desconhecida reconcilia pela Order/referência antes de criar outra cobrança.
4. `MercadoPagoWebhook` continua como inbox assinada da conta/tenant recebedor. O worker consulta a Order com a credencial dessa conta e roteia a referência validada para `CreditPurchase` somente quando comprador/recebedor, conta e seller ID correspondem. Se não for compra de créditos, a trilha atual `MercadoPagoPayment` continua inalterada. Referência desconhecida, Order de outra conta ou divergência de seller não credita saldo.
5. Um histórico aditivo `CreditPurchaseEvent` registra tipo/estado da transição, tenant comprador, compra, timestamp e chave idempotente, sem payload sensível integral. Uma entrada `PhotographerCreditEntry` do tipo `purchase` referencia a compra e o pacote, sob unicidade por tenant/compra e a chave idempotente já suportada pelo ledger. Na transação da confirmação autoritativa, esse único movimento positivo é criado para o tenant comprador; nenhum saldo fica disponível antes do commit dessa confirmação. Histórico de carteira expõe a compra pelo ledger já existente.
6. Estados financeiros de reembolso/chargeback ficam registrados em `CreditPurchase`/`CreditPurchaseEvent`. Cada compra contestada mantém um estado de revisão próprio. Uma revisão pendente ou restrita bloqueia o tenant inteiro, inclusive quando existe saldo de outras origens. A reserva do upload, `prepare` e `submit` consultam o bloqueio no servidor. Somente `PlatformOwner` pode registrar `released` (liberar) ou `restricted` (manter bloqueado), com justificativa, ator e horário; outro evento contestado mantém o tenant bloqueado. O ledger não recebe débito automático dos créditos consumidos.

O inbox do provedor é roteamento de webhook, não uma notificação de saída ao fotógrafo. A atualização/histórico dentro da carteira é o retorno de produto especificado até aqui; canal externo de notificação não foi pedido nem desenhado nesta change.

A reconciliação manual de compras já confirmadas continua consultando a Order mesmo quando `active=false`, permitindo descobrir reembolso/chargeback sem callback. O worker periódico continua selecionando apenas compras ativas; não há polling contínuo novo para compras pagas. Compras preparadas, abandonadas e terminais nunca pagas não geram consulta externa desnecessária.

Na validação do callback, o manifest HMAC preserva `data.id` bruto conforme o SDK oficial 3.6.0. Para preservar o contrato legado já aceito pelo fluxo de fotografias, a variante com ID em minúsculas continua aceita somente quando o HMAC dessa variante também coincide com a assinatura usando o segredo da conta. Ambas continuam sujeitas aos mesmos gates de conta, tipo, Order, identidade e comparação constante; isso não autoriza callback sem assinatura válida.

## Contrato HTTP e checkout do fotógrafo

- As rotas de compra ficam sob `/admin/credits/purchases` e exigem sessão administrativa ativa, origem same-origin nas mutações e carteira `finite`. O tenant comprador é sempre o `tenant_id` da sessão validada; o proprietário com carteira `unmetered` não recebe checkout.
- `GET /admin/credits/purchases` lista as compras recentes do tenant autenticado, inclusive estados pendentes e financeiros, sem dados do cartão ou CPF. `GET /admin/credits/purchases/active` lista somente tentativas ainda conciliáveis para retomada após recarga da página.
- `POST /admin/credits/purchases/prepare` aceita somente `package_id` e `idempotency_key`. A API valida pacote ativo, preço/moeda BRL, carteira em modo `finite` e conta recebedora do proprietário; congela pacote/quantidade/preço e grava a compra antes de qualquer chamada financeira. A repetição da mesma chave e pacote retorna a compra existente; usar a mesma chave para outro pacote é conflito.
- `POST /admin/credits/purchases/{purchase_id}/submit` recebe método Mercado Pago (`credit_card` ou `pix`), tokenização de cartão quando aplicável e dados do pagador requeridos pelo checkout. O método é congelado no primeiro envio. A referência da compra e o valor vêm do snapshot no servidor. O token de cartão e os dados CPF/e-mail do pagador não são persistidos; o checkout segue os campos já usados pela integração fotográfica.
- `GET /admin/credits/purchases/{purchase_id}` retorna estado somente para a compra pertencente ao tenant autenticado. `POST /admin/credits/purchases/{purchase_id}/reconcile` consulta a Order pela conta recebedora persistida, sem emitir nova cobrança, e tem limite por administrador/IP antes de qualquer consulta ao provedor. A confirmação atualiza a compra, evento de auditoria e ledger atomicamente; retorno de browser nunca é confirmação.
- O fotógrafo escolhe cartão ou PIX nativo do Mercado Pago dentro do Checkout Transparente; o PIX interno do sistema não aparece como opção. O checkout reutiliza o Brick/tokenização de cartão existente. Estado de pagamento, preço e quantidade são sempre mostrados a partir da API.

## Condições de ativação operacional

- A validação externa com credenciais e conta de teste foi concluída em 01/11/2026. O proprietário aceitou em 02/11/2026 os limites de simulação registrados em `external-validation-results.md`: PIX não estava disponível nessa conta; chargeback autoritativo e alguns estados tardios foram cobertos por testes sintéticos. Isso não equivale a validação ou autorização de pagamentos reais.
- O checkout exige um pacote de créditos ativo e usa o preço congelado fornecido pela carteira; a aplicação não cria pacote ou preço padrão. Essa configuração é necessária para oferecer compras em um ambiente, mas não é uma validação de implementação ainda pendente.
- Esta change não configura credenciais de produção nem autoriza pagamento real, migration remota ou deploy.

## Validação esperada

- Testes sintéticos de assinatura inválida, pagamento pendente/recusado/confirmado, webhook duplicado e fora de ordem, replay, consulta autoritativa, aprovação tardia, reembolso/chargeback e créditos idempotentes.
- Testes PostgreSQL de isolamento com tenant comprador distinto do tenant da conta recebedora do proprietário; verificar que as credenciais do comprador não são consultadas e que a compra nunca aparece como venda de fotos.
- Verificar que PIX interno não aparece no checkout de créditos e que o checkout de fotos preserva os meios já configurados para seu tenant.
- Verificar que uma revisão financeira bloqueia no servidor uploads e compras; só `PlatformOwner` pode liberar/manter o bloqueio; outra revisão não é desbloqueada por uma resolução isolada; nenhum débito automático chega ao ledger.
- A validação externa registrada usa credenciais e conta de teste no host compartilhado da API do Mercado Pago; não há host separado de sandbox para Orders. A separação depende das credenciais/contas e nenhum teste deve recorrer a credenciais reais como fallback.

## Preservação nas rotinas de homologação

`MercadoPagoCreditPurchase` e `MercadoPagoCreditPurchaseEvent`, o ledger, as operações de upload, seus eventos e alocações são evidências financeiras/operacionais imutáveis. A limpeza de conteúdo deve classificar todas essas tabelas como preservadas e contá-las sem expor detalhes. O reset integral deve preservar o catálogo global de pacotes e a carteira do tenant proprietário, adquirir bloqueios nas tabelas de histórico e recusar antes de mutação se existir qualquer entrada, operação, evento, alocação ou compra, inclusive reserva pendente ou compra preparada/abandonada. A carteira de tenants removidos só pode ser eliminada quando não houver histórico referenciando esses tenants. A política impede apagar tentativas, uploads cobrados, callbacks ou histórico que exijam reconciliação humana.
