# Continuidade — 14/09/2026

## Autorização e escopo

Proprietário confirmou explicitamente o plano após inventário (`Sim, confirmo`):
preservação de logo/favicon/ícone, backup, publicação em homologação e atualização do
worker de prévias já ativo na mesma versão. Nenhum novo transporte/chave de notificações
é ativado nesta operação. Sem alteração de terceiros, porta ou subdomínio.

## Implementação e evidências locais

- 6/8 tasks concluídas. Persistência exclusiva da API em volume nomeado; fallback local
  e contratos preservados. `docker compose ... config --quiet` aprovado; sem novas portas.
- `scripts/preserve_branding.py`: alvo por labels, raiz/nome/tamanho restritos, stop
  gracioso da API antes de ler chaves/copiar bytes, backup com hash, transferência
  atômica sem sobrescrita, override persistente no rollback. Ausência explícita permite
  prosseguir, erro genérico/conflicto aborta e reinicia API antiga. Fontes não removidas.
- Deploy constrói imagens antes da janela sem API. Mantém o worker opcional de ajuste
  de prévias atualizado apenas se já ativo. Rollback anterior à preservação não recria
  containers; após preservação mantém override. Guardas de schema/terceiros intactas.
- Backend cirúrgico: `test_derived_galleries.py -k 'branding or uploaded_app_icon_sizes'`:
  **4 passed, 69 deselected**, SQLite temporário exclusivo; upload/autorização, leitura,
  tamanhos 180/192/512, hashes, preferências e fallback ausente.
- Helper: **11 passed, 1 skipped** em Linux container isolado (skip apenas fixture Docker
  aninhada); inclui symlink real, archive malicioso, válido/ausente, conflito, falha,
  repetição, integridade e retorno da API antiga. Fixture Docker executada separadamente
  no host: três PNGs 64x64 válidos, duas instâncias removidas usando o mesmo volume,
  terceira leitura com hashes idênticos; volume sintético exclusivo removido ao final.
- `scripts/test_deploy_homolog.sh` aprovado em Linux, incluindo políticas e gate de
  preservação no início/rollback. Ruff dos arquivos tocados aprovado. OpenSpec estrito
  e diff check aprovados. Não rodada suíte completa local. CI inclui testes do helper
  e shell como gate. Documentação: `docs/branding-persistence.md`.

## Restante

4.1: publicar commit separado no PR #84 junto à dependência autorizada, aguardar CI,
merge/deploy e conferir mount/SHA/saúde/paridade/terceiros. Não repetir testes já aprovados
sem alteração que os afete. Último inventário remoto: SHA
`23bdee9bb7b3c1f946693f08c48741dee28188f1`, API/web/workers saudáveis, nginx próprio
`127.0.0.1:8080`, domínio `markina-homolog.duckdns.org`. Refresh somente leitura antes
da publicação efetiva; confirmar novamente apenas se escopo/impacto mudar.

4.2 depende do proprietário reenviar os três ativos individuais ainda ausentes. Não
substituir por prancha/sintéticos nem declarar arte real validada antes do reenvio.
Sem sync/archive até revisão humana. Preservar `.codex-tmp/` fora dos commits.
