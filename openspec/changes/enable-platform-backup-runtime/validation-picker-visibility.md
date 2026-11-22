# Visibilidade do seletor no console — 20/11/2026

## Causa comprovada

A sessão autenticada do proprietário em `/admin/platform` mostrava autorização Drive registrada, mas não o seletor global. O endpoint `/api/admin/platform/console/sources` usa `scope=platform_owner` para indicar o escopo operacional da fonte; o frontend comparava esse valor com a URI OAuth `drive.file`. A comparação nunca era verdadeira no contrato real.

A correção compara o campo operacional com `platform_owner`. A disponibilidade continua exigindo `authorization_recorded`; o console continua verificando capacidade do proprietário. O endpoint de sessão e o componente Picker preservam a validação independente de OAuth `drive.file`, senha e TOTP. Não foi ampliado escopo, emitido token ou escolhido destino por esta correção.

## Evidência local

- A fixture existente já representava o endpoint real. Atualizar sua expectativa para exigir o seletor reproduziu uma falha antes da correção; os outros seis testes passaram.
- Após a correção, console e componente Picker passaram juntos: 9 testes. O contrato exige formulário visível, botão desativado sem reautenticação e nenhuma chamada automática a `/picker/`; mantém os testes de recusa de escopo OAuth ampliado.
- ESLint dos arquivos alterados e TypeScript passaram. `npm run build` com dependências próprias instaladas pelo lockfile concluiu com código 0, incluindo compilação, TypeScript e geração das páginas.
- O ensaio inicial com `node_modules` compartilhado por junction falhou na resolução de pacotes/fontes. Somente a junction criada para esta task foi removida; `npm ci --no-audit --no-fund` instalou o lockfile no worktree isolado, sem alterar dependências ou lockfile. A build padrão passou depois dessa preparação.
- O Next instalado emitiu aviso de vulnerabilidade e encerrou a primeira build local com esse aviso após compilar; a repetição padrão concluiu com código 0 e preservou o aviso. Não houve atualização de dependências nesta task.
- O pin do único arquivo de runtime alterado foi atualizado. O teste do console é admitido nominalmente no gate de escopo e coberto pela fixture de aceitação; não há wildcard novo. O teste focado do gate, Ruff, OpenSpec estrito e diff check passaram.

## Operação

Nenhum recurso de produção foi alterado pela correção visual. O mount da API e a instalação da ponte seguem a task 3.2c. A publicação do frontend exige revisão/merge, CI e aprovação operacional pelo canal existente. Seleção do destino pelo proprietário, vínculo desativado e ensaio sintético continuam pendentes em 3.2. Backup real e timer permanecem no gate separado 3.3.

A revisão de refatoração ficou na comparação incorreta e na cobertura existente; nenhuma remoção ou reorganização adicional foi necessária.
