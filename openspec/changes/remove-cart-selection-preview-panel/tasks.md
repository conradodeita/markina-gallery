## 1. Contrato do carrinho

- [x] 1.1 Ajustar o teste da galeria privada em modo de revisão para exigir as fotos selecionadas somente na grade principal, ausência de `Revisar seleção`/lista duplicada e presença de quantidade, total, faixas e CTA no resumo. Evidência: o contrato reproduziu a duplicação no código anterior e passou após a remoção; 21 testes da rota aprovados.
- [x] 1.2 Cobrir que o diálogo de proteção autoral continua sendo apresentado independentemente do painel removido e verificar o contrato no teste direcionado da rota. Evidência: o teste aciona a proteção pela prévia da grade e confirma o diálogo autoral sem a lista do carrinho.
- [x] 1.3 Cobrir que, após a criação do pedido PIX, a grade anterior, filtros, atalho e resumo flutuante desaparecem; `Conferência do pedido` permanece como única revisão e permite ampliar, favoritar e desmarcar antes do PIX. Evidência: regressão falhou no comportamento anterior e passou após a correção, cobrindo ausência das quatro superfícies, ampliação, favorito, desmarcação e PIX.

## 2. Simplificação visual

- [x] 2.1 Remover do resumo flutuante a renderização duplicada dos itens e confirmar no teste que seleção, ampliação, desmarcação permitida e checkout continuam acessíveis pela superfície principal. Evidência: `Revisar seleção` saiu do resumo; grade, `✓ Desmarcar`, proteção, faixas e `Continuar para o PIX` permaneceram cobertos.
- [x] 2.2 Inventariar consumidores do componente e estilos da lista do carrinho; remover somente código órfão e verificar por busca que nenhum import ou seletor quebrado permaneceu. Evidência: busca confirmou que `ClientCartItems` e `.client-cart-items` eram exclusivos do painel; componente, tipo, import, função duplicada e CSS foram removidos sem referências restantes.
- [x] 2.3 Fazer o estado `pendingOrder` substituir a composição anterior do carrinho, reutilizar a apresentação protegida na conferência e invalidar pedido/PIX obsoletos quando a seleção for alterada. Evidência: `activePendingOrder` seleciona composição exclusiva, `GalleryPresentation` protege e amplia a conferência; favorito preserva o pedido e desmarcação retorna ao carrinho sem restaurar o rascunho naquele fluxo.

## 3. Validação e entrega

- [x] 3.1 Executar teste frontend direcionado da galeria, ESLint dos arquivos alterados, typecheck e OpenSpec estrito; revisar o diff para confirmar ausência de mudança em API, pagamentos ou proteção autoral. Evidência: 21 testes passaram; ESLint focado, `tsc --noEmit`, OpenSpec estrito e `git diff --check` aprovaram; nenhuma API ou regra comercial foi alterada.
- [x] 3.2 Executar regressão direcionada da etapa PIX revisada, ESLint e typecheck, confirmando que preços, comunicação de pagamento e proteção permanecem intactos. Evidência: 21 testes da galeria aprovados; ESLint sem erros, typecheck e build aprovados; QR Code, copia e cola, total, proteção e comunicação de pagamento continuam cobertos.
- [ ] 3.3 Validar a composição em viewport desktop e mobile sem duplicações; preparar inventário de impacto zero e executar o push, merge e deploy em homologação já autorizados pelo usuário.
