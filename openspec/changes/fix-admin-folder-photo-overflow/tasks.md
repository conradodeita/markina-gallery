# Tasks

## 1. Reprodução e correção

- [x] 1.1 Reproduzir na página administrativa real com fixtures sintéticas de duas pastas, nomes extensos e medidas de overflow; registrar evidência antes da correção. Em 320, 360 e 390 px o documento e o conteúdo dos dois cards de nome longo ultrapassam seus limites; em 390 px a imagem vizinha interceptou o clique de ampliação. Capturas no diretório temporário `pick-your-pic-folder-photo-before`.
- [x] 1.2 Corrigir somente CSS da grade afetada; verificar em navegador imagens/textos/controles contidos, troca de pasta, seleção e ampliação em celular/desktop e temas. Dez combinações 320/360/390/768/1440 × claro/escuro passaram, com zero overflow e zero mutações; captura inspecionada em 390 px. Ver validation.md.

## 2. Integração

- [x] 2.1 Executar testes do editor, lint/typecheck e build frontend, validação OpenSpec e revisão do diff; registrar evidências e limitações, preservando alterações preexistentes. 52 testes passaram, lint sem erros (28 avisos preexistentes), TypeScript/build aprovados, OpenSpec estrito e diff --check aprovados; ver validation.md.
