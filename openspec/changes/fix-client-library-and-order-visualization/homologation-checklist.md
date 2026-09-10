# Roteiro autenticado de homologação

Use uma cliente de teste autenticada por OTP que possua ao menos duas galerias e dois pedidos com estados comerciais diferentes. Execute o roteiro no desktop e no celular.

## Entrada e carregamento progressivo

1. A partir de uma Galeria pública, clique em `Minha biblioteca` e confirme feedback imediato enquanto a rota abre.
2. Em `/library`, confirme que os cards de galerias e a ação `Ver fotos` aparecem sem aguardar o término do histórico de pedidos.
3. Simule ou observe uma falha somente no histórico e confirme que as galerias permanecem utilizáveis, com `Tentar novamente` restrito à seção `Pedidos`.
4. Confirme que o botão principal possui texto visível, foco perceptível e nome acessível.

## Separação e visualização de pedidos

1. Em dois pedidos diferentes, clique em `Ver fotos` no primeiro e confirme que somente suas fotos são expandidas dentro daquele card.
2. Confirme quatro colunas de fotos em navegador desktop e duas colunas em viewport mobile.
3. Amplie uma foto individualmente e feche pelo botão, pelo fundo ou pela tecla Escape.
4. Confirme que cada pedido mantém galeria, quantidade, valor e estado próprios e que não há navegação `Anterior`/`Próxima` como modo principal de conferência.

## Galeria privada e estados comerciais

1. Abra a galeria privada e confirme que `Capa ainda não definida` não aparece; a Galeria pública e as páginas administrativas devem manter seu hero/capa normal.
2. Verifique os filtros `Todas`, `Carrinho`, `Aguardando pagamento`, `Pagamento informado` e `Compradas`.
3. Compare os contadores com as fotos efetivamente exibidas ao alternar cada filtro.
4. Em `Acompanhamento do pagamento`, confirme separação espacial, rótulo textual e diferenciação visual dos pedidos aguardando pagamento, informados, confirmados e não localizados, quando existirem.

## Responsividade e aceite

1. Em desktop, confirme ausência de áreas vazias indevidas, sobreposição e rolagem horizontal.
2. Em 320, 360 e 390 px, confirme duas colunas, miniaturas legíveis, botões acionáveis e diálogo contido na viewport.
3. Confirme que seleção, PIX, comunicação/confirmacão de pagamento, busca facial e mídia não mudaram de comportamento.
4. Registrar evidência humana e somente então autorizar sincronização/arquivamento da change.

## Gates operacionais

Push, merge e deploy exigem autorização humana específica depois deste inventário. Após a publicação autorizada, registrar SHA efetivamente implantado, healthchecks e resultado deste roteiro antes de marcar a task 4.3 como concluída.
