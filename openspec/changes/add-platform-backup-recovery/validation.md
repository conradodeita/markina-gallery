# Validação — backups e recuperação da plataforma

## Revalidação PostgreSQL local pré-push — 15/11/2026

- `PYP_BACKUP_POSTGRES_TEST=1`, `APP_ENV=test`, somente `test_platform_backup_postgres.py`: **1 passed em 24,94 s**, sem skips. JUnit externo `C:/codex-data/local-review/prepush-backup-postgres-20261115.xml`.
- Docker Desktop local `desktop-linux` conferido; imagem `postgres:17.11-alpine` já disponível, ID `sha256:266d3c257594e195b309ae9d1805e54c788f1d7b375f56bf6c367aac6c917e7b`, sem pull. A fixture criou somente dois containers com nomes aleatórios, labels por execução/instância/papel, `network=none`, sem portas e PostgreSQL em tmpfs; removeu apenas seus IDs após revalidar os labels. Conferência posterior sem containers do ensaio; bases visuais/TOTP/gates e os três containers Evolution preservados.
- Restore global real comprovou conteúdo sintético equivalente, origem e banco sentinela preservados, recusa de restore sobre alvo preenchido, pacote adulterado sem materialização, rollback transacional quando falta a role e recusa de alvo que contém somente enum. Nenhum alvo, backup ou credencial real foi acessado.
- Os 13 módulos de `platform_backup` mantêm os mesmos hashes do inventário de 14/11. A revisão estática anterior foi reaproveitada nesses conteúdos; `remote_copy.py`, `postgres_sandbox.py`, `worker.py` e o entrypoint foram conferidos diretamente nesta continuação. A prova não cobre os contratos POSIX ignorados no Windows, cópia Workspace real ou independência física das cópias, que continuam gates separados. Nenhum deploy ou ativação do coordenador em produção.

## Inventário local — 06/11/2026

Revisão estática das fontes listadas em `inventory.md`, Compose e worker. Os dumps e pacotes existentes protegem operações específicas de release/migration; não estabelecem backup SaaS recorrente, retenção ou recuperação por tenant. A ausência de serviço de backup no Compose não exclui serviço externo ao repositório. A task 1.1a está concluída nesse limite.

## Inventário externo — 06/11/2026

A consulta autorizada por SSH inventariou timers, propriedades de resultado systemd, containers/portas, nomes de volumes e arquivos cron. O serviço de backup dos dois projetos terminou com status 1, das 03:01:22 às 03:15:34 -03. O filtro processou 14 mensagens e encontrou duas ocorrências de `RuntimeError` e de reconciliação interrompida, sem atribuição segura por projeto. Fonte e logs brutos não foram exibidos/salvos.

A leitura estática autorizada identificou comparação entre nomes listados e o esperado derivado do estado anterior. Nenhum job, migration, backup ou restore foi executado. A task 1.1b está concluída nesse limite.

## Correção de premissa — 06/11/2026

- Consulta estruturada via D-Bus executada como root: `LoadCredential` tem assinatura `a(ss)`, contagem **0**, campos completos.
- Runtime observado: systemd **249**; rclone **1.53.3** em `/usr/bin/rclone`; sem binário alternativo em `/usr/local/bin/rclone`.
- A interpretação anterior da saída textual como credencial não era válida. A indisponibilidade de `systemd-creds` não bloqueia essa consulta e não implica segredo ausente.
- A categoria anterior `credential_materialization` e as buscas de arquivos do suposto ID não provam falha do serviço. Os registros de ausência de credencial e necessidade de correção pelo operador foram reconciliados.
- Uma reprodução em namespace sem rede examinou somente inicialização local; não realizou chamada externa. Os aliases dos dois projetos são do tipo `crypt`; valores de configuração não foram emitidos.
- Montar somente o arquivo read-only não protege o diretório pai contra temporários. A ausência de toda escrita temporária nas tentativas anteriores não está comprovada. Nenhum resíduo foi removido.

## Prova de reconciliação de metadata — 06/11/2026

Uma única execução isolada comparou os dois destinos. Namespace privado, diretório de configuração inferior read-only, overlay e cache em tmpfs permitiram ao rclone persistir sua configuração somente em RAM. O arquivo e o diretório persistentes não foram alterados pela execução bem-sucedida segundo a comparação de metadata. Não houve mudança de configuração do serviço nem exposição de segredo.

| Check | Resultado |
|---|---|
| Execução como root no namespace privado | Confirmada |
| Diretório inferior read-only | `true` |
| Upper/work/cache em tmpfs | `true` |
| Overlay montado | `true` |
| Configuração regravada em RAM | `true` |
| Metadata de nomes/inodes/tamanhos/mtime/modos do original igual antes/depois | `true` |
| Pick-your-Pic | 2 entradas, 2 esperadas, 0 faltantes, 0 extras, conjuntos iguais |
| ClearBudget | 3 entradas, 2 esperadas, 0 faltantes, 1 extra, conjuntos diferentes |

As listagens foram não recursivas, sem modtime/mimetype/hashes. Somente o estado exato `last-success.json` foi lido, com limite de 128 KiB, para consultar `archive`. Nenhum arquivo de backup foi aberto/baixado, nenhum objeto foi corrigido ou excluído. Relatório sanitizado não contém nomes/IDs, JSON do estado, logs brutos ou secrets.

A task **1.1c está concluída**: a comparação solicitada foi realizada e a divergência foi preservada. A observação do ClearBudget é compatível com o ramo de proteção, mas não prova causa histórica exclusiva da falha. Igualdade do Pick-your-Pic não comprova conteúdo íntegro ou restauração.

## Revisão proporcional e validações

Alteração documental e diagnóstico de metadata; nenhum código funcional foi modificado. Foram eliminadas das conclusões vigentes as premissas de credencial systemd ausente. Não há refatoração de runtime elegível neste escopo. Os dados operacionais e as alterações locais preexistentes foram preservados.

A validação OpenSpec strict das changes `add-platform-backup-recovery` e `add-platform-owner-console` passou em 06/11/2026 após a reconciliação documental. O desenho 2.1 e a política aprovada também passaram strict depois de dividir uma norma longa em requisitos de política e escopo. Esta evidência documental não substitui testes do código que será implementado.

## Arquivo autenticado local — 06/11/2026

`backend/app/platform_backup/archive.py` usa AES-256-GCM em streaming, AAD canônico vinculado ao contexto e staging anônimo cedido somente depois da validação integral. Chave não é lida de configuração real nem persistida. Limite de 32 GiB e blocos de no máximo 1 MiB; nenhum import/caller em runtime foi alterado.

`backend/.venv/Scripts/python.exe -m pytest -q tests/test_platform_backup_archive.py`: **28 passed** em Python 3.12.9/cryptography 48.0.0. Ruff dos arquivos novos passou. A primeira execução recusou uma fixture sintética com 33 bytes; a fixture foi corrigida para 32, preservando a validação do código. Estilo dos arquivos novos foi ajustado pelo Ruff; nenhum arquivo preexistente foi reformatado. Repetição após essas correções passou 28/28.

O container local de probe, sem rede/portas, reportou Python 3.13.16, cryptography 50.0.2 e pytest 9.1.1. O ensaio complementar do mesmo arquivo no runtime Linux/ARM64 local passou **28/28 em 8,89 s de pytest**, com app/test read-only e tmpfs, sem mounts de dados, pull ou alteração nos containers preexistentes. Ambos os containers próprios terminaram com código 0 e foram removidos pelo `--rm`; imagens e recursos alheios foram preservados.

## Catálogo e cópias sintéticas

`catalog.py`, `filesystem.py` e `storage.py` implementam fronteira POSIX privada, eventos append-only assinados por HMAC com chave derivada HKDF, upload parcial com conferência de prefixo, checksum e publicação por link exclusivo sem sobrescrever destino. O resultado é somente uploaded; não concede restore comprovado. Ruff dos arquivos novos passou. Os testes POSIX passaram **16/16 em 5,47 s** no container próprio Linux/ARM64, sem rede/portas. Foram cobertos reinício/reabertura, corrupção/truncamento/ordem/chave do catálogo, lock concorrente, retomada, quota/acesso, checksum, symlink/hardlink e preservação de arquivo alheio. O container terminou com código 0 e foi removido pelo `--rm`. A task 2.2b está concluída nesse escopo sintético.

## Worker diário global local

`payload.py` empacota somente dump custom `PGDMP`, configurações essenciais explicitamente fornecidas e manifesto cifrado; recusa membros ZIP extras/duplicados, symlinks, compressão e divergências de checksum/contexto antes de ceder o dump. **10 testes passaram** em Windows/Python 3.12.9. `worker.py` e o índice diário assinado do catálogo reutilizam o mesmo UUID/artefato por dia UTC, reabrem cada cópia e mantêm falhas sem promover envio a restore comprovado. Nenhuma coleta de configuração real ou chamada de provedor foi ligada ao runtime.

A primeira coleta conjunta Linux falhou porque o diretório de trabalho da imagem preexistente priorizava seu app antigo em vez do bind read-only. O driver foi corrigido para `--workdir /work`; não foi alterado código para mascarar import. A suíte conjunta repetida passou **62/62 em 27,79 s** (archive, payload, storage e worker), com Python 3.13.16/cryptography 50.0.2. Ruff dos novos módulos/testes passou. O container próprio terminou com código 0 e foi removido pelo `--rm`. A task 2.2c está concluída no escopo sintético; pg_dump/restore real local permanece na task 2.3.

## Restore PostgreSQL descartável — 06/11/2026

`restore.py` autentica ciphertext, GCM e manifesto antes de inspecionar/escrever o destino; exige alvo descartável, vazio, atômico e diferente da origem, e só emite recibo depois de conferir schema. **12 testes de contrato passaram** em Windows/Python 3.12.9. `postgres_sandbox.py` aceita apenas Docker Desktop local, IDs completos e labels/UUIDs do ensaio, rede none e nenhuma porta; não recebe DSN/host ou banco arbitrário. Configuração é conferida em staging e não aplicada.

Ensaio opt-in `PYP_BACKUP_POSTGRES_TEST=1`: **1 teste de integração passou em 46,68 s**, usando dois containers novos PostgreSQL **17.11**, imagem amd64 local `sha256:266d3c257594e195b309ae9d1805e54c788f1d7b375f56bf6c367aac6c917e7b`, PGDATA em tmpfs, sem rede/portas/volumes persistentes. Dump custom real foi empacotado, cifrado, autenticado e restaurado. Conferidos dois tenants sintéticos, ledger em centavos, tabela biométrica sintética, schema e ownership, preservação do banco origem e de banco sentinela distinto.

Repetir sobre destino já preenchido foi recusado; adulteração deixou outro banco vazio; um dump com role ausente provocou falha depois de DDL e `--single-transaction` reverteu o conjunto, mantendo o alvo vazio. Configuração privada sintética não foi aplicada. A fixture conferiu IDs/labels antes de remover somente os dois containers próprios. Essa prova não valida bancos/backups reais, roles arbitrários, mídia, RTO de produção ou independência externa. O registro assinado de restore e a suíte integrada serão revalidados antes de marcar 2.3/2.4.

Complemento: a recusa de destino não vazio foi ampliada para tipos/enums e objetos globais relevantes. A repetição Windows de contratos/integração passou **14/14 em 52,83 s**, incluindo recusa de enum já existente sem removê-lo. A suíte Linux de contratos passou **76/76 e 1 skip** em 53,58 s; o skip é o PostgreSQL opt-in já ensaiado separadamente. Esse conjunto validou também o recibo assinado de restore somente para hash/schema/cópia previamente verificados. Task 2.3 concluída. A injeção explícita de credencial expirada como erro de autorização do adapter está sendo acrescentada à matriz 2.4; não é um teste OAuth real.

## Matriz de falhas local

`fault-matrix.md` relaciona cada fronteira ao teste correspondente. A injeção explícita de credencial expirada (`authorization` uma vez no adapter) e o retry com mesmo UUID/snapshot passaram na rodada focada Linux: **23 passed em 20,80 s**. Junto dos testes de quota, checksum, retomada, arquivo/chave/contexto inválidos e rollback real sintético, isso conclui a task 2.4. Não houve teste de expiração OAuth ou quota em conta real.

## Retenção local validada

`retention.py` calcula a união 7/4/3 por períodos UTC e protege o último ponto com restore declarado; o catálogo/arquivo sobrevivente são revalidados antes de qualquer remoção local explicitamente confirmada. Roots, IDs e domínios devem ser distintos; locks ordenados e hash/GCM/manifesto/prova assinada precedem unlink de um único arquivo redundante. O scheduler nunca chama essa operação. Não existe adapter de exclusão remota nem expurgo real autorizado.

As verificações repetidas de receipt/ciphertext foram centralizadas em `archive.py` e reutilizadas pelo worker, restore e retenção; isso também aplica o limite de tamanho antes de consumir origem declaradamente excessiva. Testes Windows atualizados: **58 passed/10 skips POSIX** em 0,77 s. Ruff passou. A suíte final Linux, incluindo os testes POSIX de retenção, passou **94/94 e 1 skip em 24,35 s**. O skip é o ensaio PostgreSQL opt-in, executado separadamente. O container próprio terminou com código 0 e foi removido pelo `--rm`. Task 3.1 concluída; task 3.2 aguarda a rodada nativa final/revisão documental.

## Revisão final concluída

- O novo pacote não tem caller em `backend/app` fora de si; não foram alterados API, frontend, autenticação, workers existentes, migrations, Compose ou configuração de segredos. O README existente recebeu somente o link de documentação relacionado; seu diff anterior foi preservado.
- Revisados os três unlink do produto: parcial após publicação exclusiva, building após publicação exclusiva e cópia local explicitamente confirmada após prova do sobrevivente. Nenhuma remoção recursiva, shell=True ou exclusão remota. A remoção de containers está somente na fixture opt-in, com IDs/labels conferidos.
- Chaves/PII/paths não entram nos relatórios ou eventos; membros e configurações permanecem cifrados. Eventos de falha têm códigos allowlisted. O código reaproveita cryptography e o helper Drive existente permanece independente, sem duplicar OAuth/HTTP ou modificar preservação facial/financeira.
- Checksum de ciphertext foi centralizado com limite antes de IO grande, sem generalizar helpers especializados. Nenhum código preexistente foi removido ou reformatado. Dependências/runtime e limites estão em `docs/saas-evolution/platform-backup-local.md`.
- OpenSpec strict das duas changes passou; `git diff --check` do README passou. A ausência de imports de produção foi confirmada por busca focada (rg retornou 1 por ausência de ocorrências, não por falha de OpenSpec).
- Não se executou a suíte integral backend/frontend nem build de frontend: a mudança é um módulo backend interno novo, sem caller existente ou alteração de UI. Nenhum commit, push, sync/archive ou deploy foi realizado.

## Checkpoint final local — 06/11/2026

- Linux/ARM64: **94 passed/1 skip em 24,35 s** no código final de arquivo/catálogo/pacote/worker/restore/retenção. O skip opt-in de PostgreSQL foi ensaiado no host, sem socket no container Python.
- Windows/Python 3.12.9: rodada final dos sete módulos de teste, com `PYP_BACKUP_POSTGRES_TEST=1`, **59 passed/36 skips POSIX em 29,14 s**. Inclui nova criação, dump, cifragem, restore, alvo não vazio/enum, falha por role e rollback PostgreSQL, já usando o helper final de checksum. Skips são exclusivamente os contratos POSIX aprovados no Linux.
- Ruff passou para todos os módulos/testes novos. OpenSpec strict passou para backup e owner-console; diff check do README passou. Não houve mudanças funcionais após essas provas; somente evidência/matriz/decisões/status.
- Inspeção final do daemon `desktop-linux`: **zero containers** com labels de ensaio backup-local-synthetic e backup-restore-synthetic. Os cinco containers locais preexistentes continuavam healthy nas mesmas portas; nenhuma ação remota adicional foi executada durante os testes.
- `requirements.json` revisou somente R07, preservando IDs, statements, source_lines e demais 670 unidades. Contagens recalculadas: 694 itens; 184 precisa mudança, 347 parcial, 102 confirmado, 42 não aplicável, 19 aguarda investigação e zero na categoria decisão do proprietário. R07: 18 parciais, 3 precisam mudança, 2 confirmadas e 1 contextual. Itens adiados por escopo continuam rastreados, sem virar implementados.
- Tasks **12/12 concluídas no escopo local aprovado**. Recuperação por tenant, arquivos, conta/provedor da cópia independente, chave/Drive reais, revisão humana e release/ensaio externo conservam seus gates; nada foi sincronizado/arquivado ou publicado.

Política e escopo foram aprovados pelo proprietário em 06/11/2026; tasks 1.2 e 2.1 concluídas. O código local e seus ensaios podem avançar. Permanecem pendentes o provedor/conta real da segunda cópia, chave real, Drive real e ensaio operacional antes de publicação ou expurgo. Não houve sync/archive, commit, push, deploy ou alteração de produção.
