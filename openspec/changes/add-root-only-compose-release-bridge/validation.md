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

## Em andamento

- Primeiro push: commit `ff735dfa35a3334c6208de46bf774c56f17df623`, CI `44306467902`. Frontend, backend-quality, ARM64, OpenSpec e segredos passaram no snapshot consultado; aguardar conclusão dos demais jobs antes de declarar CI verde.
- Revisão posterior acrescentou negativas para aliases inexplicados, prioridade de gateway e `NoCopy`, com pins recalculados. Os 34 testes da ponte, Ruff e política de workflow passaram novamente; regras existentes do produto/arquitetura não foram alteradas.
- Gates locais concluídos e diff revisado; nenhum arquivo de aplicação, migration, credencial ou ambiente está no delta desta change. Prossiga ao commit/push e CI com o conjunto explícito; preserve `output`.
- Não declarar instalação/deploy antes das evidências dos jobs protegidos e validação real do runtime.
- Instalar ponte e wrapper apenas pelo dispatch protegido depois da integração; o preflight real ainda pode recusar campos de runtime sem contrato comprovado. Não transformar recusa em aprovação automática.
