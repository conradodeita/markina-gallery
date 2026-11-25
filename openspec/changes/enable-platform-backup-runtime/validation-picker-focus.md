# Validação — seleção e revalidação de foco do console

> **EVIDÊNCIA HISTÓRICA — NÃO RETOMAR.** O Picker foi retirado em 25/11/2026; estes resultados não autorizam provisionar chave, pasta ou runtime.

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
- Task 3.2i validada localmente com revisão de diff e pins exatos. A seleção e a segunda autorização reais após #397 foram confirmadas pelo proprietário; 3.2h está concluída. O vínculo root-only e o ensaio sintético da task 3.2 continuam pendentes.
- A CI inicial da PR #397 (`44784725438`, SHA `95fb38ea`) passou OpenSpec e escopo, mas Gitleaks classificou o pin Git de `use-console-access.ts` como `generic-api-key` no commit `44cde916`, manifesto linha 38. `git rev-parse HEAD:frontend/app/admin/platform/use-console-access.ts` confirmou o valor exato do blob, `e9d73d435d764a33858c2c0698de513927b2d1eb`. Registrado somente o fingerprint desse commit/path/regra/linha em `.gitleaksignore`, conforme padrão existente, sem ampliar regex/paths ou desabilitar varredura. Repetir CI no head corrigido.

## Integração e autorização de publicação

- CI `44785023938` concluiu success no SHA revisado `883c6da734a245feac34c852c75bb72219ab5b4b`: frontend (lint/Vitest/build), backend-quality, quatro shards, agregado backend, imagens AMD64/ARM64, OpenSpec, Gitleaks e políticas integradas passaram.
- O proprietário autorizou integrar e publicar #397 após CI verde e preflight consistente com a base saudável `ebfed532`. Escopo autorizado: API/web, possível breve interrupção; preparação da referência Git pelo canal protegido. Sem migration, backup real, ativação de timer ou alteração de segredo.
- PR #397 integrada por merge commit em `77cf2788e3d9be4e2628bcdd9d508dc59916847e`, preservando o histórico dos fingerprints pontuais. Árvore do merge e da revisão coincidem em `85f1d62bde2cace9bc025fa2f79335048fe36553`; primeiro pai é a base aprovada `ebfed532`.
- CI da main `44788742378` iniciou. O job `production-app-preflight` (`136470719284`) passou no escopo e recusou a referência local `origin/main` ainda desatualizada com `SHA não é a main local aprovada; preparação necessária`, antes de inventário completo ou publicação. Aguardar todos os gates de código; instalar o suporte/referência pelo workflow protegido, comprovar containers inalterados e repetir somente os jobs falhos/dependentes do mesmo SHA.
- Durante a CI, o proprietário reconsiderou a hipótese de manter somente a cópia mais recente e confirmou seguir o plano vigente de retenção 7 diários / 4 semanais / 3 mensais. A confirmação mantém a política existente; não autoriza expurgo nem primeira cópia real/timer, que continuam com gates próprios.
- A tentativa 1 de `44788742378` concluiu com todos os gates de código aprovados e apenas a falha isolada no preflight. O verificador versionado `verify_main_ci_evidence.py --app-bridge-install` aceitou esse estado para a preparação. O workflow protegido `44792334858` concluiu success: ponte de blob `e52d3b791471fdbff568ea89b09ee343f7ffbe16`, `root:root:755`, backup preservado em `/var/backups/markina-gallery/app-compose-bridge-20261120T182437Z-77cf2788e3d9`; wrapper anterior preservado em `/var/backups/markina-gallery/preflight-ssh-wrapper-20261120T182439Z-preview-migration-77cf2788e3d9`. A ref avançou de `ebfed532` para `77cf2788`; `containers_unchanged=true`.
- Disparada somente a repetição dos jobs falhos/dependentes de `44788742378`, preservando os gates verdes do mesmo SHA. Aguardar preflight/handoff consistentes com o runtime `ebfed532` antes de aprovar o release protegido.
- A tentativa 2 passou no preflight `136484129469`: checkout `ebfed532`, API `sha256:6542cb04aa28b065f072430a2530deeb60005c42522a643d03b15b9d1de7302f` e web `sha256:ed4ed1329b3843bb1b1f63de958bf9d68db20e28f1b513ac460c30c9d7d64eb3`, com os mesmos IDs de container observados após #395, saudáveis. Schema `20261113_0126`, `APP_ENV=production`, processamento facial ativo, Nginx `127.0.0.1:8080`, HTTPS 200. Fingerprint `961734a68b330b9eff72dc7f3defe651936da3fdf8c330fa1d6d8297096352a9`; imagem-base API exportada pela chave read-only. A condição de base consistente foi atendida.

## Publicação concluída — 20/11/2026 às 15h30 BRT

- CI da main `44788742378`, tentativa 2, concluiu success após repetir somente os jobs falhos/dependentes. Os gates de código aprovados do mesmo SHA foram preservados.
- Artifact ARM64 `136484602178` passou: bundle SHA-256 `17c07f404cdd9756244e9fd5bff25bd089807b88609a72fd001b720f5b9cfc25`, sobre a imagem-base API `sha256:6542cb04aa28b065f072430a2530deeb60005c42522a643d03b15b9d1de7302f`. Handoff `136485779668` confirmou checkout `ebfed532` e fingerprint `9a287500c132ed7d6b1a21de8756199a1c708a9422c64be88ff92cfb3ce48632`.
- O histórico de revisão do GitHub registra aprovação do ambiente `production` por `conradodeita`. O job protegido `production-app-release` (`136486015235`) concluiu success com `release saudável: 77cf2788...; serviços=api,web; anteriores preservados`.
- Imagens candidatas/live conferem: API `sha256:02b991244d46fa868ae830a7e83c000c0c36bb249d2f568b7d8b70db72fb63d4`, web `sha256:e203bc5d67a33fddae2e96abe838aae9e12dbf39f14c43303ae73c76159bda60`, ambas healthy. O recibo confirma checkout `77cf2788`, `APP_ENV=production`, processamento facial ativo, Nginx `127.0.0.1:8080` recarregado e versões/imagens anteriores preservadas.
- Após a publicação, consultas HTTPS independentes a `/healthz`, `/api/health` e `/` responderam 200. A publicação não executou migration, backup real ou ação sobre o timer.
- A seleção autenticada real ainda depende do reteste do proprietário. Manter 3.2h/3.2 abertas até confirmar a candidata e completar sua autorização/vínculo/ensaio; não declarar o backup recorrente ativo.

## Continuidade solicitada pelo proprietário

Reteste autenticado após #397: o proprietário confirmou que `Pasta selecionada` e `Autorizar esta pasta` apareceram. Após a segunda reautenticação, confirmou `Pasta autorizada: Pick-your-Pic Global. O vínculo protegido e o ensaio sintético ainda precisam ser concluídos com a rotina desativada.` Isso comprova o fluxo visual e a autorização OAuth da pasta. A task 3.2h está concluída; vínculo root-only e ensaio sintético permanecem pendentes em 3.2. O helper de vínculo aceita somente auditoria dos últimos 15 minutos; revalidar esse prazo ao executar, sem ampliar a janela por conveniência.

## Lacuna do executor operacional

Registro em 20/11/2026:

- Inspeção dos arquivos versionados encontrou o código da CLI `backend/app/platform_backup/production_cli.py`, as unidades systemd e o lock em `scripts/backup_runtime/`, mas não encontrou instalador do runtime nem workflow protegido para instalá-lo/executar o vínculo. A CLI expõe `--bind-selected-destination`, porém não há operação de ensaio sintético do Drive.
- O inventário read-only `44796009869` confirmou `APP_ENV=production`, API e web saudáveis, Nginx restrito a `127.0.0.1:8080` e o mount do Picker já presente. Terminou com `picker_mount_already_present` ao tentar preparar novamente um plano de mount; não emitiu fingerprint e não alterou o servidor. Esse diagnóstico não verifica o runtime de backup, `source.json`, destino ou unidades systemd; o estado desses itens continua não verificado após o inventário anterior.
- Antes de escrever em `/etc/pyp-backup` ou na pasta global do Drive, definir e revisar em OpenSpec um canal root-only de instalação/vínculo/ensaio com inventário e fingerprint, mantendo o destino desativado. Não usar SSH ou comandos ad hoc. Nenhum backup real, timer ou acesso a dados de tenant foi executado.

O [guia de reuso para arquivo/recuperação de mídia](../../../docs/saas-evolution/backup-global-reuso-arquivo-midia.md) reúne provas externas concluídas, componentes de Drive reutilizáveis, núcleo de mídia já implementado, lições operacionais e sequência para conectar o adaptador real. Foram conferidas 32 referências locais, todas existentes. O guia fica ligado ao índice SaaS e ao checklist pós-deploy; não inicia a implementação da etapa de mídia nem substitui seus gates.
- Manutenção proporcional: a chave `revision` por foco foi substituída pelo estado de revalidação. Os únicos consumidores do hook são shell e link do console; ambos foram reconciliados. Nenhuma limpeza independente ou alteração de backend era necessária.

O escopo operacional deste recibo foi a preparação protegida e a publicação de API/web. Pasta do Drive, vínculo root-only do backup e timer permaneceram sem operações nesta correção; nenhum backup real foi iniciado.
