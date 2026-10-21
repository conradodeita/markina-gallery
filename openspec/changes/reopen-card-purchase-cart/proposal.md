# Proposal

## Why

O fotógrafo precisa devolver ao carrinho as fotos de uma compra de cartão que não foi concluída, permitindo à cliente tentar novamente por cartão ou PIX. A recuperação pontual de três compras no PR #264 demonstrou o caminho, mas ainda não existe essa ação no card da cliente.

## What Changes

- Oferecer **Reabrir carrinho** por compra em Vendas e pagamentos, no card da cliente, com prévia das fotos/valor e confirmação explícita do fotógrafo.
- Limitar a ação a ausência de retorno ou falha inconclusiva de cartão. PIX/cartão confirmados não são elegíveis; negativas claras seguem o contrato aplicável e o fluxo existente, sem converter qualquer HTTP de erro em prova de não criação.
- Restaurar as fotos reservadas, preservando seleções novas e o histórico antigo; recalcular o carrinho pelos preços atuais e oferecer os meios já habilitados.
- Registrar a decisão manual como exceção local auditada, sem afirmar recebimento, não criação ou cancelamento remoto. O fotógrafo reconhece que a reabertura local não encerra um eventual link antigo.
- Recusar compra confirmada/NSU/recibo verificado, ownership incorreto, snapshot divergente ou seleção inelegível. Garantir transação, fingerprint, revisão e idempotência.
- Impedir que uma resposta atrasada da emissão coloque novamente em aguardando pagamento uma compra manualmente recuperada.
- Identificar a recuperação no histórico da cliente com acesso ao carrinho; a preparação local do PIX continua seleção em aberto e não deve aparecer como outra compra no painel financeiro.
- Preservar essa distinção nas listas de pedidos da galeria e no contador comercial do diretório do fotógrafo, sem alterar inventários nem a proteção de exclusão.

## Capabilities

### New Capabilities

- `gallery-sales/payment-cart-recovery`: reabertura administrativa auditável de uma compra pendente de cartão, com recuperação integral da seleção para uma nova escolha de pagamento.

### Modified Capabilities

Nenhuma spec consolidada é substituída. O delta ativo de add-infinitepay-credit-payments será reconciliado com a exceção administrativa expressamente aprovada; a recuperação automática conservadora e as decisões do PIX permanecem vigentes.

## Impact

Backend de recuperação/rotas/projeção administrativa, guarda da emissão e UI do card de cliente em Vendas e pagamentos. Reutilizar seleção/cotação/pagamentos existentes, sem migration ou nova tabela. Basear no PR #263, preservando seu filtro de pendências por fotos; não modificar a branch desse PR. PR #264 continua como recuperação operacional já executada; PRs #261/#262 permanecem independentes. Sem nova emissão, segredo, merge ou deploy remoto nesta missão. Avaliar somente duplicação/código obsoleto na área tocada.
