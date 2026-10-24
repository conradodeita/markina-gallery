# Design

## Decisão

A change remove a operação InfinitePay e seus segredos, sem apagar o histórico das compras. O intervalo até a change Mercado Pago não oferecerá checkout de cartão. O PIX manual existente continua como o meio de pagamento disponível no Pick-your-Pic.

## Limite entre código ativo e histórico

Retirar os componentes que criam, retomam ou consultam cobranças InfinitePay, a configuração de InfiniteTag/API Key, os desafios de alteração de credenciais, o card administrativo e as rotas de retorno/webhook. Remover referências e instruções de runtime exclusivas da InfinitePay. A infraestrutura genérica de `integration_secrets` e os vínculos de tenant continuam intactos, pois podem servir a outras integrações e ao Mercado Pago.

Manter `ProviderPayment`, `ProviderPaymentAttempt`, `ProviderPaymentReceipt` e `ProviderPaymentCorrection` como registros históricos somente leitura. Não reescrever identificadores, valores, snapshots comerciais, NSU, datas, confirmações ou correções. As compras concluídas continuam vinculadas aos pedidos/fotos e aparecem em Compras e no painel com a indicação InfinitePay (legado). Tentativas antigas podem ser exibidas como último estado conhecido, mas sem botão de reabertura, URL de pagamento ou afirmação de cancelamento remoto.

## Migration e segredos

Criar migration somente de avanço, sem editar migrations históricas. Apagar as tabelas exclusivas `infinitepay_settings` e `infinitepay_credential`, removendo antes as referências de configuração e a FK/coluna `credential_id` de `provider_payment`. Remover do registro financeiro a coluna operacional `checkout_url`, que não será mais usada nem exposta. Preservar tabelas e linhas de pagamentos, tentativas, recibos, correções e pedidos. Não apagar nem alterar `global_pix_settings`, `PaymentGroup` ou histórico PIX.

Não acessar nem modificar `.env`, cofre remoto, banco de produção, Oracle ou recursos compartilhados. A mudança local remove a variável e o mount InfinitePay do Compose versionado; o arquivo dedicado que já exista fora do repositório só poderá ser removido durante um procedimento de release autorizado, depois da nova versão estar ativa.

## Compatibilidade e consequência

`add-infinitepay-credit-payments` permanece como registro histórico da decisão anterior; suas tasks pendentes deixam de ser acionáveis após esta retirement. Nenhuma migration anterior será reescrita. O Mercado Pago terá change independente depois que esta estiver implementada, validada e revisada.

## Riscos e controles

- A remoção do provedor pode quebrar Compras, notificações, estatísticas ou recuperação de carrinho se esses consumidores dependerem do fluxo ativo. Mapear consumidores e manter projeções de histórico antes de remover serviços.
- A migration precisa comprovar preservação do conjunto financeiro histórico em banco descartável com dados sintéticos, incluindo pedido confirmado e seus relacionamentos.
- O sistema não invalidará links remotamente. O cliente não receberá nem poderá reabrir esses links pelo Pick-your-Pic após a retirada.
