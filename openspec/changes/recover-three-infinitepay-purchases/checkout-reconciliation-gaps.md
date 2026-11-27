# Conferência sem retorno do navegador — mapa de continuidade

## Escopo e estado

Levantamento de 21/10/2026 a pedido do proprietário. A recuperação delimitada das três compras foi aplicada e validada conforme validation.md. Este mapa trata da correção geral futura; nenhuma rotina, rota, migration, worker ou comportamento público foi implementado por este documento. O PR #264 continua sendo a operação isolada. PRs #261/#262/#263 não foram modificados.

## Fronteiras comprovadas no código publicado

| Caso | Comportamento atual e lacuna | Correção necessária / limite |
|---|---|---|
| Pagamento concluído, cliente não clica em continuar | A verificação depende de GET /infinitepay/return. operational_provider não fornece webhook_url ao adaptador. | Receber aviso servidor a servidor, persistir antes de responder e verificar pela API; retorno do navegador continua alternativa. |
| Retorno chega, payment_check falha temporariamente | A rota faz a consulta na própria requisição; exceção causa rollback e redirecionamento, sem trabalho durável para repetição. Resposta unknown/unpaid não produz uma fila de consulta. | Fila persistente com tentativas limitadas, próximo horário, deduplicação e retomada após reinício; repetir apenas consulta, jamais POST /links por isso. |
| Criação do link dá timeout, HTTP de erro ou URL inválida | A tentativa durável unknown protege contra reemissão. Não há busca implementada de link por order_nsu nem evidência autoritativa de não criação. | Conservar bloqueio financeiro; registrar pendência visível, responsável e procedimento. Só recuperar automaticamente se o contrato aplicável provar ausência de checkout ativo ou pagamento em curso. |
| Cliente abandona um link válido e quer PIX | A URL aceita pode continuar pagável. paid=false informa ausência de pagamento confirmado naquele momento, não cancelamento do checkout. | Preservar retomada do link; permitir troca somente após encerramento comprovado e conferência financeira. Não usar relógio local/fechar aba como prova. |
| Aviso duplicado, fora de ordem ou durante a emissão | A aplicação financeira já tem checks e idempotência; ainda não há recepção assíncrona. A emissão atual atribui awaiting_payment após receber a URL. | Testar eventos repetidos/atrasados e concorrência entre resposta de criação e confirmação, impedindo regressão de confirmed para awaiting_payment. |
| Aviso inválido ou de outra conta | Consulta financeira confere UUID, tenant, handle, perfil, NSU, método, valor e snapshots. Não existe contrato implementado de autenticação webhook. | Aviso recebido nunca é prova financeira isolada. Definir autenticação verificável, limites de corpo/frequência, ownership e armazenamento mínimo; conferir dinheiro pela API antes de confirmar. |
| Pagamento antigo depois de recuperação excepcional | A rotina interna recusa confirmar exception; a rota pública nem consulta esse estado. | Guardar/conferir sinal tardio e destacar divergência ao fotógrafo, preservando exceção e sem liberar pedido cancelado ou alterar o novo PIX automaticamente. |
| Link oferece PIX integrado | A criação restringe credit_card e a confirmação aceita somente cartão. PIX local usa PaymentGroup e confirmação manual. | Oferecer os dois métodos no gateway exige decisão explícita sobre o domínio financeiro, a confirmação de PIX e compatibilidade com o fluxo manual; não basta habilitar uma opção. |

## Contrato oficial consultado

Fontes primárias, consultadas em 21/10/2026:

1. [Central de Ajuda — Checkout Integrado](https://ajuda.infinitepay.io/pt-BR/articles/10766888-como-usar-o-checkout-integrado-da-infinitepay): documenta X-Api-Key, objeto webhook com URL/eventos, single_payment e valid_until, além de payment_check com handle, order_nsu, transaction_nsu e slug. Lista eventos created/paid/settled/canceled/refunded/payment_failed. Não fornece nessas instruções assinatura verificável dos eventos, payload completo de cada evento ou consulta/cancelamento autoritativo somente por order_nsu. A existência de valid_until não prova, sozinha, ausência de autorização em curso ou impossibilidade de liquidação tardia.
2. [Documentação interativa](https://www.infinitepay.io/checkout-documentacao): documenta webhook_url e payload de pagamento com invoice_slug/transaction_nsu/order_nsu, com repetição após resposta de erro. O formato de configuração difere do objeto webhook da Central de Ajuda; não presumir equivalência entre perfis.

A documentação oferece mecanismos para melhorar o fluxo, mas não comprova que uma rotina local consiga encerrar automaticamente toda criação incerta. Assinatura, payload/eventos e semântica de cancelamento precisam de contrato aplicável; não inventar endpoint, header, HMAC, erro de não criação ou prazo de desbloqueio. A API Key permanece no servidor, isolada por fotógrafo; não solicitar seu valor pelo chat.

## Menor missão recomendada, até cinco etapas

1. Reconciliar o seguimento com a change add-infinitepay-credit-payments, seus gates G3/G4 e as specs do roadmap. Fixar por perfil o contrato de evento/autenticação e a verificação pela API. Submeter qualquer alteração material de confiança ao proprietário antes de código, conforme INSTRUCOES_EXECUTOR_CLAUDE_CODE.md.
2. Implementar recepção durável de sinais e consulta com repetição no worker, sem depender do retorno do browser. Nenhum dado do evento isoladamente confirma, cancela ou desbloqueia compra. Preservar credenciais por tenant e snapshots de operações antigas.
3. Implementar reconciliação visível: estados claros, próxima tentativa e pendência do fotógrafo quando faltarem identificadores/prova de encerramento. Retomar link existente; recuperar seleção/trocar meio somente com evidência suficiente ou operação excepcional separadamente autorizada. Não criar bypass público.
4. Executar testes direcionados de ausência de retorno, indisponibilidade, reinício, payload inválido, replay, concorrência, isolamento, pagamento tardio e compatibilidade de PIX/cartão. Depois executar gates pertinentes; homologação do provedor depende de autorização específica e não é substituída por mocks.
5. Preparar publicação coordenada de API/worker e, se alterada, UI, com migration aditiva apenas se necessária, inventário, backup, rollback compatível com transações e autorização de publicação. Não modificar PR #261 nem presumir merge/deploy autorizado.

Objetivo verificável: toda tentativa possui confirmação, retomada segura ou pendência operacional com procedimento explícito. **Não prometer desbloqueio automático universal sem prova do provedor.** O HTTP 422 e eventual valor mínimo de cartão continuam sem causa demonstrada; a rotina de reconciliação não deve mascarar esse problema de emissão.
