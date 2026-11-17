# Validation

## Evidência local

- Inventário estático encontrou 32 funções downgrade com SELECT EXISTS entre as revisões 0094–0126. Todas agora tentam LOCK TABLE em ACCESS EXCLUSIVE MODE NOWAIT antes do primeiro guard.
- Revisão AST adicional cruzou as tabelas FROM/JOIN dos guards e os alvos de `drop_table`, `drop_column`, `drop_constraint`, `alter_column` e `drop_index` com as listas de locks: 32/32 sem lacunas estáticas.
- `pytest -q tests/test_migration_downgrade_lock_guards.py`: 1 aprovado.
- Ruff nas 33 migrations 0094–0126 existentes e nos 2 testes tocados: aprovado.
- `npx --no-install openspec validate protect-data-bearing-migration-downgrades --strict`: change válida.
- A documentação oficial do PostgreSQL confirma a sintaxe `LOCK TABLE ... IN ACCESS EXCLUSIVE MODE NOWAIT`, que `NOWAIT` aborta a transação se houver conflito e que o lock permanece até o fim da transação: https://www.postgresql.org/docs/current/sql-lock.html.
- A regressão PostgreSQL test_downgrade_fails_before_ddl_when_a_writer_holds_a_guarded_table foi coletada no ambiente virtual do backend e ficou pulada porque PHOTOGRAPHER_TEST_DATABASE_URL não está configurada. 127.0.0.1:15470 também está fechado. O primeiro Python consultado não tinha o pacote mercadopago; o ambiente virtual do backend coletou o teste corretamente.

## Limites

- A regressão NOWAIT, os cenários de recusa/vazio e o caso de compra protegida foram executados no PostgreSQL descartável local, conforme a evidência abaixo. A cobertura não executa cada downgrade com toda combinação possível de escritores.
- As migrations 0091–0126 continuam sem rastreamento no HEAD desta branch. O artefato `C:/Users/Conrado/Documents/Codex/2026-11-13/continue-imediatamente-o-trabalho-do-pick/work/release-review/migration-baseline-pre-locks-20261115` registra o baseline histórico reconstruído, os hashes e os diffs de origem; os limites dessa reconstrução estão descritos abaixo.
- A execução local usou banco descartável isolado. Nenhuma migration remota, deploy ou alteração em dados de produção foi executada.
- A task PostgreSQL 3.2 foi fechada com os resultados locais descritos abaixo; nenhum resultado histórico foi tratado como prova desta alteração.

### Gate PostgreSQL resolvido com autorização local — 15/11/2026

A autorização posterior do proprietário para iniciar o ambiente local substituiu a restrição de inicialização do checkpoint anterior. Em PostgreSQL17.11 descartável `127.0.0.1:15470/pyp_photographer_test`, o teste `test_downgrade_fails_before_ddl_when_a_writer_holds_a_guarded_table` passou: uma conexão mantém ROW EXCLUSIVE em `platform_admin_event`, downgrade0122→0121 falha e versão/coluna/tabela permanecem. O teste de recibos0122 também passou; relatório `C:/codex-data/local-review/prepush-closure-migrations-final-20261115.xml` (**8 passed** no recorte completo).

Os testes reais de catálogo confirmaram recusa com histórico e downgrade vazio removendo triggers antes da tabela; são dois dos três aprovados no relatório inicial `prepush-catalog-closure-postgres-20261115.xml`. Os outros oito casos desse relatório falharam por configuração sintética incoerente e foram corrigidos no comando/reexecutados, conforme a validação de encerramento. O downgrade0095 com compra/evento já está aprovado em `prepush-credit-downgrade-final-20261115.xml`. Estas provas fecham a task3.2 no escopo solicitado, sem certificar individualmente 32 downgrades em todas as combinações de escritores.

O baseline e a revisão estática da task3.3 foram concluídos abaixo. A mudança posterior do upgrade0113 pertence expressamente à task3.10 de `add-gallery-media-archive` e não foi atribuída à change de locks. Nenhum upgrade foi modificado pela change de locks; não houve migration remota nem deploy.


### Baseline histórico completo e diff final — 15/11/2026

- Artefato: `C:/Users/Conrado/Documents/Codex/2026-11-13/continue-imediatamente-o-trabalho-do-pick/work/release-review/migration-baseline-pre-locks-20261115`. O diretório contém os 125 arquivos, `manifest.json` com SHA-256 e proveniência por arquivo, e `README.md` com o método e os limites.
- As 89 migrations rastreadas foram extraídas de `HEAD` (`855be42b826c61c8ebdb2bd1e471ca1d28147061`). As 36 migrations 0091–0126, ainda não rastreadas em `HEAD`, foram reconstruídas da cópia pós-lock anterior à mudança posterior de 0113, revertendo os 32 diffs `FileChange` registrados no rollout.
- O grafo Alembic foi analisado: 125 revisões únicas, uma raiz, um head e nenhum parent ausente. AST de `upgrade()` e o restante dos módulos fora de `downgrade()` não diferem entre baseline e cópia pós-lock.
- Os guards SQL `SELECT EXISTS`, erros de preservação e chamadas destrutivas de DDL mantêm as mesmas assinaturas nas 36 revisões; exatamente 32 funções `downgrade()` têm as mudanças registradas.
- 33 das 34 revisões com snapshots anteriores disponíveis coincidem byte a byte. A exceção 0095 é explicada pela cópia de 10/11, anterior a uma correção independente de preservação de compras; a baseline mantém essa correção e reverte apenas a alteração posterior para `NOWAIT`. 0125 e 0126 foram reconstruídas pela reversão dos diffs arquivados, pois não havia snapshot anterior disponível.
- A versão atual da 0113 difere da cópia pós-lock por uma alteração posterior de `add-gallery-media-archive`, task 3.10. O baseline usa a cópia pré-task3.10 para não atribuir essa mudança ao trabalho de locks.
- Limite: como 0091–0126 não estão no Git-base, o baseline é reconstruído com evidência de filesystem e rollout, não um commit Git original. Nenhuma migration foi aplicada por esta revisão.
