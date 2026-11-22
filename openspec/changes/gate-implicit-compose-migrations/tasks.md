# Tasks

## 1. Compose e inspeção

- [x] 1.1 Retirar dependências implícitas de `migrate`, manter dependências de infraestrutura e reservar `migrate` para manutenção explícita. Evidência: Compose principal e override de prévias renderizados; `validation.md`.
- [x] 1.2 Implementar conferência somente-leitura de revisão/head com falha fechada e mensagens sanitizadas. Evidência: testes SQLite e PostgreSQL em transação read-only; `validation.md`.

## 2. Fluxo operacional

- [x] 2.1 Adaptar homologação para `alembic upgrade` com revisão identificada explicitamente e atualizar documentação de bootstrap local. Evidência: teste shell/policy e `backend/README.md`, `docs/HOMOLOGACAO-AUTH-EXECUCAO.md`.
- [x] 2.2 Registrar o faseamento TOTP e os gates que ainda impedem release em produção, sem executar nenhuma etapa remota. Evidência: `validation.md` e `docs/saas-evolution/candidate-validation-2026-11-03.md`.

## 3. Validação

- [x] 3.1 Validar inspeção em banco descartável e invariância da revisão/ausência de escrita; validar grafo Compose e testes de homologação. Evidência e limites: `validation.md`.
- [x] 3.2 Revisar diff, oportunidade de refatoração proporcional, lint e OpenSpec; registrar evidência e limites. Evidência: `validation.md`.
