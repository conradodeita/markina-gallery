# Validação local do runtime protegido de backup

**Data:** 20/11/2026
**Ambiente:** Windows, worktree `codex/record-picker-focus-release`
**Escopo:** artefato ARM64, inventário/fingerprint, instalador inerte, vínculo e ensaio sintético, canal protegido e allowlist do release API/web.

## Evidências locais

| Verificação | Resultado |
|---|---|
| `backend/tests/test_platform_backup_workspace_store.py` e `backend/tests/test_platform_backup_production_cli.py` | 26 passaram, 1 skip |
| Testes do artefato de runtime | 4 passaram |
| Testes do inventário | 5 passaram, 1 skip |
| Testes do instalador | 1 passou, 4 skips |
| Testes do workflow protegido | passou |
| `scripts/test_prod_app_release_scope.py` | 30 passaram |
| Ruff nos arquivos Python afetados | passou |
| `compileall` nos módulos Python afetados | passou |
| Parse YAML de `ci.yml` e dos dois workflows de backup | passou |
| `bash -n` do builder, instalador do wrapper e forced-command wrapper | passou |
| `openspec validate enable-platform-backup-runtime --strict` | passou |
| `git diff --check` | passou |

O teste de escopo usa repositórios Git temporários. Seu fixture remove os overrides externos `GIT_CONFIG_*` para que a configuração injetada pelo ambiente desktop não altere a interpretação do Git; a suíte completa passou após esse isolamento.

## CI remoto do candidato

A [CI `44845952777`](https://github.com/conradodeita/markina-gallery/actions/runs/44845952777) concluiu `success` para a PR #398 no SHA `7c4e6842d0bd97327c754b1c2d06102c554ad51a`. Passaram OpenSpec, escopo, Gitleaks, frontend, backend-quality, imagens AMD64/ARM64, os quatro shards do backend, `homolog-inventory-policy` e `gemma-runtime`. A política agregada instalou Ruff 0.17.6, aprovou os testes do artefato (4), do inventário executado com `sudo` (6) e do instalador executado com `sudo` (5), validou o canal protegido e montou/verificou o bundle no runner: `source_sha=4d6b17b12da5503abeef4a0625eb77fee29aa647`, `bundle_sha256=d715489b5e2836a8847e1803c84ad9ba791de8996401321542f86836fd943611`. O arquivo ficou no diretório temporário do runner; não foi publicado como release nem transferido ao servidor.

O ciclo de correção da CI encontrou e resolveu três incompatibilidades: o job agregado não preparava Ruff; o builder era chamado como executável apesar de estar versionado sem esse modo; e uma asserção global impedia o staging temporário recém-adicionado ao forced-command. O workflow agora instala Ruff e chama o builder via Bash. O teste de política verifica SHA remoto antes do staging, limpeza via `trap`, ausência de temporários no caminho de preflight legado e ausência de `git fetch` no wrapper. A execução final passou todos esses gates.

Os jobs de preflight e publicação protegidos ficaram ignorados por se tratar de uma PR. Nenhum inventário do host, SSH, wrapper/runtime, vínculo Drive, ensaio remoto, backup real ou timer foi executado.

## Limites e gates pendentes

- As tasks de implementação e validação 3.2l, 3.2m e 3.2n estão concluídas com as evidências locais e de CI acima. A PR #398 permanece draft e aguarda revisão humana e decisão de integração.
- O gate pai 3.2 permanece aberto: após revisão/merge será necessário executar os despachos protegidos separados para inventariar, instalar o runtime inerte e, com reautorização recente do proprietário, vincular e realizar o ensaio sintético. Isso requer inventário/plano e autorização operacional próprios; `enabled=false` deve ser preservado.
- A validação não escreveu no Google Drive, não vinculou a pasta, não gerou backup real e não habilitou/iniciou serviço ou timer. A task 3.3 continua pendente de autorização específica para a primeira cópia real e de prova de recuperação.
