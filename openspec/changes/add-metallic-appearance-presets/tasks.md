## 1. Preferência e seletor

- [x] 1.1 Estender o seletor compartilhado para oferecer Neutro, Cinza metálico, Azul metálico e Vinho metálico em administração e área do cliente. Evidência: `ThemeControl` no layout raiz compartilhado exibe as opções nos dois contextos; `theme-control.test.tsx` cobre seleção.
- [x] 1.2 Persistir o acabamento separadamente da preferência Claro/Escuro/Sistema, com fallback Neutro e comportamento funcional quando armazenamento local falhar. Evidência: chaves independentes, bootstrap antes da pintura, sincronização entre abas e testes de armazenamento inválido/indisponível em `theme-control.test.tsx`.
- [x] 1.3 Consolidar modo e acabamento em um único seletor “Aparência” com rótulos de presets combinados; remover o seletor “Acabamento” separado e cobrir combinação, persistência, fallback e sincronização nos testes. Evidência: 12 presets testados em `theme-control.test.tsx`; preferência persistida e sincronizada nas duas chaves legadas; `npm test -- --run app/theme-control.test.tsx` passou (7/7).

## 2. Tokens e acessibilidade

- [x] 2.1 Implementar tokens coordenados de superfície, texto principal/secundário e realce para os acabamentos aprovados nos modos claro e escuro, preservando as mídias sem filtros ou alterações. Evidência: tokens de superfície/texto em `appearance.css`; nenhuma regra de filtro ou cor aplicada a imagens, logos, favicons ou QR Codes.
- [ ] 2.2 Verificar contraste de texto e indicadores, foco, responsividade e aparência em todas as combinações de acabamento e modo; registrar evidências.
  - Contraste calculado para texto principal/secundário sobre cada parada de superfície em 8 combinações acabamento/modo: mínimo observado 7,75:1 e 4,70:1, respectivamente. Inspeção visual em desktop concluída; a interface de automação não oferece controle de viewport móvel, então a checagem responsiva permanece pendente. A primeira tentativa em `127.0.0.1:3000` retornou `EACCES`; o aplicativo existente foi preservado e a inspeção desktop foi concluída em `127.0.0.1:3101`.

## 3. Validação e documentação

- [x] 3.1 Executar testes focados, lint, typecheck, build e validação OpenSpec aplicáveis; registrar resultados e atualizar documentação relevante. Evidências e limitação visual em `validation.md`.
- [x] 3.2 Revisar o diff e reconciliar tarefas com evidências antes de solicitar revisão humana para sincronização/arquivamento. Evidência: revisão dos quatro arquivos de frontend e artefatos desta change; alterações locais preexistentes em outros arquivos foram preservadas. Validação OpenSpec estrita passou.
