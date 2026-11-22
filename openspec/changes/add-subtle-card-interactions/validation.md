# Validação local — 11/11/2026

## Implementação e escopo

Adicionado bloco focal ao final de `frontend/app/globals.css`, reutilizando seletores e tokens existentes. Links da listagem de galerias e `a.source-folder-card` elevam 2 px em 180 ms somente com mouse preciso e sem preferência de movimento reduzido. Cards administrativos de edição mantêm posição/dimensões e destacam borda; foco explícito nos links e resposta `:active` em ponteiro coarse. Nenhum pacote, JavaScript, alteração de dados ou consulta extra foi introduzido.

O pedido explícito “ótimo! Implemente” aprovou a implementação local do padrão já apresentado; proposta/design/delta/tasks foram registrados antes do código. Não foi necessário novo gate de aprovação para repetir essa mesma autorização. Não houve publicação, commit, push ou alteração produtiva. Specs principais e arquivamento aguardam revisão humana.

## Verificações

- `npx vitest run app/layout-system.test.ts --maxWorkers=1 --reporter=dot`: 15 aprovados, 13,74 s.
- `npx tsc --noEmit`: aprovado.
- `npm run build`: aprovado, Next 16.4.2, compilação e 27 páginas geradas.
- CSS não possui linter configurado no projeto; sintaxe foi processada pela build e conferida no navegador. `npx eslint app/layout-system.test.ts`: aprovado, sem avisos/erros.
- `git diff --check` focal e OpenSpec estrito aprovados; fechamento das tasks conferido na sequência.

## Chrome

Conta e galeria exclusivamente sintéticas já existentes, em `127.0.0.1:3039`. Conferidos temas claro e escuro e viewport desktop 1440×1000 e celular 390×844. Conteúdo de 1425 e 375 px respectivamente, sem overflow horizontal. Preferência original Claro/Neutro, viewport e emulações foram restaurados; aba deixada na listagem de galerias.

Para verificação determinística do CSS, usado DevTools Protocol `CSS.forcePseudoState` nos estados hover/focus-visible/active e `Emulation.setEmulatedMedia`/touch. Uma tentativa de mover o ponteiro via CDP não ativou hover; não é contabilizada como prova de movimento real do mouse. As provas seguintes verificaram o estado CSS forçado e não hardware de toque real:

- Hover sem redução: transformação calculada `matrix(1, 0, 0, 1, 0, -2)` e duração `0.18s`.
- Reduced motion: transformação `none`; duração efetiva `0.00001s` por regra global de acessibilidade já existente, suprimindo a nova transição. Nenhum movimento residual de 2 px.
- Foco: outline sólido calculado de 2 px, sem depender apenas de cor.
- Touch emulado: `(pointer: coarse)` verdadeiro, `(hover: hover)` falso, transformação `none`, borda usando a cor de marca no active.
- Card com formulário: antes/depois de hover/focus-within, mesma posição (350,07 / 1249,11 px), largura (275,26 px), altura (652,19 px), transformação `none`; somente borda mudou. Nenhum formulário foi salvo ou dado alterado.

Capturas externas ao Git: `C:/codex-data/test-runs/card-interactions-20261111/hover-light.jpg`, `hover-dark.jpg`, `touch-mobile.jpg` e `stable-form.jpg`. A captura isolada não demonstra duração de animação; essa medida vem do estilo calculado. A captura nativa do formulário não enquadrou os campos e não é prova visual da geometria; as medidas DOM acima são a evidência da estabilidade.

## Refatoração proporcional

Reutilizados os seletores e tokens existentes, sem introduzir componente paralelo nem mudar cliques, autenticação, disponibilidade ou regras de galeria. Não removidos efeitos legados de botões/fotos: extrapolariam o ajuste aprovado. Nenhuma oportunidade adicional de remoção segura foi identificada no escopo.
