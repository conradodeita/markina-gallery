# Design

## Context

Ver proposal.md. O catálogo já aceita ciclo `deleting`/`deleted`, operação `delete_remote` e adapter injetável com `delete_object` idempotente. O worker global reivindica apenas `restore` e `archive`. A conta encerrada já exige que os ciclos e a limpeza local sejam concluídos antes de chegar a `closed`; a recuperação administrativa usa os mesmos ciclos e um console reautenticado.

## Goals / Non-Goals

**Goals:** exclusão manual e retomável de todo o arquivo frio de uma conta fechada elegível; prova de ausência remota por objeto; recibo agregado preservado; CPF protegido mantido até a conclusão de todos os ciclos; recuperação/reabertura impossíveis após exclusão.

**Non-Goals:** expurgo por idade ou rotina; remover fotos reais em desenvolvimento; chamar Google Drive real; excluir banco operacional, financeiro, Termos, dados biométricos ou a identidade mínima do fotógrafo; mudar o fluxo normal de exclusão de galeria.

## Decisions

- **Ação e elegibilidade:** criar um único lote por ciclo atual de encerramento, sob lock tenant-scoped. Somente `PlatformOwner` com senha + TOTP e frase de confirmação pode iniciá-lo. Exigir `Tenant.lifecycle == closed`, `review_due == true`, ao menos um ciclo de arquivo e todos os ciclos do tenant em `archived` com a operação mais recente concluída e limpeza local confirmada, e nenhuma operação em aberto/reconciliação. Ciclo arquivado apenas com manifesto é válido e esse manifesto ainda deve ser excluído/verificado; ausência de ciclos é `archive_proof_unavailable`, nunca um inventário vazio presumido. Validar tudo antes de criar jobs ou alterar estado.
- **Reutilização:** usar `MediaArchiveOperation(operation_type='delete_remote')`, `MediaArchiveCycle` e a fila/coordenador existentes. Não criar cliente Drive nem fila paralela. Prioridade global: `restore`, depois exclusão manual já autorizada, depois `archive`; uma exclusão nunca é criada pelo scheduler.
- **Lote e tentativas:** registrar `TenantClosureMediaDeletionBatch` e itens por ciclo ligados a operações existentes. O lote agrega hash do inventário, contagem total/deletada, solicitante, timestamps e estado; as tabelas de operação/eventos preservam cada tentativa. Replay da solicitação retorna o mesmo lote. Um retry exige nova senha, TOTP e confirmação; somente operações `failed` ou `reconciliation_required` podem voltar à fila. O retry bloqueia primeiro o coordenador global, na mesma ordem do worker, antes de tenant, lote, operação ou ciclo.
- **Checkpoint por objeto:** acrescentar `remote_deleted_at` a `MediaArchiveObject`. Antes da remoção, validar o manifesto canônico e conferir objeto remoto e SHA-256 esperado em streaming. Chamar `delete_object`, reler metadados e só marcar o objeto concluído quando `read_object` confirmar ausência. O manifesto remoto também é um objeto do catálogo e segue as mesmas verificações. A ausência já confirmada é idempotente. Se um objeto marcado como removido reaparecer, suspender para reconciliação.
- **Falhas:** uma resposta remota ainda presente é falha comprovada; resultado de delete/readback que não pode ser determinado vira `reconciliation_required`. Ciclo fica `deleting`, não aceita restauração e o lote retém o verificador de CPF. Outras operações já autorizadas do mesmo lote podem terminar; depois disso, o lote permanece em atenção/reconciliação. Leases expirados retomam a mesma operação; falhas e reconciliação não entram sozinhas na fila e exigem ação explícita do proprietário.
- **Conclusão:** cada ciclo passa a `deleted` só com todos os checkpoints presentes e readback final ausente. O lote conclui somente quando todos os ciclos do seu inventário concluíram; nesse commit grava recibo agregado e apaga apenas `cpf_fingerprint` e `cpf_fingerprint_key_version` do perfil correspondente. Nome, e-mail, perfil restante, pedidos, ledger, transações, aceite e recibos técnicos permanecem. Recuperação e reabertura falham fechadas se o ciclo foi excluído.
- **API/UI:** estender o console existente de encerramento do tenant; respostas têm contagens, status e categoria/etapa sanitizados, nunca PII, caminho, bytes, URL ou ID remoto. Nenhuma mensagem é exibida ao fotógrafo. Ações com `request_id` consultam auditoria antes e depois do lock serializador do proprietário, antes de TOTP e mutação, para que uma repetição concorrente leia o resultado confirmado sem duplicar efeitos ou auditorias.
- **Compatibilidade da auditoria:** ampliar `previous_status` e `next_status` de 16 para 32 caracteres na migration local, preservando estados como `attention_required` e `reconciliation_required` integralmente. O downgrade recusa truncar estados ou remover auditorias de exclusão.
- **Compatibilidade local:** testes usam um adapter sintético. O runtime continua exigindo adapter explicitamente injetado e gate já existente. Não modificar ambiente, segredos, Drive real, Oracle ou bancos persistentes.

## Risks / Trade-offs

- Uma falha externa pode deixar só parte dos objetos removidos; por isso o ciclo permanece oculto e irreversível até o proprietário autorizar reconciliação/retry.
- A verificação integral de cada objeto consome tráfego e tempo, mas evita excluir um ID cujo conteúdo divergiu do manifesto.
- O recibo depende do inventário tenant-scoped e da prova de limpeza local já exigida pelo encerramento. Uma lista vazia de ciclos, um ciclo ausente ou legado sem prova bloqueia o lote em vez de presumir que não havia bytes; por isso não existe lote vazio que remova o verificador de CPF.
- O schema atual declara `delete_remote` e os estados finais, mas não possui checkpoint por objeto nem lote de exclusão. A migration será aditiva e seu downgrade recusará perda de recibos/checkpoints.
- Refatoração contínua: reutilizar a fila, adapter, verificador, reautenticação e painel existentes. Não duplicar cleanup local de `gallery_lifecycle`; a revisão final verificará o uso dos métodos injetáveis e a ausência de uma segunda fila.
