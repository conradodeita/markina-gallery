## Context

Existem cards de navegação (`.gallery-admin-list > a`, `a.source-folder-card`) e superfícies com ações internas (`.mk-card`, `.admin-card`, `.gallery-linked-client`, cards de pasta e painel editor). Usar os seletores existentes, sem tornar toda superfície clicável. Alguns estilos legados já contêm hover; a regra nova deve preservar foco e estados.

## Decisions

- Reutilizar tokens `--mk-brand`/`--mk-border` para o destaque de borda nos temas existentes; nenhuma sombra pesada ou escala de fotografias/texto.
- Somente links de navegação elevam com `transform: translateY(-2px)`, dentro de `(hover: hover) and (pointer: fine)` e `prefers-reduced-motion: no-preference`. Duração de 180 ms; não usar `transition: all`, `will-change` permanente ou bibliotecas.
- Superfícies com formulário recebem borda sutil no hover/foco interno, mantendo posição e dimensões. Links mantêm foco explícito com outline.
- Em ponteiro coarse, resposta de borda no `:active`; nenhum estado hover persistente. Em reduced motion, remover transições novas e manter destaque estático.
- Não ampliar este ajuste para o movimento legado de botões/fotos ou redesenhar telas não relacionadas.

## Validation

Executar testes existentes de layout, lint aplicável, TypeScript e build. Conferir no Chrome desktop/celular, temas claro/escuro, hover, foco, reduced motion e estabilidade de formulário; guardar capturas fora do Git. Não adicionar testes que apenas espelhem declarações CSS.
