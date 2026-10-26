# Validação externa — 24/10/2026

## Retomada manual do piloto — 26/10/2026

Sessão do proprietário no Chrome, cartão oficial de teste e envio final realizado pelo próprio proprietário. Nova compra `602b1681-6bdf-4b2c-a1e1-6536729e0c29`, 15 fotos da galeria Batizado do Benjamin, R$ 105,00, preparada enquanto `70980398-54e3-4923-ba35-70519f0e34ac` permanecia em processamento (20 fotos, R$ 1,00).

Painel Developers em Teste confirmou order `ORDTST01M5WMD3CZPFBZ0J9NPXYVN8E3`, transação `PAY01M5WMD3DCPD9ZVM66MPBZSVDY`, ambas `processed/accredited`, total e pago 105.00, `live_mode:false`, referência externa exatamente igual à nova compra. Corpo de evento exibido: `order.processed`. Essa exibição não comprova, isoladamente, entrega/validação do webhook no servidor.

Carrinho inicialmente mostrava as duas como em processamento; ao abrir Acompanhar pagamento, a nova compra passou a Pagamento confirmado. Compras confirmou 15 fotos/R$ 105,00 na nova, 20 fotos/R$ 1,00 ainda em processamento na antiga e carrinho zerado. Recusa anterior `8df6f53b` e aprovação `fdb74f6f` também permaneciam no histórico. Cenário manual de nova compra independente concluído, sem confirmação forçada ou edição da tentativa antiga. Não foi inspecionado o banco nesta retomada; o mecanismo exato da atualização (consulta ou webhook) não foi atribuído sem evidência adicional.

Formulário oficial montou e aceitou dados de teste; a inspeção visual confirmou contraste inadequado em alguns campos no tema escuro. Esse defeito visual permanece pendente de correção. Não declarar encerrada toda a task visual 8.2.

### Recusa e nova tentativa com as mesmas fotos

Selecionadas BAT06972.jpg e BAT06973.jpg, total R$ 14,00. Tentativa `07bc4bbe-89a1-4fb5-b39e-a131718d7f9c` preenchida com FUND; proprietário enviou. Houve estado intermediário Verificando cartão e posterior Pagamento recusado; duas fotos retornaram ao carrinho e Tentar novamente ficou disponível.

Na retomada, a tela já apresentava nova tentativa `3c6a741b-d3df-4b35-8744-07b326b8607d`, com as mesmas duas fotos/R$ 14,00. Executor preencheu APRO e não acionou Pagar. Durante a inspeção seguinte a página já retornou Pagamento confirmado. Compras confirmou a nova tentativa e preservou a anterior como recusada, ambas com seus próprios pedidos e R$ 14,00; carrinho zerado. `70980398` permaneceu em processamento e `602b1681` confirmada.

Após o proprietário concluir a verificação de identidade exigida pelo Mercado Pago, o painel Developers em Teste confirmou as duas referências externas:

- Recusa `07bc4bbe`: order `ORDTST01M5WN1M77YB7P0XTNMK1WA9Z8` em `failed/failed`, transação `PAY01M5WN1M7QTQTPZZHJ0GA475H1` em `failed/insufficient_amount`; evento exibido `order.failed`, total 14.00 e `live_mode:false`.
- Aprovação `3c6a741b`: order `ORDTST01M5WP296F24W1XNFQB3JAQ1G8` e transação `PAY01M5WP296WQPVYEE00S87WT8ZK` em `processed/accredited`; evento exibido `order.processed`, total/pago 14.00 e `live_mode:false`.

Referências externas são exatamente os UUIDs internos acima. A lista apresentou uma order para cada tentativa nesta sequência; apenas a segunda está aprovada. A consulta é evidência independente no provedor, sem auditoria direta de banco nem prova isolada de entrega/validação da assinatura de webhook pelo backend. O corpo simulado da recusa também trouxe campos de valor pago preenchidos, apesar do estado failed; não foram interpretados como pagamento aprovado.

### Abandono preparado, redução da seleção e carrinho vazio

Na sessão autorizada do cliente, selecionadas BAT06976.jpg e BAT06977.jpg, R$ 14,00. Checkout preparado `1b67cecf`, sem preencher cartão nem clicar Pagar. Voltar ao carrinho preservou duas fotos/R$ 14,00. Remover BAT06977.jpg reduziu contador/total para uma foto/R$ 7,00; reabrir checkout mostrou nova referência `0ccbf0e7` e uma foto/R$ 7,00.

### Retomada após recarga, ampliação e consulta de tentativas antigas

Reabrir diretamente a compra confirmada `602b1681` mostrou 15 fotos/R$ 105,00 e Pagamento confirmado, sem formulário de pagamento. Recarregar o checkout da `70980398` preservou 20 fotos/R$ 1,00 em processamento, com Atualizar pagamento e sem formulário de envio. Evidência de UI; não foi disparado reenvio nem auditada a rede/banco nessa etapa.

Nova seleção somente BAT06976.jpg gerou preparação `a69694bf`, uma foto/R$ 7,00. Recarregar a página manteve exatamente essa referência e total. Voltar ao carrinho, adicionar BAT06977.jpg e preparar novamente gerou `64b88461`, duas fotos/R$ 14,00. Nenhum preenchimento de cartão ou envio foi efetuado nesta sequência. Isso conclui os três cenários manuais adicionais anunciados (recarga de preparação, adição após preparo e reabertura de tentativas antigas enviadas), sem declarar teste financeiro completo ou encerramento dos problemas visuais pendentes.

Encerrar checkout da preparação `0ccbf0e7` apresentou Checkout encerrado e informou seleção preservada. Retorno ao carrinho confirmou BAT06976.jpg/R$ 7,00. Remover a última foto mostrou Carrinho (0), vazio e sem CTA de novo pagamento. Acesso direto a `/library/checkout` retomou a tentativa já enviada `70980398`, 20 fotos/R$ 1,00 em processamento, com Atualizar pagamento e sem formulário para nova cobrança; não tratá-lo como criação de checkout vazio. Nenhum dado de cartão, geração de PIX ou envio de pagamento foi acionado nesta sequência. Escopo de evidência: comportamento de UI autenticada, sem inspeção direta de banco/API do provedor para essas preparações.

## Escopo autorizado

O proprietário forneceu arquivo fora do Git com credenciais do ambiente Teste e autorizou todos os testes possíveis em desenvolvimento, inclusive cartão oficial de teste. A credencial foi lida sem imprimir valores; `/users/me` confirmou `MLB` e `test_user`. Gate de pagamentos reais permaneceu fechado. Não houve acesso à Oracle, alteração de dados de clientes, migration operacional ou deploy.

Dados locais: PostgreSQL dedicado em loopback 55888, schema sintético `mp_external_b18f656c582741cd9b60d54f66d6649a`; API somente loopback 18117. Conta cifrada pelo cofre no schema descartável. Segredos não estão neste documento, no frontend, no Git ou nos logs de diagnóstico. A configuração do ensaio foi preparada por harness sintético; o fluxo administrativo senha/OTP tem evidência automatizada local, sem envio externo de WhatsApp neste teste.

## Resultados no provedor e no produto

| Cenário | Evidência externa | Correspondência no sistema |
|---|---|---|
| Cartão Mastercard oficial APRO, R$ 21,00 | `ORDTST01M5QZAZFWM8WF3E868H4JBSSC`, transação `PAY01M5QZAZGBMDE1ATCTT934PT2F`; POST 201 e GET com order/transação `processed/accredited`, pago 21.00 | Um submit/token oficial; confirmed, 2 pedidos/3 fotos, soma de itens/pedidos 2100, seleção consumida e um evento de confirmação |
| Refund parcial R$ 7,00 | Mesmo ID: order e transação `processed/partially_refunded`, confirmado por GET | partially_refunded, pedidos em revisão, entrega bloqueada, IDs e total original preservados |
| Refund do saldo restante | Mesmo ID: `refunded/refunded` em order/transação por GET | refunded, pedidos cancelled, histórico e filtro do painel correspondentes, sem liberação de entrega |
| Cartão FUND, R$ 21,00 | `ORDTST01M5QZGVKEW3RSG48KJH9HH45X`; criação HTTP 402, busca por referência recuperou ID e GET confirmou order failed/failed e transação failed/insufficient_amount | Resultado inicial verification_required, depois rejected; seleção restaurada, pedido cancelled, sem reenvio financeiro |
| Nova tentativa CONT após FUND | `ORDTST01M5QZKVP0YKD49MQF07NNPXDX`, `PAY01M5QZKVPH48FZ08KNBF6WC89B`; `processing/in_process` | processing; retomada com nova chave/método retorna a mesma tentativa; cancelamento 409/cannot_cancel_order mantém reserva e bloqueia nova cobrança |
| MP Pix pela tela, R$ 21,00 | `ORDTST01M5QZSRPK3WVTKBSJBNQNEEB5`, `PAY01M5QZSRQ3JBJSW9YD36RHYRWK`; action_required/waiting_transfer; QR e copia e cola presentes | pending, QR exibido e total/fotos do snapshot |
| Cancelamento MP Pix | Mesmo ID, cancelamento e GET confirmaram canceled | canceled e 3 fotos restauradas; não depende de sucesso informado pelo frontend |
| Edição depois de cancelamento | Remoção de uma foto pela API autorizada; novo preparo local R$ 14,00 | Nova tentativa/total 1400; tentativa anterior preserva 2100 e canceled; abandono preparado preserva as duas fotos sem nova cobrança |
| Resposta do submit perdida, APRO | `ORDTST01M5QZXQ0Z2GWA3QHYD3T1GGPT`, `PAY01M5QZXQ1GVYQBCRQ5FZ58QS0D`, R$ 21,00; um POST; somente a resposta ao navegador foi interrompida | Tela passou por verificação e polling recuperou confirmed sem reenvio; evidenciou contador antigo do carrinho |
| Resposta perdida após correção do contador | `ORDTST01M5R01FR0KQ8N5KRHH41DNW87`, `PAY01M5R01FRG5GXX6HRT8XATV2A7`, R$ 21,00; um POST | Verificação → confirmed por polling e navegação `Carrinho (0)` comprovada no navegador |
| Simulador oficial Pix aprovado, R$ 50,00 | `ORDTST01M5R03ACH4ETP55SSFS3PKA3F`, `PAY01M5R03AD0HPRS2CH6QNP9JWWW`; pending → processed/accredited | Um pedido sintético de 5000, confirmed por GET. Harness inclui exclusivamente em teste o campo oficial payer.first_name=APRO; código do produto não recebe simulador |
| Histórico, painel e CSV | Consultas autenticadas locais refletem estados obtidos da API externa | Filtro refunded retorna 2 pedidos; CSV padrão 4 colunas e detalhado 12, ambos com 2 linhas sob o mesmo filtro; token ausente nas respostas |
| Acesso de outra cliente | Sessão sintética distinta tenta consultar UUID de CONT | 404; dados financeiros não são expostos |

Reembolsos foram executados somente contra `ORDTST` da conta cuja identidade de teste foi verificada imediatamente antes. Não foi adicionado botão/endpoint de movimentação de reembolso ao produto. Pagamentos de teste APRO adicionais permanecem no painel para rastreabilidade; nenhuma exclusão remota foi tentada.

## Achado corrigido e regressão

Polling recuperava aprovação financeira corretamente, mas não notificava a navegação para atualizar a contagem. Corrigido em `frontend/app/library/checkout/page.tsx`; teste novo reproduziu a falha antes da alteração e passou depois. Teste externo com resposta perdida repetido e `Carrinho (0)` comprovado. TypeScript exigiu correção no mock de setInterval; verificação posterior passou.

O comportamento HTTP 402 foi incorporado em teste contratual: busca exata por referência recupera a recusa sem novo POST. `test_mercadopago_checkout.py`: 10 aprovados em PostgreSQL, 59,73s. Frontend checkout: 6 aprovados, typecheck aprovado; demais resultados locais anteriores continuam em `validation.md`.

## Webhook HTTPS — comprovado

O proprietário autorizou em 24/10 um túnel temporário Cloudflare limitado ao webhook. Binário oficial cloudflared 2026.10.3, SHA-256 verificado com o digest do release oficial: `76b2805253d0d6ffacb092a7acfbee99e7af6917835c0c5410e23f3ef5052da2`. Executável somente na pasta local ignorada; sem instalação de serviço, mudança de DNS/firewall ou alteração de recursos compartilhados.

Gateway em loopback 18118 encaminha somente POST no caminho exato da versão de conta de teste, limita corpo/tempo, não encaminha cookies e expõe nenhum outro recurso. Sondas locais e pela URL HTTPS confirmaram 404 em raiz/painel/API de clientes/GET do callback e 401 em POST sem assinatura. Cloudflare recebe apenas o tráfego desse gateway.

URL temporária desta execução:

```text
https://walking-milk-feet-eco.trycloudflare.com/api/mercadopago/webhooks/778e31fa-80b4-4a15-9b64-86d4628896c3
```

O proprietário autorizou configurar a página aberta por computer-use. Aplicação PickYourPic e seletor Teste foram conferidos; URL e checkbox Order (Mercado Pago) salvos. O Mercado Pago exigiu aprovação de identidade no aplicativo, concluída pelo proprietário. Não houve automação de autenticação. Após retornar ao formulário, URL e evento persistidos foram conferidos. Assinatura foi lida em memória sem imprimi-la, gravada no JSON de teste autorizado, ocultada novamente e carregada no cofre do schema sintético. Acesso por browser ficou disponível nessa etapa, apesar da indisponibilidade inicial.

Foram solicitados refund parcial de R$ 7,00 e refund do saldo restante da order de teste `ORDTST01M5QZXQ0Z2GWA3QHYD3T1GGPT`. Os dois eventos foram enviados pelo Mercado Pago através da URL pública; nenhuma chamada local sintetizou essas entregas. A inbox possui **dois digests distintos**, ambos `done`, `attempts=1`, `processed_at` preenchido. A primeira entrega mudou a compra de confirmed para partially_refunded; a segunda para refunded, sem consulta manual intermediária no produto e sem esperar o polling diário da tentativa final. Order/transação finais refunded, pedido cancelled, snapshot de 2100 e um único evento mp-confirmed preservados. Assinatura adulterada no mesmo endpoint foi recusada com 401; rota administrativa pública continuou 404.

Evidências locais ignoradas: `mp-webhook-real-result.json`, `mp-webhook-test-configured.png` (segredo oculto), logs sanitizados e snapshots do banco. O painel do provedor também confirmou `order.refunded`, recurso correspondente, HTTP 200, zero erros e 918 ms no resultado visível; evidência `mp-webhook-provider-200.png`. A inbox local mantém as duas entregas distintas (parcial/integral); a lista resumida do painel mostrava somente a entrega integral naquele momento, sem presumir contagem equivalente.

O túnel foi encerrado após a segunda entrega e HTTP 530 confirmou indisponibilidade externa. A nova verificação de identidade para retirada foi concluída pelo proprietário. Porém, o formulário recusou URL vazia com “Insira uma URL válida” e desabilitou Salvar ao remover o único evento. Não foi encontrado controle de exclusão/desativação no formulário, e MCP save_webhook não está disponível. As tentativas de retirada não foram persistidas; recarregar confirmou a configuração de Teste anterior. A URL encerrada permanece cadastrada somente em Teste, com Order selecionado, e deverá ser substituída antes de novo ensaio. Não inventar endpoint de exclusão, trocar por destino de terceiros nem alterar produção para contornar essa limitação.

## Fontes oficiais revalidadas

- [Teste com cartões](https://www.mercadopago.com.br/developers/pt/docs/checkout-api-orders/integration-test/cards): cartão 5480 8328 0103 3311, cenários APRO/FUND/CONT.
- [Teste com Pix](https://www.mercadopago.com.br/developers/pt/docs/checkout-api-orders/integration-test/pix): simulador APRO e consulta GET para comprovar aprovação.
- [Refund Orders](https://www.mercadopago.com.br/developers/pt/reference/online-payments/checkout-api/refund-order/post) e [gestão de reembolsos](https://www.mercadopago.com.br/developers/pt/docs/checkout-api-orders/payment-management/refunds-cancellations): SDK oficial refund, parcial com transação/valor e total com corpo vazio.
- [Tools MCP](https://www.mercadopago.com.br/developers/pt/docs/mcp-server/tools): documentação atual aceita `order_id` em quality_evaluation e exige pagamento produtivo. Corrige a limitação Orders-only descrita na skill instalada. Não executar essa medição mediante cobrança real nesta missão.
- [Cloudflare Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/) e [release oficial](https://github.com/cloudflare/cloudflared/releases/tag/2026.10.3): endereço temporário para desenvolvimento, sem garantia de disponibilidade de produção.

## Limites restantes

Chargeback, expiração real, aprovação tardia real, rotação real e condições de corrida permanecem cobertos por simulações contratuais/banco; não forçar esses eventos com operações reais ou endpoints não documentados. O cenário CONT continua processing no provedor de teste e seu cancelamento foi recusado; não marcar artificialmente como cancelado. A medição oficial produtiva de qualidade e qualquer publicação continuam fora da autorização.

Matriz local final após os achados externos: **42 testes Orders PostgreSQL aprovados**, 7 avisos, 156,18s; **84 testes frontend em 13 arquivos aprovados**, 19,01s; build e typecheck aprovados. Nenhum Access Token/segredo de webhook do arquivo do proprietário foi encontrado nos 57 arquivos modificados/novos verificados; nenhum arquivo .env foi alterado. Os servidores locais temporários foram encerrados; PostgreSQL dedicado e histórico de teste preservados para revisão, sem limpeza de recursos compartilhados.
