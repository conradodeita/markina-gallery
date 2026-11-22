# Resultados externos — Mercado Pago Orders

Data: 01/11/2026. Ambiente: aplicação local isolada, PostgreSQL 17 descartável, identidades e pacote sintéticos; conta fornecida pelo proprietário e confirmada via `/users/me` como `test_user` do site MLB. Nenhum acesso ao servidor de produção nesta execução.

## Fronteira da evidência

As chamadas create/get/cancel usaram o `OrdersProvider` real. O recebedor foi configurado pelo fluxo real `prepare_proposal`/`apply_proposal`, com os segredos cifrados em schema temporário. O formulário de ensaio usa o `cardPayment` Brick oficial com a mesma configuração do componente compartilhado; ele chama `prepare_credit_purchase` e `submit_credit_purchase` reais. O callback HTTPS encaminha somente para uma aplicação receptora mínima, que usa `receive_notification` e o worker de inbox reais.

O primeiro ensaio comprovou serviços/provedor e Brick. Em complemento, a página real `/admin/credits` e a API real da aplicação foram executadas em cópia temporária do frontend e schema sintético, com sessões administrativas sintéticas criadas por `create_session`; essa etapa está detalhada abaixo. Nenhum desses ensaios é um release. Nenhum payload pessoal, token, assinatura completa, segredo ou dado de cartão foi persistido neste relatório.

## Compras sintéticas

Pacote: 12 créditos por R$ 15,00. Comprador e recebedor são tenants distintos da aplicação. Usado e-mail sintético válido; a documentação atual de Orders não exige login de comprador separado para esse tipo de ensaio.

| Cenário | Compra local | Order Mercado Pago | Resultado autoritativo |
|---|---|---|---|
| Cartão APRO | `7b6b4cda-ce6c-43df-b748-a7d064c08797` | `ORDTST01M6CDP54T9HKZ72DN9KD1YA80` | `processed/accredited`; ledger único +12 |
| Cartão OTHE | `2156eb2c-a219-43b0-bbeb-0e9955cd879e` | `ORDTST01M6CDQZJ676KJZZFC15KX03H5` | `failed/failed`; aplicação convergiu para `rejected` após callback; sem crédito |
| Cartão CONT | `86dd6589-5438-4a25-b9a1-a7b28cbd4ed4` | `ORDTST01M6CDR8HX4FDPNFE7W43F0XWV` | `processing/in_process`; sem crédito |
| Cartão APRO pela página real autenticada, em outro schema sintético | `91476901-224e-4f6e-89fa-b93d194b5949` | `ORDTST01M6CETW5QAWDP6H935S3EDFTA` | `confirmed`; saldo da UI de 0 para 12 e histórico Compra 91476901 |

Na recusa, o create retornou erro ao adaptador e o submit inicialmente registrou `verification_required/unknown_creation`; o callback real localizou a Order e convergiu para `rejected`. Esse comportamento preservou a tentativa sem emitir outra cobrança.

O GET da Order aprovada não trouxe `live_mode`; a identidade `test_user`, o recebedor correspondente e os dados públicos de cartão de teste são a evidência de uso de teste. A ausência do campo não foi tratada como prova isolada de modo de execução.

## Matriz de callbacks

| ID | Exercício | Origem | Evidência | Resultado |
|---|---|---|---|---|
| CB01 | Aprovação | Provedor real | Inbox processada, GET autoritativo, estado confirmado | Confirmado |
| CB02 | Recusa após resposta create desconhecida | Provedor real | Compra saiu de verification_required para rejected | Confirmado |
| CB03 | Pendência | Provedor/API real | GET processing; ledger sem crédito dessa compra | Confirmado |
| CB04 | Callback com manifest raw ID | Replay gerado no ensaio, assinado com segredo de teste | HTTP 200; worker consulta Order real | Confirmado |
| CB05 | Mesmo request-id/body/signature repetido | Replay gerado | HTTP 200; uma única entrada para a mesma identidade; sem segundo crédito | Confirmado |
| CB06 | Outro request-id da mesma Order | Replay gerado | HTTP 200; inbox processa; ledger continua único | Confirmado |
| CB07 | Formato legado ID minúsculo no manifest | Replay gerado | HTTP 200 com HMAC específico válido | Confirmado |
| CB08 | Assinatura inválida | Requisição negativa gerada | HTTP 401 | Confirmado |
| CB09 | Assinatura ausente | Requisição negativa gerada | HTTP 401 | Confirmado |
| CB10 | user_id de outro vendedor | Requisição negativa gerada | HTTP 401 | Confirmado |
| CB11 | Caminho com account_id diferente | Requisição negativa gerada | HTTP 401 | Confirmado |
| CB12 | data.id do body diferente da query | Requisição negativa gerada | HTTP 401 | Confirmado |
| CB13 | Payload assinado alega chargeback para Order ainda aprovada | Replay gerado; estado financeiro real preservado | HTTP 200; GET retorna aprovação; sem hold nem alteração do ledger | Confirmado |
| CB14 | Reembolso parcial R$ 5,00 | API de reembolso real de teste + callback do provedor | HTTP 201; GET partially_refunded; revisão pending | Confirmado |
| CB15 | Replay do mesmo reembolso após liberação pelo proprietário | Replay gerado + GET real | HTTP 200; revisão permanece released | Confirmado |
| CB16 | Reembolso do restante após liberação | API real de teste + callback do provedor | HTTP 201; GET refunded; revisão reabre como pending | Confirmado |
| CB17 | Aviso de aprovação atrasado após reembolso total, repetido | Replay gerado + GET real | HTTP 200; compra permanece refunded/pending, sem novo crédito | Confirmado |
| CB18 | Reconciliação manual de compra confirmada/inativa | Serviço real + GET externo | Estado financeiro preservado após consulta; ledger único | Confirmado com limite abaixo |

CB18 foi executado com o provider real carregado do arquivo seguro e conferido contra conta/seller do registro; a fábrica de credencial do processo auxiliar retornou esse provider diretamente, pois as chaves efêmeras de cifra pertencem ao processo do receptor. O submit e o worker exercitaram o caminho de decifragem real. O cenário externo de reembolso com callback totalmente perdido não foi forçado; sua transição por reconciliação manual tem cobertura sintética PostgreSQL.

## Bloqueio e revisão no ensaio

- Depois do reembolso parcial real, `prepare_credit_purchase` recusou nova compra e `reserve_photo_credit` retornou HTTP 409. Não houve débito automático.
- O comprador não conseguiu liberar a revisão; a identidade PlatformOwner sintética registrou restrict e depois release, com justificativas e eventos append-only. A liberação removeu o hold quando não havia outra revisão.
- O replay da mesma Order parcialmente reembolsada não reabriu a revisão; o novo reembolso total abriu nova revisão.
- Depois dos callbacks, replays, reembolsos e consulta manual, havia **1 movimento no ledger, total +12**, 10 notificações da inbox em `done`, 1 evento `confirmed`, 1 `partially_refunded`, 1 `refunded` e 2 `owner_reviewed`. As tabelas `MercadoPagoPayment`, `SaleOrder` e `SaleOrderItem` permaneceram vazias no schema do ensaio.

## Limites de simulação aceitos pelo proprietário

- PIX não apareceu nos métodos retornados pela conta fornecida. Não foi habilitado outro meio, ignorado o gate de disponibilidade ou fabricada aprovação. Teste externo PIX permanece indisponível nessa conta.
- Não foi encontrado endpoint oficial para forçar chargeback de Order online de teste. Payload assinado com action chargeback foi exercitado, mas isso não muda o recurso financeiro; chargeback autoritativo e múltiplos holds têm cobertura sintética local, não confirmação externa.
- A Order CONT permaneceu processing. Tentativa de cancelamento de teste retornou HTTP 409 e o GET continuou processing. Não foram realizadas tentativas repetidas nem alteração artificial do recurso.
- Aprovação tardia após pendência e callback completamente perdido não foram forçados no provedor; não são substituídos pelos replays gerados. Há testes locais específicos para esses contratos.
- Em 02/11/2026, o proprietário aceitou esses limites de simulação. A cobertura sintética dos estados permanece como evidência para PIX indisponível, chargeback autoritativo, aprovação tardia e callback perdido. A task 4.2 foi concluída com esse aceite; nenhum desses resultados autoriza deploy ou migration produtiva.

## Página real e consulta do proprietário

- Uma cópia temporária dos fontes do frontend (sem arquivos de ambiente) rodou com o mesmo Next.js instalado, porta `127.0.0.1:18084`; a API real rodou em `127.0.0.1:18083`, com banco isolado, integrações de mensagens em sandbox e hooks de startup desabilitados apenas no harness. O servidor Next preexistente em 3002 foi preservado.
- As sessões de fotógrafo e proprietário foram sintéticas, usando `create_session` real e cookie exclusivo HttpOnly `pyp_mp_ui_session`. Isso exercita autorização da página/API; não comprova o login com senha/TOTP nem envio real de OTP.
- Pelo botão Comprar pacote da página real, o comprador preencheu o Brick de teste. O submit real retornou HTTP 200/confirmed; sem recarregar a página manualmente, a carteira mudou de 0 para 12 e o histórico mostrou pacote, R$ 15,00, status, data e Compra 91476901, além do movimento +12 com UUID completo.
- Em viewport 390×844, a página recarregada preservou saldo/histórico e não apresentou transbordamento horizontal. Capturas locais: `C:\codex-data\temp\pyp-mp-external-20261101\photographer-approved-desktop.png` e `photographer-approved-mobile.png`.
- Na sessão do proprietário, a pesquisa parcial por e-mail selecionou o tenant comprador e mostrou saldo 12 e o mesmo movimento, com referência `91476901-224e-4f6e-89fa-b93d194b5949`. Captura: `C:\codex-data\temp\pyp-mp-external-20261101\owner-buyer-ledger-desktop.png`.
- A inspeção encontrou e removeu o texto obsoleto do painel de pacotes que dizia que a compra não estava habilitada. Também corrigiu a mensagem de busca vazia exibida depois de selecionar uma sugestão válida. Os 17 testes dos componentes passaram, assim como ESLint/TypeScript; o build Next.js em cópia temporária dos fontes revisados passou. As capturas foram renovadas após a correção.

## Referências oficiais

- [Dados de cartões e resultados APRO/OTHE/CONT](https://www.mercadopago.com.br/developers/pt/docs/checkout-api-orders/integration-test/cards)
- [Contas de teste específicas de Orders](https://www.mercadopago.com.br/developers/pt/docs/checkout-api-orders/resources/test-accounts)
- [Assinatura e tópicos opcionais](https://www.mercadopago.com.br/developers/pt/docs/checkout-api-orders/optional-notifications)
- [Validação do SDK: preservar valores brutos](https://github.com/mercadopago/sdk-nodejs/blob/master/docs/webhooks.md)
- [Reembolso de Order](https://www.mercadopago.com.br/developers/pt/reference/online-payments/checkout-api/refund-order/post)
