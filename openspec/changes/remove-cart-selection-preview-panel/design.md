## Context

Veja `proposal.md` e a delta spec. A rota privada em modo `review` já filtra a grade principal para as fotos selecionadas. O mesmo estado também força a abertura de um bloco `Revisar seleção` dentro do resumo fixo, que renderiza novamente cada item e cria a coluna escura observada na validação humana.

## Goals / Non-Goals

**Goals:**

- manter uma única representação visual das fotos selecionadas;
- preservar as ações comerciais e a edição permitida do carrinho;
- reduzir sobreposição e ocupação de viewport em desktop e mobile.

**Non-Goals:**

- alterar persistência, cotação, checkout, PIX ou comunicação de pagamento;
- remover a grade principal ou o resumo inferior antes da criação do pedido PIX;
- mudar o comportamento das listas de itens usadas em outras páginas, se houver consumidores legítimos.

## Decisions

### A grade principal é a autoridade visual da conferência

O bloco expansível de miniaturas será removido somente do resumo do carrinho. A grade filtrada da página continuará exibindo os itens e seus controles, enquanto o resumo conserva dados comerciais e CTA. Isso elimina a duplicação sem esconder as fotos.

Alternativa descartada: manter apenas a gaveta e retirar a grade. A gaveta ocupa uma área estreita, encobre conteúdo e piora ampliação, proporção e uso em celular.

### Limpeza do componente depende de inventário de consumidores

O componente de itens do carrinho será removido apenas se a busca confirmar que nenhuma outra superfície o utiliza. Estilos exclusivos também serão eliminados; estilos compartilhados permanecem.

Alternativa descartada: apagar o componente antecipadamente. Isso pode quebrar outra conferência ou histórico que reutilize a lista.

### O pedido PIX substitui o estado anterior do carrinho

Enquanto ainda não há pedido, a grade filtrada e o resumo flutuante continuam sendo a revisão necessária para avançar. Assim que `pendingOrder` existe, esses elementos deixam de ser renderizados e `Conferência do pedido` passa a ser a única etapa visível. As fotos dessa conferência usam a mesma interação protegida da galeria: ampliar, favoritar e desmarcar quando o prazo permite.

Se a cliente desmarcar uma foto nessa etapa, o pedido pendente local é invalidado e a aplicação volta ao carrinho recalculado; não se apresenta um QR Code com itens ou valor obsoletos. A comunicação de pagamento continua congelando o pedido conforme o contrato existente.

Alternativa descartada: manter a grade completa e adicionar controles às miniaturas estáticas do pedido. Isso conserva duas superfícies concorrentes e pode exibir simultaneamente totais de estados diferentes.

## Risks / Trade-offs

- [A cliente perder a ação de remover] → manter a alteração do item na grade principal e cobrir o fluxo por teste.
- [CSS órfão ou componente sem consumidor permanecer] → inventariar referências e remover somente código comprovadamente exclusivo.
- [Resumo crescer novamente em viewport estreito] → testar ausência do painel e preservar empilhamento responsivo dos controles comerciais.
- [Pedido e seleção divergirem após desmarcação] → invalidar a conferência pendente, recarregar carrinho/galeria e exigir uma nova criação do pedido antes do PIX.

## Migration Plan

1. Adicionar contrato de regressão que reproduza o carrinho em modo de revisão.
2. Remover o painel duplicado e limpar apenas dependências sem consumidores.
3. Validar que o estado final mostra somente a conferência interativa e os dados PIX, em desktop/mobile, além de lint e typecheck focados.
4. Publicar sem migration ou mutação de dados; rollback restaura somente o frontend anterior.
