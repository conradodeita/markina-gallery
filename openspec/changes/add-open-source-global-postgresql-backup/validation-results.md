# Resultados de validação — backup global PostgreSQL

## Prova sintética local ampliada — 27/11/2026

### Fixture e isolamento

- Prova executada no Docker Desktop local, contexto `desktop-linux`, sem host, produção, Drive, credencial real, dados de cliente, entrega externa ou serviço remoto.
- Dois PostgreSQL temporários 17.11 usaram a imagem `postgres:17.11-alpine` pelo digest local `sha256:266d3c257594e195b309ae9d1805e54c788f1d7b375f56bf6c367aac6c917e7b`, rede exclusiva, portas dinâmicas limitadas a loopback e armazenamento em `tmpfs`; nenhum volume persistente foi montado.
- A fixture semeou dados artificiais tenant-scoped em 33 tabelas: cliente/telefone, galeria/pasta/foto/acesso, seleções/favoritos/visualizações/comentários, regras de preço, pedido/grupo de pagamento/itens sem pagamento real, análise/derivados/jobs em estado inerte, ciclo/operação/objeto/evento de arquivo frio com manifesto V1 sintético, política facial desativada/solicitação cancelada/comprovante sintético sem biometria, configuração/evento/entrega de notificação cancelada, auditoria e ledger com grants sintéticos. Há um pacote de créditos global inativo. Os IDs de objeto remoto são marcadores sintéticos; nenhum provider foi consultado.
- As 33 tabelas tenant-scoped têm ao menos uma linha para cada um dos dois tenants; as contagens/hash são comparadas por tabela e tenant. `notification_setting` também preserva e compara os defaults já semeados pelas migrations (seis linhas num tenant e uma no outro). A comparação inclui todas as demais relações, mesmo quando vazias.

### Resultado do dump e restore

`python scripts/prove_global_postgresql_backup.py --run-local-synthetic-proof` concluiu com `synthetic_global_postgresql_proof=passed` em 57,45 s; duração exclusiva desta fixture, sem representar RPO/RTO/SLA.

- PostgreSQL `17.11`, Alembic `20261113_0126`, extensão `pgcrypto` `1.3`; inventário: 963 relações, 138 tabelas, 7 sequências, 1 materialized view e 1 large object.
- Archive custom: 832.522 bytes, SHA-256 `8f3ec4ade4297a4ca31ffbab1d8d28f4c1073a5e2e3b3694f8bc1663e1406f6a`.
- `pg_restore --list`, restore isolado com `--exit-on-error`, comparação de conteúdo/hash por tabela/tenant, estado das sequências, catálogo/schema e dump canônico passaram. O restore completo após bootstrap das roles preservou owners/grants/default ACLs: 3 roles sintéticas `NOLOGIN`, 1 membership, 16 grants e 1 default privilege. O perfil com `pg_restore --no-owner --no-privileges` continuou demonstrando a perda intencional de owner/ACL.
- Oito casos negativos foram rejeitados: archive truncado, SHA divergente, role ausente, metadados de extensão ausentes, versão de extensão incompatível, conteúdo de tabela divergente, large object alterado e conflito de restore parcial.
- 13 testes focados passaram; Ruff, formatação Ruff, `py_compile` e `git diff --check` passaram após a alteração final do resumo sanitizado.

### Limites

- Os dados adicionados são representativos, mas não populam todos os 138 tables; a comparação de todas as relações não equivale a cobertura de dados de todos os domínios. O manifesto de mídia é V1 e os IDs são fictícios; a prova não cobre binding `provider_id`/manifesto V2 da #441, não acessa Drive e não testa recuperação de mídia.
- Filas foram restauradas como dados e não havia aplicação/worker conectado ao destino. Isso não prova pause/reconciliação na operação integrada; task 4.2 continua aberta.
- O runtime atual não foi consultado. Patch/digest, roles/extensões/globals e o método operacional de provisionamento continuam desconhecidos ou sem decisão. `pg_dump` não inclui roles globais nem tablespaces; os resultados anteriores sobre flags de restore custom permanecem aplicáveis. Task 1.1 continua aberta.
- Dois ensaios iniciais da nova fixture pararam antes do dump por defeitos no harness (namespace UUID curto; campo `photo_folder.updated_at` omitido). Um terceiro revelou que migrations já haviam criado a configuração `payment_reported` em um tenant; a fixture passou a reutilizá-la e cria a configuração apenas quando ausente. Após cada interrupção, os containers e a rede com a etiqueta da prova foram removidos; inventário voltou a `desktop-linux`, 37 containers, 8 redes e 32 volumes, hashes iguais ao baseline registrado, porta 15490 livre. Nenhum artefato persistente foi criado.
- A prova não executou destino Restic/Rclone, retenção/prune, rotina diária, aplicação/worker, promoção, rollback operacional ou produção.

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
