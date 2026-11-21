# Validação da granularidade sanitizada do inventário de containers

## Evidência que motivou a subtask

Após o merge da PR #402, a ponte e o wrapper foram atualizados pelo canal protegido no run `44935123431`, com `containers_unchanged=true`. O inventory read-only `44935370437` falhou com `container_inventory_invalid`; não emitiu fingerprint e `operate` foi ignorado. A categoria atual localiza a validação de um registro fixo API/web/db, mas não distingue papel ou campo. O teste de caracterização reproduziu essa saída genérica antes da alteração.

## Mudança e limite de dados

O inventariador passa a usar códigos estáticos allowlisted que identificam somente o papel fixo (`api`, `web` ou `db`) e a classe de validação (formato, ID, imagem, labels, estado, saúde ou início). Não registra valores observados, nomes/IDs de containers, argumentos/saídas do Docker, exceções ou caminhos. Papel ou classe desconhecidos continuam no código genérico seguro `container_inventory_invalid`. A fingerprint e as precondições continuam ausentes em qualquer falha.

## Validação local

Executada na branch `codex/backup-inventory-container-diagnostics`, baseada na main `33e2a95a8587835501518387106deae194152706`:

- Regressão sintética: 27 combinações (3 papéis × 9 classes) falharam antes com o código genérico e passaram depois com a classe estática correta.
- `python scripts/test_platform_backup_runtime_inventory.py -v`: 10 testes passaram; 1 teste root-only foi ignorado no Windows.
- `python scripts/test_platform_backup_runtime_workflow.py -v`: `platform_backup_runtime_workflow=valid`.
- `python scripts/test_prod_app_release_scope.py`: 30 testes passaram em 265,138 s.
- `python scripts/test_production_release_workflow_policy.py`: `production release workflow policy: ok`.
- Ruff nos dois arquivos Python alterados, sintaxe shell por Git Bash, OpenSpec estrito e `git diff --check`: passaram.
- O pin atualizado do inventariador coincide com o blob `b86f629a7117660334cbe66a86e6eb7aeb315298`.
- O classificador sobre o commit de código `51fc044b987aa839f8fbbaece71014df359c720e` retornou `release_scope=none`; o gate de API/web retornou `app_release_ready=true` e `criterio=somente_api_web`.

## Instalação protegida e inventory após #403 — 21/11/2026 UTC

- A PR #403 foi integrada na main em `e935cbc36c13466af9c93dbfb4246997ddaa47fa`; a CI completa da main `44941683466` concluiu success nesse SHA. A classificação de release permaneceu fora de publicação de API/web.
- O primeiro preflight do canal de backup `44943687719` falhou antes da instalação porque `origin/main` no checkout do host ainda estava desatualizado; não emitiu fingerprint e não alterou o host.
- Com autorização operacional, a instalação protegida da ponte/wrapper `44944029651` concluiu success, preservou as versões anteriores e confirmou `containers_unchanged=true`. A ponte ficou `root:root 0755`, SHA-256 `76f78aa72c47ea4c4ba9a807ac75d12e25551b2d16b341654f702bc76f803177`; o wrapper ficou `root:root 0755`, SHA-256 `34d5ff1e474c64aa8c7acd371dd1d043a4364e8eaea4a9a83bb745b60fb6fb28`. A operação atualizou somente o suporte root-only e a referência `origin/main`; não trocou o checkout ativo nem recriou serviços.
- O inventário app/host protegido `44944231035` concluiu success e confirmou `APP_ENV=production`, `FACIAL_PROCESSING_ENABLED=true`, API/web saudáveis e Nginx somente em `127.0.0.1:8080`. A impressão digital foi mantida no fluxo de aprovação e não foi copiada para este artefato.
- O inventory do runtime `44944398862` concluiu a construção do artefato ARM64, mas a etapa read-only de preflight retornou somente `api_container_project_label_mismatch`. Não emitiu fingerprint nem precondições; `operate` ficou `skipped`. A aplicação não foi alterada. Um segundo inventory app/host (`44945024206`) também concluiu success com API/web saudáveis.
- Essa combinação localiza a divergência na resolução do serviço API pelo inventariador do runtime, que usava um nome gerado fixo, embora a leitura protegida baseada no Compose continuasse validando o serviço. O valor observado do label, IDs, saída Docker e fingerprint não foram persistidos ou divulgados.
- Nenhum runtime de backup foi instalado; nenhuma configuração/destino foi lida ou alterada; não houve escrita no Drive, vínculo, ensaio, cópia real ou ativação de serviço/timer. O estado atual do destino e das unidades permanece não atestado por inventário válido.

## Correção local do seletor de containers — subtask 3.2s

- O inventariador deixou de escolher API/web/db por nome gerado. Ele consulta exclusivamente os labels Compose fixos `project=markina-gallery` e `service=api|web|db`, exige exatamente um ID completo por serviço, inspeciona por esse ID e revalida os labels. Ausência, duplicidade e falha de listagem retornam códigos estáticos allowlisted; nenhuma fingerprint é emitida após falha.
- `python scripts/test_platform_backup_runtime_inventory.py -v`: 13 testes passaram, 1 teste root-only foi ignorado no Windows. Inclui seleção estrita pelos labels, ausência, duplicidade, ID inválido, falha de listagem, labels divergentes e sanitização.
- `python scripts/test_platform_backup_runtime_workflow.py -v`: `platform_backup_runtime_workflow=valid`; `python scripts/test_production_release_workflow_policy.py`: `publication_candidate_ready=true / somente_api_web` e `production release workflow policy: ok`.
- Ruff, sintaxe Bash do wrapper, OpenSpec estrito e `git diff --check` passaram. O pin `BACKUP_INVENTORY_BLOB_SHA` coincide com o blob local `7823d1ef5b318e96fab2ebec0c66c8c66e3f366f`.
- A PR #404 foi aberta contra `main`, commit `d5f06f7dbf9d54a99cf413eef67e5dd94c7b5eac`. A CI da PR `44946701487` concluiu `success`: quatro shards backend, backend quality, frontend, imagens ARM64/AMD64, OpenSpec, gitleaks e política de inventário passaram; gates de publicação API/web foram ignorados.
- A PR permanece aberta para revisão humana. O código corrigido ainda não foi instalado no host; inventário protegido em SHA novo requer autorização operacional específica. Não executar vínculo, ensaio, backup real ou ativar timer com base nesta evidência.
