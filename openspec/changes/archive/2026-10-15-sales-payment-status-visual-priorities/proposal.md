# Proposal: Grupos visuais por situação financeira em Vendas e pagamentos

## Why

A página Vendas e pagamentos ainda oferece um filtro de entrega de mensagem que não participa da rotina do fotógrafo. A leitura dos cards também depende de localizar visualmente cada situação financeira em uma lista única, embora as situações já estejam disponíveis no filtro.

## What Changes

- Retirar da interface o filtro `Entrega de mensagem` e deixar de enviá-lo nas consultas do painel.
- Adicionar `Pagamento confirmado - fotos não entregue` às situações financeiras. Um pedido confirmado será classificado nessa situação quando não houver nenhum link de fotos prontas salvo no campo `Link externo do álbum`; com link nesse campo, continuará como `Pagamento confirmado`.
- Quando Situação financeira estiver em `Todas`, agrupar e ordenar os cards de clientes nesta prioridade: pagamento comunicado, pagamento confirmado, pagamento confirmado - fotos não entregue, aguardando pagamento, pagamento não localizado e prazo expirado; outros estados ficam depois desses.
- Dentro de cada grupo, ordenar clientes por chegada mais antiga primeiro. Para clientes com pedidos em mais de uma situação, o card usa a situação de maior prioridade que exista em seus pedidos no resultado. Os pedidos continuam visíveis individualmente.
- Manter `No carrinho` como grupo próprio no final, depois dos estados financeiros. Essa situação representa seleções sem pedido e não será opção do filtro financeiro.
- Aplicar uma cor de fundo/borda consistente ao card e ao rótulo correspondente no filtro: amarelo para pagamento comunicado, verde para pagamento confirmado, vermelho para confirmado sem entrega, azul para aguardando pagamento, cinza para pagamento não localizado e roxo para prazo expirado. Texto e contraste continuam identificando cada situação sem depender somente da cor.

## Non-goals

- Alterar envio, reenvio, remoção ou disponibilidade de links de entrega.
- Alterar decisões financeiras, notificações, filtros de cliente/galeria/período ou demais regras comerciais.
- Remover estados individuais dos pedidos ou o resumo de falhas de mensagens.

## Impact

- A mudança afeta o contrato administrativo de situação financeira, a ordenação/paginação de clientes e a interface da página Vendas e pagamentos.
- Não requer migration: a situação composta é derivada do estado financeiro e da presença do link de entrega persistido por pedido.
- Requer atualização da spec de operações financeiras e regressões para filtros, classificação, ordenação, cores e paginação.

## Decisões para revisão

- `Pagamento confirmado` significa pagamento confirmado com link de fotos prontas salvo no campo `Link externo do álbum`; sem link nesse campo, usa a nova situação composta.
- A situação mais prioritária dos pedidos de uma cliente define a posição do card. Dentro da prioridade, a chegada mais antiga vem primeiro.
- A lista fornecida ganha `Prazo expirado` em seguida; estados residuais, se forem introduzidos, ficam por último.
- `No carrinho` permanece separado dos estados financeiros e aparece no final da lista.
