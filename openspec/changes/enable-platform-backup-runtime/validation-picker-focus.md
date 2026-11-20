# Validação — seleção e revalidação de foco do console

Data: 20/11/2026

## Sintoma e fronteiras

Após a publicação de #395 (`ebfed532`), o proprietário confirmou que senha/TOTP e abertura funcionam, mas o clique em `Selecionar` fecha o Picker e a página não apresenta candidata/erro. O acesso automatizado ao browser continua indisponível neste chat; nenhum callback real foi capturado. Não atribuir o resultado a erro do Google sem evidência.

O código revela uma fronteira reproduzível: `window.focus` dispara `useConsoleAccess.refresh`, que antes definia `access=null` e incrementava a chave `revision`. O shell desmontava `ConsoleContent` e o seletor; o callback externo continuava ligado à instância descartada. O teste integrado da página real com a fronteira Google simulada reproduziu a perda de `PICKED` antes e durante uma consulta positiva de capabilities. Os dois casos falharam antes da correção. Outros três casos falharam porque a desmontagem em recusa/falha/logout não ocultava o diálogo externo.

O texto `Backup, arquivo e restauração: sem fonte integrada; estado desconhecido.` é fixo em `page.tsx`; ele não lê a candidata e não comprova autorização, vínculo protegido ou saúde do backup. O clique em `Selecionar` deve primeiro apresentar a candidata; `/picker/authorize` exige novo step-up explícito. Não transformar seleção em prova de backup.

## Correção delimitada

- Separar acesso confirmado de revalidação pendente; manter capabilities a cada foco, com descarte de respostas antigas por geração e abort.
- Conservar o console montado, `hidden` e `inert`, durante a revalidação. Retomar a instância somente com acesso positivo. Recusa, erro HTTP/rede ou logout desmontam o conteúdo e descartam seu estado.
- Ocultar o diálogo e invalidar a geração do Picker ao desmontar; resposta tardia da sessão, biblioteca ou callback antigo não abre nem restaura o seletor.
- Preservar `drive.file`, validação da pasta no backend, senha e TOTP novo para autorizar; nenhuma persistência em storage nem logs do token/pasta/credenciais.
- Atualizar os pins exatos do seletor, página, hook de acesso e link do console; o gate aceita nominalmente os dois helpers diretamente afetados e recusa mudanças futuras sem pin revisado. Nenhum wildcard foi ampliado.

## Evidências e gates pendentes

- Controle anterior: `page.test.tsx` executou 12 testes, 7 passaram e 5 falharam nos cenários acima.
- Após a correção, os 8 arquivos de testes de `app/admin/platform` passaram: 38 testes, incluindo seleção antes/durante revalidação positiva, erro sanitizado preservado, recusa, HTTP 503, logout, callback/resposta tardios e sessão que chega depois do unmount.
- ESLint focado passou; o lint completo em cópia isolada terminou com 0 erros e 38 warnings preexistentes. `npx tsc --noEmit` passou. Build Next 16.4.2 passou em `C:/codex-data/validation/picker-focus-20261120/frontend`, com os arquivos versionados atuais e dependências próprias de `npm ci`, sem junction nem tipos gerados antigos. OpenSpec estrito das duas changes afetadas, Ruff e `git diff --check` passaram.
- O primeiro build completou compilação, TypeScript e geração de páginas, mas saiu 1 com alerta de segurança da versão instalada do Next.js. A repetição do mesmo comando, sem flags de bypass ou alteração de dependências, terminou 0 e manteve o aviso. Consulta read-only `npm audit --omit=dev --json` confirmou advisories moderados para Next 16.4.2 e correção disponível (faixa afetada informada: 16.0.0–16.4.4); nenhuma atualização foi aplicada no escopo desta correção.
- `test_prod_app_release_scope.py` passou com 29 testes (342,555 s no Windows, `GIT_CONFIG_COUNT=0` somente nesse processo), incluindo recusa dos dois helpers alterados sem pin revisado e aceitação com pins exatos. A política integrada recusou inicialmente o manifesto não commitado; após o commit `44cde916`, passou: `publication_candidate_ready=true / somente_api_web`. O verificador do candidato contra a base publicada `ebfed532` retornou `app_release_ready=true / somente_api_web`.
- Task 3.2i validada localmente com revisão de diff e pins exatos. CI ainda pendente; tasks 3.2h/3.2 continuam dependentes de publicação aprovada e seleção real. A aprovação de #395 não autoriza automaticamente merge/deploy deste novo SHA.
- Manutenção proporcional: a chave `revision` por foco foi substituída pelo estado de revalidação. Os únicos consumidores do hook são shell e link do console; ambos foram reconciliados. Nenhuma limpeza independente ou alteração de backend era necessária.

Nenhuma operação de produção, pasta do Drive, vínculo root-only, backup real ou timer foi alterada nesta correção.
