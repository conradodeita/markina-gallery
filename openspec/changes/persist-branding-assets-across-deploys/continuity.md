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

## Publicação em andamento

- Commit separado `196af2de2ae5b2016ade117f25a31c808fa7fc8c` publicado no PR #84.
- CI `34912180601` success: backend **605 passed, 3 skipped**, helper **11 passed/1
  skipped** (fixture Docker executada localmente), políticas shell aprovadas;
  frontend/build/OpenSpec/gitleaks verdes. Não houve suíte completa local.
- PR #84 mergeado com autorização em 15/09/2026 00:18 UTC, SHA
  `8adf34cd9cf0ba49f94d8fb498ba21b8c3f2fdf9` em `develop`.
- CI/deploy do merge: `34912646640`, em andamento. Não declarar deploy concluído antes
  de verificar health, mount, fonte executada e terceiros.
- Inventário imediatamente anterior ao merge: mesmo SHA remoto 23bdee9, checkout limpo,
  130 GB livres, todos os serviços próprios saudáveis. Terceiros para comparação:
  firefly_bot `9335f5e9077e`, firefly_api `f06f36a5ed33`, firefly_frontend `6ea8a742b093`,
  firefly_db `768223c11835`, nginx-proxy-manager `66c25ca56d8c`, portainer `e49166611a66`.

### Correção focada de entrega

Primeiro deploy de `8adf34cd` falhou no prebuild: `no such service:
preview-adjustment-worker`. Causa: serviço definido em override/profile próprios, não no
Compose base. Nenhuma migration, pausa/preservação de branding ou recriação ocorreu;
guard restaurou somente checkout anterior `23bdee9b`, containers antigos saudáveis.
Correção na mesma task 4.1: incluir arquivo/profile opcional na função Compose apenas
quando o worker já estava ativo; vale para build, subida, health e rollback. Teste
regressivo confirma que o override aparece uma vez com worker ativo e não no caminho
inativo. Não habilita módulo novo, não altera segredo/porta e não amplia o plano aprovado.
