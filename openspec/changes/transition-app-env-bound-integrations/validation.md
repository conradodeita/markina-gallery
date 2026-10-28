# Validação

## 28/10/2026 — inventário local (task 1.1)

- `rg` confirmou os consumidores de `APP_ENV`, classificadores `*_CREDENTIAL_ENV`, chaves de cofre e campos cifrados em `backend/app`; a matriz e a classificação criptográfica estão em `inventory.md`.
- O teste `backend/tests/test_app_env_transition_inventory.py` verifica que o conjunto e a contagem de linhas com marcadores ambientais/criptográficos não mudou sem revisão e que os serviços Compose que recebem `APP_ENV` continuam exatamente `api`, `worker`, `face-search-worker`, `face-index-worker` e `face-maintenance-worker`.
- `python -m pytest -q backend/tests/test_app_env_transition_inventory.py`: **2 passed**.
- `python -m ruff check backend/tests/test_app_env_transition_inventory.py`: **All checks passed**.
- No run read-only `40715456515`, o conjunto de serviços, saúde e portas passaram antes do bloqueio sanitizado `ambiente_divergente:outro_ambiente_conhecido`. O run não forneceu fingerprint completo, revisão de schema, matriz financeira nem contagem de dados cifrados. A composição ativa/quantidades reais permanecem desconhecidas e não foram inferidas dos arquivos Compose.
- Revisão focalizada: não foi encontrada ferramenta existente de transição ou re-cifragem para `APP_ENV`. Foram encontrados ciphertexts faciais cujo AAD inclui ambiente. Por serem dados biométricos, permanecem fora desta operação; inventário incompleto ou qualquer ciphertext facial vinculado à origem bloqueará a mudança global. Nenhum payload facial foi aberto.
- Nenhum arquivo de configuração de segredo foi lido; nenhum valor secreto, ID de tenant, payload cifrado, serviço de produção ou registro financeiro foi alterado.

## 28/10/2026 — contrato de inventário (task 1.2)

- Implementado `backend/app/environment_transition_inventory.py`: classifica `APP_ENV` sem copiar valores, aceita somente contagens/labels allowlisted, valida revisões, fingerprints de configuração, conjunto de serviços e categorias de bind/portas, e emite SHA-256 canônico somente quando todos os gates passam.
- O inventário exige os 15 serviços do contrato operacional atual, health saudável nos serviços ativos, ausência dos dois workers aposentados, somente bind `127.0.0.1:8080` no nginx, gate live fechado, integração externa classificada e contagens biométricas zeradas. Qualquer fonte desconhecida ou divergente produz blockers e fingerprint `null`.
- O recibo agrega as cinco categorias faciais sem abrir os payloads. `render_environment_inventory` rejeita chaves extras, valores com formato inesperado, checksum divergente e dados não sanitizados.
- `python -m pytest -q tests/test_environment_transition_inventory.py tests/test_app_env_transition_inventory.py`: **12 passed**.
- `python -m ruff check app/environment_transition_inventory.py tests/test_environment_transition_inventory.py tests/test_app_env_transition_inventory.py`: **All checks passed**.
- Os dados testados são sintéticos; nenhuma consulta ao banco de produção, inspeção de segredo ou operação remota foi realizada.

## 28/10/2026 — contextos explícitos e classificação (tasks 2.1, 2.4 e 2.5)

- `IntegrationCipher.from_explicit_context()` valida ambiente, igualdade do binding, keyring, chave ativa e comprimentos das chaves sem consultar `os.environ`; `for_environment()` cria o contexto de destino mantendo o keyring validado em memória.
- Os testes verificam AAD incompatível entre ambientes, chave/keyring inválidos, mensagem de erro sanitizada e preservação byte a byte das variáveis de processo.
- `classify_external_integrations()` classifica WhatsApp, SMTP e facial a partir de flags agregadas e sanitizadas: integração desligada, habilitada e validada para o destino, ou não classificada. Não recebe nem retorna credenciais. O fingerprint bloqueia qualquer integração não classificada.
- O contrato biométrico bloqueia fingerprint quando qualquer um dos cinco contadores de ciphertexts faciais é positivo; as fixtures cobrem embeddings, referências, localizadores, notificações e jobs sem abrir payloads.
- `python -m pytest -q tests/test_app_env_transition.py tests/test_integration_secrets.py tests/test_environment_transition_inventory.py tests/test_app_env_transition_inventory.py`: **47 passed**.
- `python -m ruff check app/app_env_transition.py app/environment_transition_inventory.py app/integration_secrets.py tests/test_app_env_transition.py tests/test_environment_transition_inventory.py tests/test_app_env_transition_inventory.py tests/test_integration_secrets.py`: **All checks passed**.
- Revisão focalizada: o código de transição atualiza somente os dois campos de envelope da conta Mercado Pago; não há refatoração ou remoção de código existente elegível nesta área.
- Nenhum arquivo de segredo foi lido, nenhum payload facial foi aberto, nenhum tráfego externo foi emitido e nenhum dado operacional foi consultado ou alterado.

## 28/10/2026 — re-cifragem transacional (task 2.2, validação parcial)

- Implementados plano e execução local em `backend/app/app_env_transition.py`: validar origem/destino, descriptografar e validar os dois envelopes por tenant/ID de conta, comparar fingerprint antes da primeira escrita, bloquear tabela e linhas no PostgreSQL, re-cifrar/verificar no destino e atualizar somente `access_token_envelope` e `webhook_secret_envelope` em uma transação.
- Ensaios SQLite sintéticos confirmam preservação de tenants, preferências PIX/Mercado Pago, checkout key, revisão do carrinho, valores, estado e referências de pedido; fingerprint divergente aborta antes de escrever e erro na segunda conta reverte a transação inteira.
- Foi adicionado teste PostgreSQL opcional, restrito a `localhost`/loopback e ao banco com nome exato `app_env_transition_test`, usando schema aleatório próprio e removendo somente esse schema. `APP_ENV_TRANSITION_TEST_DATABASE_URL` não está configurada, portanto o teste foi ignorado; nenhum banco remoto ou operacional foi usado.
- Estes ensaios SQLite não demonstram as garantias concorrentes do PostgreSQL. A task 2.2 permanece pendente até executar o teste em um PostgreSQL de teste explicitamente isolado.

## 28/10/2026 — recuperação cifrada e gate operacional (tasks 2.3 e 3.1)

- Backup autenticado AES-GCM implementado com chave derivada via HKDF da chave de integração ativa e domínio separado. IDs, metadados das contas e envelopes originais ficam dentro do arquivo cifrado; o payload externo contém somente chave identificadora, contagem, categorias sanitizadas, fingerprint, nonce e ciphertext. O backup não inclui nem substitui a keyring: ela deve permanecer em armazenamento seguro separado até concluir a verificação e a janela de rollback.
- O backup inclui o contexto ambiental anterior cifrado; recovery valida autenticidade, fingerprint e cada envelope antes de gravar e restaura somente os dois campos de envelope, mantendo o contexto anterior disponível para o operador sem alterar `os.environ`.
- Ensaios sintéticos cobrem backup/restauração após transição, backup adulterado abortando antes da escrita e erro durante restauração revertendo todas as contas. Recuperação/configuração de serviços continua sendo etapa operacional manual descrita em `operations.md`; nenhuma configuração foi aplicada.
- O ensaio ponta a ponta `test_synthetic_runbook_roundtrip_has_no_secrets_or_external_calls` persiste e relê o backup cifrado em diretório temporário do teste, valida os gates, migra e restaura os envelopes sintéticos. O arquivo relido não contém os valores sentinela; o fluxo não invoca provedores externos.
- `execute_approved_mercadopago_transition()` exige fingerprint completo do inventário, confirmação textual que vincula inventário e contas, backup autenticado e declarado persistido/verificado, gate live fechado, zero contagens biométricas, integrações classificadas e a lista exata de consumidores próprios pausados. Fixtures testam aprovação válida e cada bloqueio antes da primeira escrita.
- A guarda local não pausa serviços e não prova que um operador realmente os pausou ou persistiu o backup; `paused_consumers` e `backup_storage_verified` são confirmações do executor. A task 3.1 continua pendente até ensaio operacional específico, sem parada ou alteração remota nesta execução.
- `python -m pytest -q tests/test_app_env_transition.py tests/test_integration_secrets.py tests/test_environment_transition_inventory.py tests/test_app_env_transition_inventory.py`: **58 passed, 1 skipped** (PostgreSQL de teste não configurado).
- `python -m ruff check app/app_env_transition.py app/environment_transition_inventory.py app/integration_secrets.py tests/test_app_env_transition.py tests/test_environment_transition_inventory.py tests/test_app_env_transition_inventory.py tests/test_integration_secrets.py`: **All checks passed**.

## 28/10/2026 — checkpoint de integração e revisão focalizada (task 3.3)

- Com o Python do venv `backend/.venv` (que contém `mercadopago==3.6.0`), `python -m pytest -q` nos quatro módulos novos/alterados e nos testes Mercado Pago de settings, schema, projeções, operações, checkout, worker, webhooks e disponibilidade: **128 passed, 4 skipped** em 296 s. Nenhuma falha observada; entre os skips está o PostgreSQL dedicado não configurado. Avisos emitidos foram de deprecações existentes do FastAPI/Starlette e warnings de DROP do fixture SQLite.
- `backend/.venv/Scripts/ruff.exe check backend/app backend/tests`: **All checks passed**.
- `backend/.venv/Scripts/python.exe -m compileall -q` nos módulos/testes alterados: **passou**.
- `openspec validate transition-app-env-bound-integrations --strict`: **change válida**; `git diff --check`: sem erros de whitespace. A política `docs/CONTINUOUS-REFACTORING.md` foi aplicada à área afetada; imports/lint e revisão não apontaram código substituído elegível.
- O backend não declara etapa de mypy/pyright/typecheck ou build em `backend/pyproject.toml`/CI; Python compileall e testes são a validação local aplicável.
- O commit inicial `61df1a8` foi enviado ao branch de feature. O ajuste de CI para PostgreSQL ainda está em alteração local. Nenhuma migration, configuração, serviço, credencial ou dado de produção foi alterado.
- Para executar a prova PostgreSQL pendente, o job `backend-tests` do CI agora cria um banco `app_env_transition_test` isolado em cada PostgreSQL descartável do shard e fornece sua URL somente ao teste opcional. O teste usa schema aleatório e remove somente esse schema. Parse do YAML do workflow e `python -m unittest scripts.test_classify_ci_scope -q`: **10 passed**. A task 2.2 só será marcada depois do resultado do teste PostgreSQL no CI.

## 28/10/2026 — prova PostgreSQL no CI (task 2.2)

- O primeiro CI `40735393207` executou o teste real no PostgreSQL isolado e revelou que o fixture adicionava tenant e cliente no mesmo flush, sem relacionamento ORM que garantisse a ordem das inserções. A falha foi corrigida somente no fixture, com flush explícito do tenant antes de cliente/conta; nenhum código de produção foi alterado por essa correção.
- Validação local após a correção: `backend/.venv/Scripts/python.exe -m pytest -q backend/tests/test_app_env_transition.py`: **15 passed, 1 skipped** (skip esperado sem URL PostgreSQL local); Ruff do arquivo passou.
- O CI do PR #335, SHA `947582a6b297e5ae650116b0369fef3dfc6c2e88`, run [`40737909487`](https://github.com/conradodeita/markina-gallery/actions/runs/40737909487), terminou **success**. Os três shards backend passaram; o shard 1 aprovou **543 testes, 5 skipped e 1096 deselected**. O banco `app_env_transition_test` foi provisionado no shard, e o teste PostgreSQL `test_postgresql_transition_locks_and_preserves_financial_rows` deixou de falhar; seus asserts verificam envelopes/credenciais por tenant, total, revisão do carrinho, status e ID da order.
- Também passaram `openspec`, `ci-scope`, `gitleaks`, `frontend`, `backend-quality`, imagens amd64/arm64 e `homolog-inventory-policy`. Os jobs de produção foram ignorados por escopo; isso não representa execução, prontidão ou aprovação da transição operacional em produção.
- Task 2.2 validada. Permanecem bloqueadas as tasks operacionais 3.1 e 4.1: não houve pausa real de serviços, inventário/fingerprint atual do servidor, comprovação de origem biométrica, backup operacional verificado ou execução da mudança em produção. Nenhuma credencial real foi trocada e nenhuma configuração, serviço ou dado de produção foi alterado.
