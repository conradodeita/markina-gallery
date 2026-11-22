# Validação local — 04/11/2026

## Resultado

- `docker compose -p markina-gallery -f docker/docker-compose.yml --profile maintenance --profile facial config --format json`: API, worker geral e três workers faciais dependem de `db`/`redis`; `migrate` tem perfil `maintenance` e comando de conferência. `seed-admin` também depende de `db`, sem `migrate`.
- Com `-f docker/docker-compose.preview-adjustment.yml --profile preview-adjustment`, o worker de prévias depende de `db`/`redis`, sem `migrate`. O Compose renderizou sem erro. Não houve `compose up` nem alteração de serviços existentes.
- `python -m pytest -q tests/test_schema_revision_check.py`: **3 passed** em PostgreSQL 17 local exclusivo, descartável (`127.0.0.1:15471/pyp_schema_gate_test`) e SQLite. O teste PostgreSQL executou a conferência dentro de `SET TRANSACTION READ ONLY` e confirmou a revisão inalterada. O container temporário `pyp-schema-gate-20261104` foi parado e removido por `--rm`.
- Nova execução sem PostgreSQL temporário: **3 passed, 1 skipped**, sendo o skip esperado para o teste PostgreSQL opt-in. O teste de comando usa a head real do checkout e prova falha em revisão atrasada, sucesso na head e ausência de upgrade automático.
- `TOTP_MIGRATION_TEST_DATABASE_URL` apontando apenas para PostgreSQL 17 temporário local em `127.0.0.1:53005/totp_migration_test`: `python -m pytest -q tests/test_totp_migration.py` concluiu **8 passed em 75,37 s**. Inclui falha transacional de `0091` sem schema/segredos parcialmente alterados, convivência do ORM legado após expand, recusa de contract durante dual-write, contract `0093` e downgrade restaurador. O container `pyp-totp-phase-20261104` foi parado e removido por `--rm`. `python -m alembic heads` retornou uma única head: `20261103_0098`.
- `python scripts/test_deploy_homolog_policy.py`: ok. `C:\Program Files\Git\bin\bash.exe scripts/test_deploy_homolog.sh`: ok, incluindo cenários de falha de migration, parada de writers e preservação do rollback. `python -m ruff check app/schema_revision_check.py tests/test_schema_revision_check.py`: ok. `openspec validate gate-implicit-compose-migrations --strict`: válido.

## Limites e bloqueio de release

Esta mudança impede migration implícita no Compose local, mas **não autoriza produção**. O schema observado historicamente em produção era `0090`; o candidato tem head `0098` e a cadeia passa por `0091` (expand) e `0093` (contract). Ainda faltam inventário atual de todos os consumidores API/workers, ensaio de compatibilidade entre imagens, backup e restauração provados, desligamento de dual-write, análise de locks e demonstração de atendimento contínuo. Se alguma etapa exigir indisponibilidade temporária, apresentar alcance, janela e reversão ao proprietário e obter consentimento específico. Não houve SSH, acesso a banco de cliente, alteração de configuração real, migration remota ou deploy.

## Revisão do escopo

A busca no Compose principal e nos overrides encontrou uma dependência adicional no worker de prévias, removida nesta change. A revisão de scripts consumidores encontrou o deploy de homologação, ajustado para revisão explícita; os scripts de produção já usam revisões explícitas e não foram alterados. Nenhuma outra limpeza foi comprovada como segura ou relevante. O diff relacionado não introduz segredo, migração automática ou mudança em dados de tenant.

## Revalidação do Compose do candidato — 12/11/2026

- O Compose principal e o override de ajuste de prévias foram validados sem exibir a configuração interpolada: `docker compose -p markina-gallery -f docker/docker-compose.yml --profile maintenance --profile facial config --quiet` e `docker compose -p markina-gallery -f docker/docker-compose.yml -f docker/docker-compose.preview-adjustment.yml --profile preview-adjustment config --quiet` — ambos retornaram exit 0.
- `tests/test_schema_revision_check.py`: **3 aprovados, 1 ignorado** em 0,95 s; o skip é a prova PostgreSQL opt-in sem URL configurada nesta execução. O teste restante confirma revisão atual/head, falha fechada quando atrasada e ausência de upgrade automático.
- Revisão do diff confirma que os serviços de aplicação dependem somente de DB/Redis saudáveis; `migrate` fica em `maintenance` e executa conferência somente-leitura. As variáveis `ADMIN_TOTP_*` são configuração de runtime da change `protect-admin-totp-secrets`, não operação de migration. Nenhum `up`, `down`, restart, seed, banco ou serviço foi executado.

### Conferência PostgreSQL em transação somente leitura — 15/11/2026

O contrato rígido `test_postgres_schema_revision_check_in_read_only_transaction` passou: **1 passed**, 0,88 s, zero skips/falhas. JUnit `C:/codex-data/local-review/prepush-schema-readonly-postgres-20261115.xml`. O checker aceita revisão igual, recusa divergente e conserva o valor de `alembic_version` dentro de `SET TRANSACTION READ ONLY`.

O início local foi autorizado pelo proprietário. Runner externo criou somente `pyp-schema-gate-20261115`, PostgreSQL17.11 da imagem já existente, loopback15471, tmpfs256MiB, memória384MiB/pids128, sem volume persistente. Ao final conferiu ID/nome/label próprios e removeu somente esse container. Contexto Docker `desktop-linux`; resumo sanitizado em `C:/codex-data/local-review/prepush-schema-readonly-postgres-20261115-summary.json`. Serviços preexistentes preservados, nenhuma aplicação de migration ou escrita em produção.
