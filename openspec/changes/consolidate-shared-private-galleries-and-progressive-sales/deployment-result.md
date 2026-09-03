# Resultado do deploy em homologação

## Identificação

- Data: `2026-09-02`.
- Pull request: `#27`.
- SHA integrado e publicado: `f2ba6dc23d5d896daa95c654a2f2539a9cd89664`.
- GitHub Actions: run `33624664090`.
- Deployment do Environment `homolog`: `6221341108`, estado final `success`.
- Alvo: `https://markina-homolog.duckdns.org`.

O primeiro PR `#26` foi fechado porque o gitleaks identificou uma fixture
hexadecimal sintética no histórico. O artefato foi reconstruído em branch limpa,
o teste passou a usar valor de baixa entropia e a branch remota anterior foi
removida. Nenhum force push foi executado e a implementação funcional foi
preservada integralmente.

## Gates de CI

- `backend`: Ruff aprovado; `235 passed, 1 skipped` em `108.62s`.
- `frontend`: lint aprovado, `24` arquivos/`117` testes aprovados e build de
  produção com `18` rotas.
- `openspec`: validação estrita aprovada.
- `gitleaks`: histórico publicável sem ocorrências.
- `deploy-homolog`: política estrutural e teste shell aprovados antes da conexão
  ao servidor.

## Operação remota

- `GALLERY_CAPABILITY_SIGNING_KEY` foi gerada no servidor com segredo aleatório
  exclusivo, arquivo restrito e sem valor exposto no log.
- Inventário prévio confirmou disco em `26%` e containers Markina saudáveis.
- Backup lógico exclusivo da Markina foi criado antes da migration.
- Alembic avançou de `20260831_0033 (head)` para `20260901_0040 (head)`.
- Foram recriados exclusivamente `markina-gallery-api-1`,
  `markina-gallery-web-1`, `markina-gallery-worker-1` e
  `markina-gallery-nginx-1`.
- O script concluiu explicitamente para
  `f2ba6dc23d5d896daa95c654a2f2539a9cd89664`; não houve `down`, prune,
  downgrade, restauração ou operação em projeto de terceiro.

## Healthchecks e smoke

- `GET /healthz`: HTTP `200`, corpo `ok`, em `2026-09-02T11:32:25Z`.
- `GET /api/health`: HTTP `200`, corpo
  `{"status":"ok","service":"api"}`, em `2026-09-02T11:32:26Z`.
- `GET /`: HTTP `200`; o DOM publicado apresenta entrada Cliente/Fotógrafo,
  prefixo brasileiro `+55`, DDD e orientação para celular com nono dígito.
- `GET /api/admin/pricing-presets?include_inactive=true` sem sessão: HTTP `403`.
- `GET /api/admin/notifications` sem sessão: HTTP `403`.
- O ciclo sintético do mesmo SHA foi coberto pela suíte completa e pela matriz
  dirigida `8/8`: link e OTP, identidade reutilizada, associação multiusuário,
  isolamento, seleção, cotação progressiva, pedido, pagamento idempotente,
  confirmação administrativa e preservação de histórico após lifecycle.

## Gate humano restante

Homologação está em paridade funcional com `develop` e pronta para a revisão
autenticada desktop/mobile. Permanecem abertas a task 8.7 até aceite explícito e
a task 8.8 para sincronização/arquivamento posterior. Nenhum dado real de
criança ou biometria foi usado.

## Incremento da primeira revisão humana

- Data: `2026-09-02`.
- Pull request: `#29`.
- SHA funcional: `ff945f9fe4f3eb673b8107739124c2dcdcf9f4f9`.
- SHA integrado e publicado: `c240b10f8667bf60d7912cb83d74dd6d56f41ae5`.
- GitHub Actions: run `33631181609`, estado final `success`.
- Deployment do Environment `homolog`: `6222606118`, estado final `success`.
- Os gates `backend`, `frontend`, `openspec`, `gitleaks` e `deploy-homolog` foram aprovados. O backend concluiu em `3m25s`; o frontend, incluindo testes e build, em `53s`.
- O servidor criou backup lógico exclusivo da Markina, alterou o checkout de `f2ba6dc23d5d896daa95c654a2f2539a9cd89664` para `c240b10f8667bf60d7912cb83d74dd6d56f41ae5` e confirmou `20260901_0040 (head) -> 20260901_0040 (head)`, sem migration nova.
- Como o incremento altera apenas o frontend, somente `web` e `nginx` precisaram ser recriados; `api`, `worker`, PostgreSQL, Redis e Evolution permaneceram em execução.
- `GET /healthz`: HTTP `200`, corpo `ok`, em `2026-09-02T12:45:40Z`.
- `GET /api/health`: HTTP `200`, corpo `{"status":"ok","service":"api"}`, em `2026-09-02T12:45:41Z`.
- `develop` e homologação estão em paridade no SHA `c240b10f8667bf60d7912cb83d74dd6d56f41ae5`. A task 8.7 permanece aberta exclusivamente para o reteste humano autenticado das correções; a change não será sincronizada nem arquivada sem esse aceite.

## Incremento da segunda revisão humana

- Data: `2026-09-02`.
- Pull request: `#37`.
- SHA funcional: `5f6ca203c42c29616b225cf620d469e43654a822`.
- SHA integrado e publicado: `f68a5ce205e3619045e3261b377c981778ab42c8`.
- GitHub Actions: run `33688843960`, estado final `success`.
- Deployment do Environment `homolog`: `6232831214`, estado final `success`.
- Os gates `backend`, `frontend`, `openspec`, `gitleaks` e `deploy-homolog` foram aprovados. Localmente, o backend concluiu `248 passed, 1 skipped` e o frontend `127 passed`, além de lint, TypeScript e build.
- O servidor criou backup lógico exclusivo da Markina, alterou o checkout de `2eab180af1965449e4d97f2462ef78e17d92f5cb` para `f68a5ce205e3619045e3261b377c981778ab42c8` e avançou Alembic de `20260901_0040 (head)` para `20260902_0041 (head)`.
- Foram recriados somente `api`, `web`, `worker` e `nginx`; PostgreSQL, Redis e Evolution permaneceram saudáveis, sem `down`, prune, limpeza ou alteração de recursos externos.
- `GET /healthz`: HTTP `200`, corpo `ok`, em `2026-09-02T22:13:15Z`.
- `GET /api/health`: HTTP `200`, corpo `{"status":"ok","service":"api"}`, em `2026-09-02T22:13:16Z`.
- `develop` e homologação estão em paridade funcional no SHA `f68a5ce205e3619045e3261b377c981778ab42c8`. A task 8.7 permanece aberta para o reteste humano autenticado de PIX simples, desvinculação retomada, publicação ao avançar e primeiro OTP; a change não será sincronizada nem arquivada antes do aceite.

## Incremento da terceira revisão humana

- Data: `2026-09-03`.
- Pull request: `#39`.
- SHA funcional: `d9c6f0bea8e380e083e5443f2e6a18d2c34ae623`.
- SHA integrado e publicado: `d37301e0d38de8e41a720cacf3f19c5ba5fc9499`.
- GitHub Actions: run `33748208935`, estado final `success`.
- Deployment do Environment `homolog`: `6242613460`, estado final `success`.
- Os gates `backend`, `frontend`, `openspec`, `gitleaks` e `deploy-homolog` foram aprovados. A validação local concluiu `252 passed, 1 skipped` no backend e `128 passed` no frontend, além de Ruff, ESLint, TypeScript e build.
- O servidor criou backup lógico exclusivo da Markina, alterou o checkout para `d37301e0d38de8e41a720cacf3f19c5ba5fc9499` e avançou Alembic de `20260902_0041 (head)` para `20260903_0042 (head)`.
- Foram recriados somente `api`, `web`, `worker` e `nginx`; PostgreSQL, Redis e Evolution permaneceram saudáveis, sem `down`, prune, limpeza ou alteração de recursos externos.
- `GET /healthz`: HTTP `200`, corpo `ok`, em `2026-09-03T11:14:47Z`.
- `GET /api/health`: HTTP `200`, corpo `{"status":"ok","service":"api"}`, em `2026-09-03T11:14:47Z`.
- `develop` e homologação estão em paridade funcional no SHA `d37301e0d38de8e41a720cacf3f19c5ba5fc9499`. A task 8.7 permanece aberta para o reteste humano autenticado da disponibilidade automática, identidade reutilizada, link permanente e seleção pública persistente; a change não será sincronizada nem arquivada antes do aceite.
