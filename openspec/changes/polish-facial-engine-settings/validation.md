## Validação local

- OpenSpec 1.14.0 validate polish-facial-engine-settings --strict: aprovado.
- npx tsc --noEmit: aprovado; npx eslint app/admin/settings/facial-engine-panel.tsx: aprovado, sem diagnósticos.
- npm run build: aprovado, 23 páginas, compilação 3,3 s e TypeScript 4,6 s.
- git diff --check: aprovado; revisão mostra apenas apresentação do painel, sem alteração da função PATCH, autorização ou seleção global.
- Prévia externa ao Git renderizou o próprio componente React e CSS Module, com as folhas de estilo do produto e resposta agregada sintética. Nenhuma requisição ao servidor operacional nem fotografia utilizada.
- Capturas locais: C:/codex-data/visualizations/facial-engine-settings/desktop.png e mobile.png. Fixture inicialmente Gemma, faces/filas zero.
- Viewport mobile 390 x 844: scrollWidth 375 px, botão 48,67 px; details fechado inicialmente, Enter abre e fecha, grade de indicadores em uma coluna. Override de viewport restaurado.
- Página autenticada publicada foi apenas inspecionada: usuário já havia selecionado Gemma. Esta correção não aciona o seletor.
- Não foram adicionados testes automatizados; cobertura existente do seletor permanece. CI da publicação registra os resultados atuais.

## Publicação

Pendente do fluxo PR/CI/deploy conforme deployment-plan.md. Não declarar apresentação publicada antes de confirmar o novo código no navegador.
