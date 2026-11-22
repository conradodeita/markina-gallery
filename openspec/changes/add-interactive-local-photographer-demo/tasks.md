# Tasks

- [x] 1. Implementar runner com guards de ambiente/banco vazio, migration explícita, adaptadores sintéticos e caixa local; revisar risco de código obsoleto apenas na área afetada. Evidência: `validation.md`.
- [x] 2. Documentar início, URL, cadastro `example.test`, TOTP e encerramento sem afetar serviços existentes. Evidência: `docs/saas-evolution/local-photographer-demo.md`.
- [x] 3. Executar demonstração local, validar UI e login do tenant, lint, OpenSpec e revisar diff/limites com evidência. Evidência: `validation.md`.
- [x] 4. Restaurar serviço local após encerramento do processo sem migrar nem apagar o banco temporário; validar o estado da UI para o usuário. Evidência: prova assistida e limite de persistência em `validation.md`.
- [x] 5. Reconciliar os runners de cadastro e encerramento com o schema do runtime atual, mantendo revisão nomeada, portas e recusa de retomada incompatível. Duas falhas de coluna ausente reproduzidas; após revisão0126, modelos de cadastro/seed passaram em PostgreSQL real (2 testes), guards5/1skip, Ruff e whitespace. Smoke declara maioridade; não foram iniciados outra API nem migrados bancos existentes. Alcance e evidência em `validation.md`.
