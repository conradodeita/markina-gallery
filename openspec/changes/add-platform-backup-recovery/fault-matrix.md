# Matriz de falhas e fronteiras — ensaio local

> **EVIDÊNCIA HISTÓRICA — testes do runtime próprio aposentado em 25/11/2026.** Os módulos e testes citados descrevem o pacote anterior, removido do código ativo. Preserve a matriz para auditoria; não a use como evidência de validação do plano atual nem como autorização de backup, restore ou expurgo.

| Caso | Prova | Resultado/limite |
|---|---|---|
| Chave ausente/tamanho incorreto/chave errada | `test_platform_backup_archive.py`, `test_platform_backup_restore.py` | Recusa sem entregar plaintext; nenhuma inspeção/escrita no alvo para arquivo inválido. Chaves somente sintéticas. |
| Tag, nonce, cabeçalho, corpo, truncamento ou bytes extras | Archive | Autenticação falha; staging fechado; nenhum handle cedido. |
| Instalação, backup, ambiente ou schema divergentes | Archive, payload, restore | Contexto obrigatório e manifesto íntegro antes do destino. |
| Manifesto/hash de membro, ZIP extra/duplicado, symlink ou compressão | Payload | Recusado sem extração nem dump entregue ao restaurador. |
| Interrupção no upload | Storage POSIX | Parcial preservado, prefixo validado e envio retomado sem publicar conteúdo errado. |
| Prefixo incompatível ou checksum errado | Storage POSIX | Conflito/checksum sanitizado; objeto final não publicado, evidência preservada. |
| Quota e acesso negado | Storage/worker | Falha explícita, preserva parcial/cópia íntegra e usa mesmo snapshot no retry. Quota/permissão injetadas localmente. |
| Credencial expirada | Worker com adapter que devolve `authorization` uma vez | Injeção sintética; retry após liberação do adapter conserva UUID e snapshot. Não é teste de expiração OAuth real. |
| Catálogo alterado, truncado, fora de ordem ou com outra chave | Catalog POSIX | Encadeamento/HMAC recusam continuidade, sem reescrever a evidência. |
| Concorrência | Catalog/store/worker | Locks exclusivos; concorrente recebe busy, sem sobrescrever histórico/artefato. |
| Candidato interrompido ou preparado sem artefato | Worker | Falha explícita; não coleta novo snapshot silenciosamente sob o mesmo UUID. |
| Tick repetido no dia UTC | Worker | Mesmo UUID, snapshot capturado uma vez e eventos de sucesso não duplicados. |
| Cópia divergente/preexistente | Storage/worker | Não sobrescreve o objeto conflitante nem recria a origem; outra cópia pode permanecer verificada. |
| Alvo origem, persistente, protegido, não vazio ou sem atomicidade | Restore | Recusa antes de escrita. |
| Alvo PostgreSQL com enum isolado | PostgreSQL 17.11 real sintético | Recusa mesmo sem tabela; enum preexistente preservado. |
| Falha durante pg_restore por role ausente | PostgreSQL real sintético | `--single-transaction` reverte DDL; alvo continua vazio. |
| Outro tenant/banco/origem | PostgreSQL real sintético | Os dois tenants/ledger/biometria voltam no alvo, origem e banco sentinela permanecem iguais. |
| Upload tratado indevidamente como restore | Worker/registro de restore | Apenas uploaded/verified antes do ensaio; `restore_verified` exige recibo e cópia/hash/schema correspondentes. |

Resultados e runtimes constam em `validation.md`. Os casos locais não medem quota, política, credencial, independência ou RTO de um provedor real. Produção, fotos e arquivos de biometria/WhatsApp permanecem fora do ensaio.
