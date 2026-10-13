# Tasks

## 1. Contrato e migração

- [x] 1.1 Formalizar o contrato independente por pasta pública e privada. Evidência: proposal, design e delta spec definem configuração própria, ajuste ativo, face permitida e defaults públicos 50%/0 EV e privados 75%/0 EV sem herança na criação.
- [x] 1.2 Criar migration aditiva encadeada após a migration RAW integrada para materializar configurações das pastas públicas existentes com ajuste ligado; cobrir upgrade e downgrade sem apagar mídia. Evidência: migration `20261014_0079` encadeada em `20261014_0078` e `test_public_folder_processing_migration.py` verifica pastas públicas com configuração/default/fallback, preserva privada e linhas explícitas e confirma downgrade que não apaga configurações.

## 2. Backend e interface

- [x] 2.1 Ao criar pasta pública ou privada, persistir defaults próprios e permissão facial local ativa na mesma transação. Evidência: `initialize_folder_processing` persiste configuração própria nas duas rotas; `test_public_folder_creation_uses_independent_defaults_without_gallery_inheritance` e `test_private_folder_creation_persists_independent_ready_defaults` cobrem defaults mesmo com parâmetros de galeria distintos; os 13 testes de `test_folder_processing.py`, `test_folder_processing_api.py` e `test_public_folder_processing_migration.py` passaram.
- [x] 2.2 Remover leitura herdada da galeria para pastas públicas isoladas e impedir que futuras alterações da galeria afetem suas filas. Evidência: testes focados de serviço e ajuste verificam isolamento entre pastas, não cancelamento de jobs e o lifecycle de retenção da fonte.
- [x] 2.3 Atualizar a interface administrativa para apresentar e editar configuração própria sem estado “herdado”. Evidência: testes frontend focados e suíte frontend integrada (511 testes) passaram após retirada da opção de herança e atualização do texto/controles.

## 3. Validação e rollout

- [x] 3.1 Adicionar regressões para criação, isolamento, migration e preservação de pastas privadas. Evidência: execução focada `tests/test_public_folder_processing_migration.py`, `test_folder_processing.py`, `test_folder_processing_api.py`, `test_tenant_configuration.py`, `test_facial_status.py`, `test_highres_pipeline.py` e `test_preview_adjustment.py`: 84 passed.
- [ ] 3.2 Executar validações focadas e amplas, revisar o diff completo e manter evidência atualizada antes de commit/push. Evidência parcial: após a correção de defaults sem herança, 13 testes focados, Ruff e validação OpenSpec estrita passaram. CI no SHA `23b4ca5`: frontend, Gemma, OpenSpec e gitleaks passaram; backend registrou 1.516 passed, 21 skipped e uma falha no fixture PostgreSQL de limpeza, que não configurava `RAW_DEVELOPMENT_ROOT` após a adição do volume opcional. Fixture atualizado; `test_homolog_cleanup.py` + `test_tenant_migration.py`: 15 passed, 6 skipped localmente (casos PostgreSQL não executáveis sem serviço). Falta novo CI completo e revisão final.
