## 1. Contrato do carrinho

- [ ] 1.1 Ajustar o teste da galeria privada em modo de revisão para exigir as fotos selecionadas somente na grade principal, ausência de `Revisar seleção`/lista duplicada e presença de quantidade, total, faixas e CTA no resumo.
- [ ] 1.2 Cobrir que o diálogo de proteção autoral continua sendo apresentado independentemente do painel removido e verificar o contrato no teste direcionado da rota.

## 2. Simplificação visual

- [ ] 2.1 Remover do resumo flutuante a renderização duplicada dos itens e confirmar no teste que seleção, ampliação, desmarcação permitida e checkout continuam acessíveis pela superfície principal.
- [ ] 2.2 Inventariar consumidores do componente e estilos da lista do carrinho; remover somente código órfão e verificar por busca que nenhum import ou seletor quebrado permaneceu.

## 3. Validação e entrega

- [ ] 3.1 Executar teste frontend direcionado da galeria, ESLint dos arquivos alterados, typecheck e OpenSpec estrito; revisar o diff para confirmar ausência de mudança em API, pagamentos ou proteção autoral.
- [ ] 3.2 Validar a composição em viewport desktop e mobile sem painel encobrindo as fotos; preparar inventário de impacto zero e solicitar autorização humana específica antes de push, merge ou deploy em homologação.
