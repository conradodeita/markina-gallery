# Tasks

## 1. Contrato e migração

- [x] 1.1 Formalizar o contrato de snapshot por pasta pública e registrar a preservação explícita do comportamento privado. Evidência: proposal, design e delta spec definem ajuste ativo em toda pasta, face permitida, snapshot de intensidade/exposição pública com fallback 50%/0 EV e padrão privado 75%/0 EV.
- [x] 1.2 Criar migration aditiva encadeada após a migration RAW integrada para materializar configurações das pastas públicas existentes com ajuste ligado; cobrir upgrade e downgrade sem apagar mídia. Evidência: migration `20261014_0079` encadeada em `20261014_0078` e `test_public_folder_processing_migration.py` verifica pastas públicas com configuração/default/fallback, preserva privada e linhas explícitas e confirma downgrade que não apaga configurações.

## 2. Backend e interface

- [x] 2.1 Ao criar pasta pública, persistir snapshot dos controles atuais da galeria e permissão facial local ativa na mesma transação. Evidência: rota cria a configuração na mesma transação e teste de criação verifica snapshot e defaults.
- [x] 2.2 Remover leitura herdada da galeria para pastas públicas isoladas e impedir que futuras alterações da galeria afetem suas filas. Evidência: testes focados de serviço e ajuste verificam isolamento entre pastas, não cancelamento de jobs e o lifecycle de retenção da fonte.
- [x] 2.3 Atualizar a interface administrativa para apresentar e editar configuração própria sem estado “herdado”. Evidência: testes frontend focados e suíte frontend integrada (511 testes) passaram após retirada da opção de herança e atualização do texto/controles.

## 3. Validação e rollout

- [x] 3.1 Adicionar regressões para criação, isolamento, migration e preservação de pastas privadas. Evidência: execução focada `tests/test_public_folder_processing_migration.py`, `test_folder_processing.py`, `test_folder_processing_api.py`, `test_tenant_configuration.py`, `test_facial_status.py`, `test_highres_pipeline.py` e `test_preview_adjustment.py`: 84 passed.
- [ ] 3.2 Executar validações focadas e amplas, revisar o diff completo e manter evidência atualizada antes de commit/push. Evidência parcial: 84 testes backend focados passaram; suíte ampla registrou 1.355 passed, 60 skipped e uma falha de teste que esperava configuração herdada; o módulo corrigido passou em 4 passed, 1 skipped. Frontend: 511 passed; TypeScript, lint (38 avisos, 0 erros), build, Ruff, migration tests (2 passed), OpenSpec estrito (95/95), `alembic heads` (única head `20261014_0079`) e `git diff --check` passaram. Falta validar CI/PostgreSQL e revisar o diff final antes de fechar a task.
