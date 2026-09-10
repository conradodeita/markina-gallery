# Roteiro humano de homologação

Use uma cliente de teste autenticada por OTP e duas Galerias públicas com preços configurados. Execute o roteiro em celular e desktop.

## Retomada e edição

1. Na primeira Galeria pública, selecione fotos de duas pastas e confirme `Carrinho (n)`, miniaturas e total.
2. Saia da página, feche a aba e retorne pelo mesmo link. Confirme que o carrinho reaparece completo.
3. Entre em outro navegador/dispositivo com a mesma cliente. Confirme a mesma seleção sem depender do navegador anterior.
4. Abra o carrinho, clique em `Prosseguir`, volte à galeria e adicione/remova uma foto. Prossiga novamente e confirme que o mesmo rascunho mostra itens e total atualizados.
5. Verifique que outra cliente autenticada não vê carrinho, pedido ou miniaturas da primeira.

## Congelamento e pedido complementar

1. No rascunho, confira fotos, preço e PIX e clique em `Informar pagamento` uma única vez.
2. Recarregue a página. O pedido SHALL aparecer como `Pagamento informado`, com as mesmas fotos e valor, e essas fotos não podem voltar ao carrinho.
3. Repita o clique/requisição e confirme que não surge outro pedido nem outra comunicação.
4. Selecione outra foto da mesma Galeria pública. Confirme um novo `Carrinho (1)` independente do pedido congelado.
5. Selecione uma foto da segunda Galeria pública e confirme que quantidade, preço e pedido permanecem separados.
6. O fotógrafo confirma o primeiro pagamento; a cliente recarrega e vê `Comprado` e as miniaturas correspondentes.

## Busca facial e estados

1. Faça uma busca facial já autorizada e use uma candidata para selecionar uma foto.
2. Confirme que a candidata e a mesma foto na galeria mostram `Selecionada` e o mesmo contador.
3. Após comunicar/confirmar pagamento, repita a busca e confirme respectivamente `Pagamento informado`/`Comprada`, sem nova seleção.

## Prazo e linguagem

1. Em uma galeria expirada, confirme que carrinho/pedidos continuam consultáveis e que editar ou informar pagamento é recusado.
2. Após reabertura administrativa, confirme que o carrinho volta a ser editável.
3. Na biblioteca, confirme título `Minhas fotos`, estado curto e uma ação principal por card.
4. Confirme ausência de `Sua área privada`, `Cada evento aparece uma única vez` e `compras preservadas`.
5. Em 320, 360 e 390 px e em desktop, confirme miniaturas legíveis, foco visível, ausência de rolagem horizontal e controles acionáveis.

## Aceite

A change permanece sem sincronização/arquivamento até a revisão humana. O deploy requer autorização específica posterior ao inventário desta change.
