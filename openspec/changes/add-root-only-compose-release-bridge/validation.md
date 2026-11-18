# Evidências e continuidade

## Autorizações e alvo

- 18/11/2026: proprietário escolheu ponte root-only restrita e autorizou explicitamente prova semântica por serviço para API/web sem `config-hash`.
- Autorização da conversa cobre commit/push, correções de CI, PR/merge e deploy protegido. Preservar gates, dados reais e flag facial `true`; não alterar secrets, `.env`, banco, migrations, workers ou serviços vizinhos.
- Worktree: `C:\codex-data\worktrees\saas-release-candidate\Photo Delivery`; branch `fix/root-only-compose-release-bridge`. O caminho preexistente `output` está fora do escopo.

## Diagnóstico read-only do host

SSH sem sudo confirmou host `clearbudget-vnic`, checkout `bfe511f850224823254b0fc9f51fa7ff60ecfba0`, API/web saudáveis e imagens por IDs imutáveis. Cada serviço usa snapshots diferentes, web tem diretório histórico em `deploy-state`, ambos sem label `config-hash`. O recibo `web-current.identity` é anterior à imagem ativa. Nenhuma fonte protegida foi aberta e nenhuma alteração remota foi executada durante este diagnóstico.

## Gates locais

| Gate | Evidência | Resultado |
| --- | --- | --- |
| Contratos da ponte | `python -m unittest discover -s scripts -p test_production_app_compose_bridge.py` | 34 testes: 33 passaram e 1 symlink real indisponível no Windows; guarda de symlink também passou por fixture independente |
| Fronteiras cobertas | rejeição de argumentos antes do Docker, non-root, paths/symlinks/hard links/metadados, duplicatas de ambiente, segredo sentinela, fontes por serviço, defaults/imagem, deriva de ambiente/rede/mount/segurança, checksum/cópia adulterada, release/rollback só API/web, arquivo Git limitado e pin do helper | Passou com dados sintéticos, sem Docker real/SSH |
| Regressões de release | cinco `ReleaseContracts`: inventário sem escrita, app→web, flag facial falsa antes do build, web→app→rollback, falha de build/saúde com recuperação | 5 passaram em 388,813 s; fronteiras Docker/Git/HTTP simuladas |
| Ruff da ponte e scripts de coordenação | `python -m ruff check` nos arquivos da ponte, teste, estado, política de workflow e web | Passou |
| Ruff do teste de escopo | `python -m ruff check --select F,E9 scripts/test_prod_app_release_scope.py` | Passou; dois FURB192 preexistentes em linhas não alteradas ficam fora do gate CI desse arquivo |
| Política web existente | `python scripts/test_deploy_prod_web_policy.py` | Passou com identidade semântica app e contrato web-only preservado |
| Sintaxe | Git Bash `-n` no executor app e instalador | Passou |
| OpenSpec | `openspec validate add-root-only-compose-release-bridge --strict` | Passou após separar o requisito semântico |
| Shell final com pins atualizados | Git Bash `scripts/test_deploy_prod_app_services.sh` | 6 testes passaram em 222,466 s; política shell passou |
| Escopo | `python scripts/test_prod_app_release_scope.py` | 23 passaram em 231,954 s |
| Classificador | `python scripts/test_classify_prod_release.py` | 16 passaram em 4,447 s |
| Workflow protegido | `python scripts/test_production_release_workflow_policy.py` | Passou; candidato API/web elegível, dispatch protegido e pins exatos |
| Segredos | Gitleaks 8.24.3 `stdin --redact` sobre `git diff --cached` do conjunto explícito de 20 arquivos | Nenhum segredo encontrado em 164.521 bytes; artefato preexistente `output` excluído |

## Push e CI da branch

- O primeiro commit enviado foi `ff735dfa35a3334c6208de46bf774c56f17df623`. A revisão adicionou recusas para aliases de rede inexplicados, prioridade de gateway e opção `NoCopy` de volume, recalculou os pins e foi publicada no commit `94662062f7f2dffd9df78714c305035e7dbbbdf7` (`fix(ops): prove network and volume options before release`).
- O CI do commit inicial (`44306467902`) foi cancelado depois que o commit corrigido iniciou uma validação integral sobreposta; ele foi substituído pelo run mais novo, não por uma falha.
- O run [44307098266](https://github.com/conradodeita/markina-gallery/actions/runs/44307098266), no SHA `94662062f7f2dffd9df78714c305035e7dbbbdf7`, terminou com sucesso em 18/11/2026. Passaram `gitleaks`, `openspec`, classificação de escopo, frontend, qualidade e três partições do backend, gate agregado do backend, imagens AMD64/ARM64, inventário de homologação e todos os demais jobs aplicáveis; o contexto `gemma-runtime` legado também ficou verde.
- O workflow foi disparado com `operation=none`. Instalação protegida, preflight e release/deploy foram pulados; nenhum container ou serviço de produção foi alterado por essa rodada.
- Escopo/segredos e diff foram revisados antes dos commits. Nenhum arquivo de aplicação, migration, credencial ou ambiente entrou no delta; o caminho preexistente `output` permaneceu fora do escopo.
- Task 4.1 concluída com gates locais e CI integral verde neste SHA. A próxima etapa é abrir o PR, acompanhar os checks de PR e integrar somente quando os seis contextos exigidos pela proteção estrita de `main` passarem.
- Instalar a ponte e o wrapper apenas pelo dispatch protegido depois da integração. O preflight real ainda pode recusar campos de runtime sem contrato comprovado; uma recusa não deve ser convertida em aprovação automática.
- CI pós-merge `44316971108` no SHA integrado `cf63a0d7e3cc0b6cd0c81af813bdca972c62aaff`: qualidade, frontend, imagens, backend (três shards e agregado), OpenSpec, escopo, inventário e Gitleaks passaram. O job read-only `production-app-preflight` recusou com `production-preflight: script diverge do blob revisado`; não houve build nem alteração de produção.
- Dispatch protegido de instalação `44317813361`, no mesmo SHA, passou todos os gates e recebeu a aprovação do ambiente já autorizada. O instalador parou em `origin_invalid`, antes de `sudo`, lock, escrita ou consulta Docker. A URL remota sanitizada do checkout é `ssh://github.com/conradodeita/markina-gallery.git`; o instalador atual aceitava somente HTTPS. Nenhum container, fonte, recibo ou configuração Git foi modificado.
- A correção delimitada aceita exatamente as duas URLs canônicas do repositório (HTTPS e SSH), sem reescrever `origin`; host, caminho, protocolo ou credenciais diferentes continuam bloqueados. O checkout remoto permanece em `bfe511f850224823254b0fc9f51fa7ff60ecfba0`, limpo; `origin/main` por SSH confirma `cf63a0d7e3cc0b6cd0c81af813bdca972c62aaff`. O teste do allowlist passou para as duas formas aceitas e seis formas inválidas; os 35 testes da ponte, Ruff, sintaxe Bash e OpenSpec estrito passaram localmente. Novo CI/PR e retry protegido pendentes; task 2.4 concluída, tasks 4.2/5.1 continuam abertas.
