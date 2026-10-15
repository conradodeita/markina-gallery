# Design

## Contexto

O painel `/admin/payments` consulta `/admin/payment-communications`, cuja projeção financeira atualmente deriva estados de pedidos/comunicações. Cada cliente tem um card com pedidos individuais. O campo visual `Link externo do álbum` está representado como `delivery_album_url`. O backend aplica filtros antes de agrupar os pedidos e retorna clientes em páginas. Seleções sem pedido são retornadas separadamente como `selections_without_order` e hoje aparecem antes dos cards financeiros.

## Decisões

1. **Situação composta por pedido.** Derivar `confirmed_undelivered` somente quando `payment_status == confirmed` e o campo `Link externo do álbum` (`delivery_album_url`) não contém nenhum link de fotos prontas salvo. Um pedido confirmado com link nesse campo mantém `confirmed`. Não persistir a situação nem criar migration. A decisão financeira continua independente da entrega.
2. **Prioridade do card de cliente.** Usar a maior prioridade existente entre os pedidos visíveis daquele cliente, na sequência comunicada, confirmado, confirmado sem entrega, aguardando pagamento, não localizado, prazo expirado e residual. Ordenar clientes dentro da situação por chegada mais antiga, baseada no `created_at` do pedido que determinou a situação, com UUID como desempate estável. Ordenar pedidos individuais por chegada e manter todas as ações por pedido.
3. **Filtro e paginação.** O filtro `financial_status` aceita a nova situação. A classificação, filtro, facetas, contagens e ordem agrupada são calculados pelo backend antes da paginação, para que páginas consecutivas não dividam ou reordenem clientes de forma inconsistente. O controle `Entrega de mensagem` e seu parâmetro de consulta da página são retirados; os campos técnicos restantes de entrega e o resumo de mensagens permanecem se ainda forem usados para exibição/contagem.
4. **Seleções sem pedido.** Mostrar `No carrinho` em grupo próprio depois dos pedidos financeiros, sem incluí-lo nas opções do filtro financeiro. Uma seleção sem pedido continua nesse grupo. No fluxo unificado atual, abrir `/library/cart` com seleção válida chama `POST /library/cart/prepare`, que cria pedidos em rascunho e prepara o PIX; pedido pendente sem comunicação e não expirado aparece como `Aguardando pagamento`. `Informar pagamento` cria a comunicação e passa a situação para `Pagamento comunicado`.
5. **Cores acessíveis.** Centralizar rótulo, prioridade e tokens de cor por situação no frontend. O card recebe cor suave e borda/badge da situação primária; as opções do filtro usam a mesma cor. `No carrinho` usa tratamento teal neutro e texto próprio. Manter foco legível e contraste adequado em tema claro/escuro. Cor nunca será o único indicador. Usar o componente de seleção existente, salvo limitação demonstrada de estilo de opções; se necessário, criar uma seleção acessível que mantenha teclado e leitor de tela.
6. **Histórico e critérios auxiliares.** A nova situação não altera a disponibilidade para a cliente, o histórico do pedido ou os controles de ação financeira/entrega. Critérios de cliente, galeria e período continuam combináveis. O filtro de entrega de mensagem deixa de ser usado pela interface, sem remover telemetria, estados de notificação ou contratos que tenham outros consumidores.

## Validação

- Cobrir a derivação confirmada com o campo `Link externo do álbum` vazio ou preenchido, inclusive após correção de pagamento.
- Cobrir prioridade de clientes com múltiplos pedidos e desempate FIFO estável, filtros e paginação.
- Cobrir remoção do controle/parâmetro de entrega de mensagem e a renderização textual e cromática acessível das opções e dos cards.
- Executar testes focados do painel/API, validações frontend e OpenSpec conforme aplicável.
