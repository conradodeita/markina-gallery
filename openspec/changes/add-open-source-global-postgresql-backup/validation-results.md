# Resultados de validação — backup global PostgreSQL

## Prova sintética local — 26/11/2026

### Escopo

- Ambiente Docker Desktop local, contexto `desktop-linux`; nenhum host, produção, Drive, credencial real ou dado de cliente foi acessado.
- Dois containers temporários PostgreSQL 17.11 com imagem `postgres:17.11-alpine`, digest `sha256:266d3c257594e195b309ae9d1805e54c788f1d7b375f56bf6c367aac6c917e7b`; rede bridge e portas dinâmicas limitadas a `127.0.0.1`; armazenamento PostgreSQL em `tmpfs`, sem mounts/volumes persistentes.
- A fixture aplicou as migrations até Alembic `20261113_0126`, criou dois tenants sintéticos, extensão `pgcrypto` 1.3 e roles `NOLOGIN` sem senha para ownership, membership, grants e default ACLs.
- A fixture também contém uma materialized view populada e um large object binário pequeno; ambos são comparados por contagem/tamanho e SHA-256 sem registrar conteúdo.
- Archive `pg_dump` custom da execução repetida após endurecer a normalização do SQL: 823.314 bytes, SHA-256 `49466b295f90a684e75eebe93d8f2254c3e013944a9eead7d2260e4cab07e697`.

### Resultado

`python scripts/prove_global_postgresql_backup.py --run-local-synthetic-proof` concluiu novamente com `synthetic_global_postgresql_proof=passed` em 55,58 s para este fixture, sem representar meta de RPO/RTO.

- PostgreSQL `17.11`, Alembic `20261113_0126` e extensão `pgcrypto` `1.3` conferidos.
- Inventário comparável com 963 relações, 138 tabelas, zero foreign/partitioned tables, 7 sequências, uma materialized view populada e um large object; categorias de schema cobertas: colunas, constraints, índices, views, rotinas, triggers, policies RLS e tipos.
- Contagens e hashes de linhas foram comparados por tabela e, onde havia `tenant_id`, por tenant. Estado de sequências, relações, definições, roles, memberships, owners, grants e default ACLs também conferiram após bootstrap das roles sintéticas.
- Foram comparadas 3 roles sintéticas, 1 membership, 16 grants e 1 default privilege.
- `pg_restore --list` e restore isolado com `--exit-on-error` passaram. O teste de restore completo demonstrou que as roles globais precisam ser provisionadas antes da restauração.
- O perfil de restore com `pg_restore --no-owner --no-privileges` atribuiu os objetos ao usuário de restore (`postgres`) e não preservou grants/default ACLs. O profile completo preservou os owners/ACLs sintéticos após o mesmo bootstrap de roles.
- O dump de schema canônico coincidiu entre origem e restauração completa (`schema_dump_canonical_match=True`). A comparação canonizou somente a forma equivalente de converter array de literais `character varying[]` em `text[]`, e apenas fora de strings, comentários e corpos dollar-quoted; foram identificadas 138 definições com essa forma de deparse. Testes garantem que valores/tipos divergentes, texto SQL opaco e reordenação de colunas visíveis continuam sendo diferenças.
- Oito casos negativos foram rejeitados: archive truncado, SHA incorreto, role ausente, metadados de extensão ausentes, versão de extensão divergente, hash/conteúdo de tabela alterado, large object alterado e conflito que provoca restore parcial. Os dois casos de extensão exercitam a rejeição da verificação de metadados; não simulam ausência de biblioteca binária no sistema operacional.
- Onze testes unitários focados da normalização/diagnósticos passaram com `python -m unittest discover -s scripts -p 'test_prove_global_postgresql_backup.py' -v`; Ruff, formatação Ruff, `py_compile` e `git diff --check` também passaram.

### Isolamento e limpeza

O inventário anterior e posterior à execução repetida permaneceu igual: contexto `desktop-linux`, endpoint local Docker Desktop, 37 containers (SHA-256 `95b773c2d18b2a90d4f9e9dc1593d4c93e91e783fdf1aca1916f64a6d445bb26`), 8 redes (`7fce1445f99627d18fa31b99669a98766112687dfff174b808320b11db36d563`) e 32 volumes (`0f4d8b5c1fd8475d2ea9b88ea061b858785ebd0771dedb50648d18b8b47e49ed`). Não restaram containers ou redes com o rótulo exclusivo da prova; as portas locais 15490–15492 ficaram livres. A limpeza do runner opera apenas sobre IDs próprios cuja etiqueta corresponde ao UUID da execução; nenhuma rede/volume/container preexistente é removido.

Uma execução anterior encontrou churn de containers não pertencentes à prova durante o intervalo e foi corretamente rejeitada pelo comparador global antigo. O runner agora registra qualquer diferença global com contagens/hashes sanitizados e, como gate de limpeza, exige ausência dos recursos que carregam o rótulo exclusivo da prova. A execução final não observou diferença de inventário.

### Limites e pendências

- A prova não consultou a instância atual de produção. O Compose/CI declaram a major PostgreSQL 17, mas patch/digest, extensões, roles, memberships, grants e objetos globais reais permanecem desconhecidos.
- Embora inventarie todas as tabelas e compare contagens/hashes (inclusive tabelas vazias), o runner não semeia dados em todos os domínios da aplicação; os registros de aplicação explícitos são o bootstrap sintético de tenants/admin/wallet e a tabela isolada da prova. A task 1.1 permanece aberta também para fixture representativa das relações de dados ativas.
- `pg_dump` não inclui roles globais do cluster nem tablespaces. O restore completo exige bootstrap externo de roles; a prova sintética não define o manifesto/configuração operacional final de provisionamento de roles, extensões e ACLs.
- Os flags `--no-owner` e `--no-privileges` não produzem efeito em archive custom quando passados a `pg_dump`; para esse formato, devem ser fornecidos a `pg_restore`. Ver [documentação oficial do PostgreSQL 17 para `pg_dump`](https://www.postgresql.org/docs/17/app-pgdump.html) e [para `pg_restore`](https://www.postgresql.org/docs/17/app-pgrestore.html).
- Nenhum destino remoto, cifragem Restic/Rclone, retenção/prune, fila/worker, recuperação de host, serviço ou mídia foi exercitado por esta prova PostgreSQL.
- A task 1.1 permanece aberta até reconciliar o runtime por inventário autorizado e registrar o procedimento aprovado para provisionar as dependências globais da recuperação.
