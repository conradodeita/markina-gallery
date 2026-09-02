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
