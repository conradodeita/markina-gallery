# Validação local — 24/11/2026

## Snapshot e escopo

Base: `d7aa32437e426d274eb34cb0cadce0a44ce8cbd0`, branch `codex/propose-media-archive-worker-composition`, worktree `C:/codex-data/worktrees/media-archive-worker-composition`. Alterações locais sem commit/push para revisão. A PR #414 e seu checkout não foram alterados.

Mapa de chamadas: `rg -n "claim_next_operation|configure_media_archive_storage" backend/app backend/tests` confirmou o dispatcher de mídia como único consumidor de aplicação do claim de mídia. O homônimo de lifecycle tem import próprio e permanece inalterado. Filtro UUID opcional mantém a API antiga sem filtro; coordenador, prioridade/FIFO e lease global são preservados.

## Comandos e resultados

- Ambiente Windows, Python do venv existente `C:/codex-data/venvs/pickyourpic-saas-74f613/Scripts/python.exe`, sem instalar dependências. Python global e venv do checkout principal não coletam esses módulos por ausência de `mercadopago`; o venv selecionado possui a dependência real declarada, sem stub de importação.
- No diretório `backend`: `python -m pytest -q -rs tests/test_media_archive_dispatcher.py tests/test_media_archive_worker.py tests/test_media_archive_scheduler.py tests/test_google_drive_media_archive_storage.py tests/test_media_archive_executor.py tests/test_platform_backup_workspace_store.py`: **102 passed, 4 skipped**, 27,34 s. Um aviso Starlette/TestClient preexistente.
- Skips: claim concorrente PostgreSQL e três provas PostgreSQL do scheduler; exigem PostgreSQL local sintético exclusivo, não configurado. Nenhum banco real ou serviço foi utilizado; fixtures locais SQLite em memória e arquivos descartáveis.
- `ruff check backend/app/worker.py backend/app/media_archive_worker.py backend/app/media_archive_scheduler.py backend/tests/test_media_archive_dispatcher.py backend/tests/test_media_archive_worker.py`: aprovado.
- `openspec validate compose-media-archive-worker-storage --strict`: aprovado.
- `git diff --check`: aprovado; revisão do diff e varredura direcionada de marcadores de segredos sem valores reais introduzidos.

## Contratos e limites

A composição sintética cobre tenant divergente, raiz/namespace/finalidade inválidos antes de banco/transporte, descoberta sem ciclos/avisos de terceiros, seleção antes de claim, lease global vigente/expirado de terceiro preservado, retomada do próprio lease, arquivo/readback e recuperação pelo dispatcher. Testes existentes também validam gate/staging e compatibilidade Workspace.

Refatoração proporcional: reutilizados dispatcher, scheduler, claim e executor. Não há novo transporte/fila, factory de credencial ou remoção de consumidores; não foi identificada limpeza adicional segura necessária.

O binding sintético declara escopo fornecido pelo chamador e não prova OAuth, ownership do proprietário ou autorização de conta. Identidade Workspace dedicada distinta do backup e raiz própria são decisões aprovadas; provisionamento/custódia, OAuth, quota, release e ensaio real continuam no gate operacional 1.4. Nenhuma CI remota, Drive, host, credencial ou produção foi acessada. Revisão do coordenador antecede qualquer publicação.

## Revisão corretiva da configuração global e durabilidade

A revisão identificou três defeitos no diff intermediário: adapter nu podia configurar execução global sem escopo; o binding aceitava qualquer storage com quatro métodos; mesmo um storage concreto em memória não é durável e poderia satisfazer readback antes da limpeza local pelo executor.

Estado final: `configure_media_archive_storage` recusa toda tentativa, sem armazenar binding. O dispatcher sem argumento retorna fechado, ignorando o slot legado; em production até a invocação direta é recusada antes de banco/claim/executor. Composição sintética existe somente na chamada direta de harness local com SessionLocal SQLite em memória e raízes temporárias. Nenhum vínculo operacional durável foi implementado ou aprovado. UUID/root da fixture não provam identidade, ownership, autorização nem durabilidade.

Regressões negativas cobrem adapter nu, fixture arbitrária, adapter Google com token sintético/transporte proibido e subclasse. A regressão de storage volátil cobre development/production, tentativa de registro e global indevidamente preenchido, com banco/cleanup proibidos; bytes da origem permanecem idênticos e storage vazio. Arquivo/readback e restauração positivos passam exclusivamente no harness direto local; a restauração mantém também o caller direto legado.

Revalidação final no mesmo venv, na raiz com os seis paths de testes prefixados por `backend/`: **109 passed, 4 skipped**, 18,97 s. Skips PostgreSQL e aviso Starlette iguais aos anteriores. Ruff incluindo `media_archive_synthetic_storage.py`, OpenSpec estrito, diff-check e varredura direcionada de marcadores de credenciais aprovados. Diff local sem commit/push, CI remota, Drive, host, credenciais ou operação de produção. Task operacional 1.4 continua aberta.

## PostgreSQL descartável — fechamento dos skips

Em 24/11/2026, autorização específica para PostgreSQL local sintético. Contexto Docker confirmado `desktop-linux`; imagem local `postgres:17.11`, ID `sha256:ff87138949ad9a46f32ff23bd6852b52ce024a13dffe9b4087be98292cdd3b4f`, sem pull. Nenhum runner genérico descartável compatível foi identificado neste snapshot; usado container exclusivo com remoção em `finally` e verificação de ID/label antes de remover.

Container exclusivo `pyp-media-claim-b-20261124`, label `pyp.task=compose-media-archive-worker-storage`, `pyp.executor=B`, ID `e6f227dc2b4e079e5273b6ae4e950e7ed03b54932ed4cf3e998637923189971e`. Dados em `--tmpfs /var/lib/postgresql/data:rw,nosuid,size=512m`; bind dinâmico somente `127.0.0.1:63570`. Banco `pyp_photographer_test`, usuário sintético `pyp_synthetic`, senha descartável, nenhum bind mount nem volume persistente.

`pg_isready` e uma conexão SQLAlchemy comprovaram banco/usuário esperados e PostgreSQL 17.11 antes dos testes. `PHOTOGRAPHER_TEST_DATABASE_PORT` recebeu a porta dinâmica e `PHOTOGRAPHER_TEST_DATABASE_URL` apontou exclusivamente para esse banco/loopback usando psycopg. Os dois fixtures validam backend PostgreSQL, nome do banco, host e porta declarada antes de criar schemas UUID isolados; seus finalizers removem somente esses schemas. As variáveis existiram apenas no processo de teste e foram removidas em finally, sem editar configuração/segredos.

Com o mesmo Python do venv existente: `python -m pytest -q -rs backend/tests/test_media_archive_worker.py backend/tests/test_media_archive_scheduler.py`: **29 passed, zero skips**, 33,40 s. Avisos: Starlette/TestClient e Alembic `path_separator`, sem falhas. Executados os quatro casos antes skipped: exclusividade global concorrente, descoberta concorrente idempotente e as duas provas de migration com recusa de perda de dados, todas somente no banco descartável.

Cobertura nova: seleção/retomada tenant-scoped e preservação de lease vigente/expirado de outro tenant parametrizadas em SQLite e PostgreSQL; dois workers independentes filtrados pelo mesmo tenant disputam a linha coordenadora e somente um claim é emitido. Job de terceiro com prioridade superior permanece enfileirado sem attempts, e não retoma o lease global expirado do piloto. Sem alterar código de crédito, settlement, lease ou gates para fazer os testes passar.

Container removido em finally após conferir ID e label exatos. Os três containers preexistentes de Evolution (API, DB, Redis) preservados com mesmos IDs. Nenhum serviço/banco preexistente, Drive, host remoto ou produção foi utilizado. Esta evidência substitui a limitação PostgreSQL dos checkpoints anteriores; não altera o bloqueio operacional 1.4 nem comprova durabilidade de storage em memória.

## Fechamento para commit local

Revisão autorizada do coordenador: removido `_MEDIA_ARCHIVE_RUNTIME_STORAGE` de produção por não possuir consumidor. Removidos setups redundantes dos testes positivos; regressões negativas usam `monkeypatch.setattr(..., raising=False)` para criar deliberadamente uma variável inesperada e provar que ela não reabre o loop. O configurador explícito de recusa continua preservado. Essa alteração não afeta consultas/leases nem invalida as provas PostgreSQL de 29 testes acima; somente o dispatcher foi revalidado após a remoção.

Após remoção do slot: `python -m pytest -q backend/tests/test_media_archive_dispatcher.py` no mesmo venv — **19 passed**, 3,73 s, apenas aviso Starlette conhecido. Ruff dos seis arquivos Python, OpenSpec estrito e diff-check aprovados. Escopo e marcadores de segredo revisados antes do commit; sem push/CI remota.
