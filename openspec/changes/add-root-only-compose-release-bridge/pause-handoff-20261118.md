# Ponto de retomada após reinício

Atualizado em 18/11/2026. O proprietário reiniciou o PC e pediu a continuação. Não há teste local nem CI remoto em execução neste momento.

## Estado do repositório

- Worktree: `C:\codex-data\worktrees\saas-release-candidate\Photo Delivery`.
- Branch `fix/prove-received-app-engine-runtime`, HEAD `9ce97e938438b7f2375e761b6fecad832abbae4f`.
- `origin/main` foi buscado e está em `8e702c36bed16f834ca70cd28bc65ce78bf5bff1` (#383). A branch Engine ainda precisa incorporar essa base sem rebase destrutivo ou force push.
- As mudanças Engine estão sem commit. Commits locais `7817c1b5` e `9ce97e93` documentam o diagnóstico operacional anterior; preservá-los. O caminho não rastreado `output` é preexistente e não deve entrar no commit.
- Arquivos modificados/criados: `.github/workflows/ci.yml`, artefatos de `openspec/changes/add-root-only-compose-release-bridge/`, `scripts/check_prod_app_release_scope.py`, `scripts/deploy-prod-app-services.sh`, `scripts/production-preflight-ssh-wrapper.sh`, `scripts/production_app_compose_bridge.py`, testes associados e `scripts/prove_app_engine_promotion.py`.

## Validação local

- OpenSpec: 13/20 tarefas concluídas; 4.2, 5.2–5.4 e 6.1–6.3 continuam pendentes.
- Suíte completa da ponte: 51 passaram, 1 skip de symlink real indisponível no Windows. Escopo: 23 passaram. Política de workflow: 6 passaram. Contratos shell: 6 passaram antes do recálculo final dos pins; pin atual da ponte confere com o blob Git e os contratos de pin são cobertos pelas suítes da ponte/política.
- Ruff, `py_compile`, Bash `-n`, OpenSpec estrito e `git diff --check` passaram. Após o último ajuste da fixture, Ruff, compilação e diff check foram repetidos.
- A integração real Docker não pode rodar no daemon local compartilhado. Executar somente no job existente do backend-quality, em runner GitHub-hosted descartável; o próprio script impõe a guarda de ambiente.

## CI remoto e produção

- CI de `main` `44392683081`, SHA `8e702c36...`: gates de código passaram; preflight read-only falhou durante o inventário, antes de fingerprint. Release/deploy foram pulados. Nenhuma alteração de produção ocorreu. A causa exata permanece aberta.
- Não disparar o instalador protegido de #383 antes do PR Engine integrado, CI verde e revisão do estado resultante.
- A autorização documentada cobre commit/push/PR/merge e caminho protegido, mas qualquer mutação de produção segue condicionada aos gates, inventário, fingerprint, aprovação protegida e plano de impacto zero. Não tocar `.env`, secrets, dados, migrations, workers, backup ou serviços vizinhos.
- O deploy atual é API/web: não instala nem inicia `pyp-platform-backup.service`/`.timer` e não retoma workers ou filas. A volta do job de backup e da fila original ainda não tem data definida; será uma etapa/change separada após fechamento deste release e aprovação própria.

## Próximas ações

1. Revisar diff completo, fixtures da prova, allowlists e pins; repetir validações afetadas se houver alteração.
2. Diagnosticar a saída do preflight `44392683081` de forma minimizada, sem imprimir configuração ou segredos; não inferir que a falha atual repete `semantic_mismatch_environment`.
3. Reconciliar com `origin/main` sem descartar trabalho, confirmar que `output` permanece não rastreado e fora do stage, criar commit Conventional restrito à change e publicar um único PR/CI integrado.
4. Acompanhar o job de Docker isolado no CI e corrigir falhas por evidência; evitar novo push/CI completo quando um rerun dos jobs elegíveis no mesmo SHA servir.
5. Manter tasks 5.2–5.4 bloqueadas até prova Engine, inventário somente-leitura, fingerprint e aprovação protegida. Não fazer deploy sem os gates e autorização previstos.

- Investigação sanitizada adicional do 44392683081 confirmou o passo, mas não encontrou código production-preflight no log de falha; causa ainda não atribuída, sem impressão de log bruto.
