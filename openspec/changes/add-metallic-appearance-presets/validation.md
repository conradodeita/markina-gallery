# Validação — 2026-10-06

## Implementação local

- `frontend/app/theme.ts` e `theme-control.tsx`: modo claro/escuro/sistema e acabamento independente, com leitura no bootstrap antes da pintura, persistência local, fallback Neutro, suporte a armazenamento bloqueado e sincronização entre abas.
- `frontend/app/appearance.css`: tokens de superfície, texto principal/secundário, marca e foco para Neutro, Cinza metálico, Azul metálico e Vinho metálico em claro e escuro. Fotografias, logos, favicons e QR Codes não recebem filtros ou regras de tema.
- `frontend/app/theme-control.test.tsx`: cobre seleção, persistência, fallback, indisponibilidade de armazenamento e sincronização entre abas.

## Evidência de qualidade

- Teste focal `npm test -- --run app/theme-control.test.tsx`: 1 arquivo e 7 testes aprovados.
- Suíte `npm test`: 47 arquivos e 354 testes aprovados. A saída incluiu um aviso do ambiente de teste (`Not implemented: navigation to another Document`), sem falha.
- Typecheck `npm exec tsc -- --noEmit`: aprovado.
- Lint `npm run lint`: 0 erros e 25 avisos preexistentes em arquivos fora desta implementação.
- Build `npm run build`: compilação, TypeScript e geração de 22 páginas aprovados.
- OpenSpec `npx --yes @fission-ai/openspec validate add-metallic-appearance-presets --strict --no-interactive`: change válida. Uma primeira validação apontou requisito longo; ele foi dividido em requisitos menores e a validação final passou.
- Cálculo de contraste entre tokens de texto principal/secundário e as paradas de superfície: oito combinações de acabamento/modo; os mínimos foram 7,75:1 e 4,70:1. O limite do texto normal é 4,5:1.
- Inspeção visual no navegador local em desktop: acabamento neutro, cinza, azul e vinho no modo claro; vinho no modo escuro. Os fundos metálicos e textos coordenados ficaram visíveis e legíveis.

## Limitação

A inspeção visual foi concluída em desktop, mas não em larguras móveis. A primeira tentativa em `127.0.0.1:3000` falhou com `EACCES` porque essa porta já servia outro aplicativo; o serviço existente foi preservado. A verificação desktop foi concluída depois em `127.0.0.1:3101`. A interface de automação disponível não oferece controle de viewport móvel, então a tarefa 2.2 permanece aberta até essa inspeção.
