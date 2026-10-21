# Evidências

- Base: PR #260 aberto/draft, SHA `0959c64`, sem alteração do branch pai.
- OpenSpec strict: `add-infinitepay-tenant-credentials` válida antes de código.
- Crypto: `pytest tests/test_integration_secrets.py -q` — 14 passed, Ruff aprovado.
- Migration: `PHOTOGRAPHER_TEST_DATABASE_URL` aponta somente a PostgreSQL 17 descartável `127.0.0.1:15470/pyp_photographer_test`, container exclusivo `pyp-infinitepay-credentials-test`, dados em tmpfs. `test_infinitepay_credentials_migration.py` — 2 passed em 32,92 s, incluindo preservação, FKs negativas A/B e recusa de downgrade com ciphertext. Ruff aprovado.
- Gerador estático de ownership: bloqueio da base por `KeyError: RawDevelopmentSettings`, antes de alcançar a tabela nova; classificação específica e integridade estão em `ownership.md`.
- Integração nova PostgreSQL: `test_integration_secrets.py`, `test_infinitepay_credential_management.py`, `test_infinitepay_credential_checkout.py` e `test_infinitepay_credentials_migration.py` — **30 passed em 229,73 s**. Inclui 9 chamadas HTTP autenticadas/negativas, 5 contratos de checkout e concorrência, 14 casos criptográficos e 2 migrations; não usa autorização mockada ou chamada financeira real. CLI: dry-run não modifica, apply exige confirmação explícita, A não recifra B e falha criptográfica reverte a transação inteira sem imprimir valores.
- Frontend: **63 arquivos/566 testes passaram** em 83,50 s; card InfinitePay tem 11 casos. `tsc --noEmit`, lint do card e `npm run build` aprovados. Lint global sem erros, 34 avisos fora do card; build gera as mesmas rotas, sem página nova.
- Cleanup isolado SQLite: **12 passed, 1 skipped** (caso que requer PostgreSQL). Nenhuma limpeza foi executada em ambiente operacional.
- `docker compose -p markina-gallery -f docker/docker-compose.yml config --quiet` aprovado, sem imprimir configuração resolvida nem criar serviços. Arquivo seguro novo é opcional, API somente; não criado nesta missão.
- Ruff global `backend/app backend/tests`, `compileall` dos módulos novos e OpenSpec strict aprovados. Reconsulta oficial somente documental registrada em `provider-contract.md`.
- Inventário estático novamente delimitado em 21/10/2026: mesmo `KeyError: RawDevelopmentSettings` da base. A classificação R/K de `InfinitePayCredential` foi adicionada ao mapa, sem alterar classificações da missão RAW; o relatório global não é declarado aprovado.
