# Inventário de ownership e consumidores — carteira de créditos

## Estado e limites da evidência

Este documento conclui a task 1.2 da change `add-photographer-credit-wallet`. É um inventário estático do código local observado em 31/10/2026, no commit-base `6af538ecd5c46da7691fa973c33869f263945a25` e nos arquivos presentes na worktree. Não confirma o comportamento do deploy, não consultou produção nesta etapa e não alterou código, banco, arquivos de mídia ou serviços.

As matrizes abaixo preservam o baseline anterior à implementação da carteira. A implementação local posterior, ainda não publicada, está atualizada aqui:

| Área | Estado local em 31/10/2026 | Fronteira confirmada |
| --- | --- | --- |
| Schema e provisionamento | Migration `20261031_0094` cria catálogo global, carteira por tenant, ledger, alocações e eventos; provisionamento cria carteira finita sem saldo. | Migration ensaiada apenas no PostgreSQL descartável; não aplicada em produção/homologação. |
| Administração global | Rotas owner-only para pacotes, concessão e revogação; negação comercial é auditada. | `PlatformOwner` persistente autoriza; `InstallationOperator` não recebe capacidade comercial. |
| Upload | JPEG novo de `content` reserva antes da escrita e captura após o rename durável; capa e tenant ilimitado não criam operação. | Retry/reindex da mesma identidade não duplica; mismatch/indisponibilidade deixa pendente; falha comprovada antes da durabilidade libera. |
| Recuperação e exclusão | Worker reconcilia operações antigas; exclusão de ativo é bloqueada enquanto houver reserva/reconciliação pendente. | Fonte durável com fingerprint correspondente consome uma vez; ausência comprovada libera; fingerprint divergente não libera. |
| Superfície web | `/admin/credits` apresenta a carteira do fotógrafo, pacotes e operações owner-only por tenant; o dashboard consulta saldo, consumo recente, reservas, histórico curto e aviso de insuficiência. | Consultas financeiras têm falha isolada; a tela de login e o checkout do cliente não mudam. Validação funcional e responsiva local é registrada nas tasks/testes. |

Essa atualização é evidência de código e testes locais, não observação de produção.

A matriz geral de ownership e isolamento continua em [Matriz de propriedade e isolamento](../add-small-multi-photographer-pilot/ownership-matrix.md) e seu inventário enumerado em [ownership-inventory.md](../add-small-multi-photographer-pilot/ownership-inventory.md). Este complemento cobre somente o caminho de upload, mídia e superfícies afetadas pela carteira.

## Matriz de ownership e efeitos

| Entidade/caminho | Ownership e estado observados | Escrita/efeito | Consequência para a carteira |
| --- | --- | --- | --- |
| Contexto administrativo | Os handlers de upload resolvem `tenant_id` por `directory_tenant_id(db, request)` e exigem `require_admin`; o tenant vem da sessão validada no servidor. | Todos os registros, lotes e efeitos de mídia são consultados com o tenant autenticado. | O tenant de uma operação financeira deve vir do mesmo contexto do servidor, nunca de ID enviado pelo navegador. |
| `PhotoFolder` (`backend/app/auth.py:724`) | Tem `tenant_id`, galeria pública de origem e `derived_gallery_id` opcional. `purpose` é `content` ou `cover_assets`; capa não pode pertencer a galeria derivada. | Define se a pasta recebe conteúdo, capa, audiência, preparação ou publicação. | Decisão do proprietário: somente JPEG novo de `content` é cobrado; `cover_assets` fica excluído. |
| `PhotoAsset` (`backend/app/auth.py:620`) | Guarda `tenant_id`, `parent_gallery_id`, `derived_gallery_id` opcional, `folder_id`, chave de storage, nome e disponibilidade. Há FKs compostas para dono, galeria e pasta. | `POST /admin/photo-folders/{folder_id}/photos` cria/reutiliza metadado por chave da intenção e, para tenant finito, reserva crédito na mesma transação antes dos bytes. | Uma seleção deliberada usa UUID próprio mesmo que os bytes já existam na pasta; retry do mesmo envio mantém a mesma chave. O `PUT` valida hash e captura após rename durável. |
| `PhotoAnalysis` (`backend/app/auth.py:2733`) | Registro do ciclo da fonte com tenant, fingerprint SHA-256, bytes, dimensões, estado, expiração e exclusão; ausência da linha identifica foto legada. | `admit_source` valida capacidade e fingerprint, serializa admissão e persiste `receiving` antes da escrita. | Distingue fonte recebida, processamento facial pendente e legado; não é ledger nem reserva financeira. |
| `MediaJob` e `MediaDerivative` (`backend/app/auth.py:2317`, `2341`) | Mantêm `tenant_id`, foto, tipo/variante, estado, tentativas e paths de derivados. A unicidade de job é foto + tipo; tipo atual é `generate_derivatives`. | Após a fonte, o endpoint enfileira derivados; worker gera prévias em outro ciclo. | O worker não deve determinar se a fonte durável foi cobrada. Falha posterior de prévia não desfaz a gravação do JPEG. |
| `PrivateUploadBatch` e `PrivateUploadBatchAsset` (`backend/app/auth.py:3307`, `3350`) | Mantêm tenant, ator, galeria ou pasta, destinatárias e status; a associação de foto é única por lote/foto. | Rotas de lote iniciam, listam e encerram upload; processamento posterior pode notificar destinatárias e contabilizar conclusão parcial. | Cada `PhotoAsset` possui operação e reserva próprias; falha parcial só libera itens cuja ausência da fonte foi comprovada. |
| Pedido e checkout de fotos | `SaleOrder`, seus itens e pagamentos pertencem ao fluxo comercial de compra de fotografias pelo cliente; a integração Mercado Pago atual usa o recebedor do fotógrafo. | Checkout, confirmação e webhook existentes tratam vendas de fotos. | Permanecem separados de pacotes, ledger e saldo pré-pago do fotógrafo. A compra de créditos é coberta pela change própria `add-mercadopago-credit-purchases`. |

## Matriz de rotas e fronteiras do upload

| Rota/camada | Evidência observada | Resultado e fronteira |
| --- | --- | --- |
| `POST /admin/photo-folders/{folder_id}/photos` (`backend/app/main.py:4872`) | Aceita somente pasta `content`, verifica tenant, estado da galeria e lote aberto; cria ou reutiliza `PhotoAsset` por chave de storage. | Para tenant finito, reserva uma unidade por novo asset usando SHA-256 da chave, antes de a UI iniciar o `PUT`; saldo insuficiente recusa o registro. Não é a fronteira de consumo final. |
| `POST /admin/parent-galleries/{parent_gallery_id}/cover-photos` (`backend/app/main.py:3716`) | Cria/reutiliza asset em `cover_assets`, usando `idempotency_key` na chave da capa e retorna a mesma rota genérica de fonte. | A fonte continua no mesmo `PUT`, mas capa não abre reserva nem movimento de crédito. |
| `PUT /admin/photo-assets/{photo_id}/source` (`backend/app/main.py:6619`) | Resolve tenant pela sessão, valida asset/pasta, aceita JPEG até 25 MiB, verifica conteúdo real e orientação horizontal para capa. `content` usa `admit_source`; `cover_assets` não cria `PhotoAnalysis`. `x-facial-reindex: true` altera o caminho facial. | Se chamado diretamente, garante reserva antes de ler o corpo; compara o hash real com a chave reservada e só captura após rename durável. Retry/replay/reindex reutiliza a operação por tenant+asset; divergência falha fechado. |
| Lotes públicos restritos e privados (`backend/app/main.py:8007–8092`) | Lotes privados de galeria e de pasta pública com audiência `selected`; o cadastro associa fotos e o fechamento sinaliza o lote. | Controlam agrupamento/entrega e reabertura parcial; lote não é a unidade atômica de cobrança. A UI pode concluir alguns itens e falhar outros. |
| Exclusão de foto de pasta (`backend/app/main.py:4748–4840`) | Preserva histórico elegível, remove referências operacionais, jobs e metadados; agenda limpeza de fonte e derivados após commit. | Não reembolsa consumo; exclusão é bloqueada se reserva/reconciliação ainda exigir a fonte como evidência. |
| Remoção de foto privada (`backend/app/main.py:8398`) | Remove a origem administrativa da associação privada e mantém a referência se outra origem continuar válida. | Remover a associação não equivale necessariamente a excluir o `PhotoAsset`; futuras movimentações não podem depender da existência da associação de galeria. |
| Resumo administrativo (`GET /admin/validation-summary`, `backend/app/main.py:2790`; UI `frontend/app/admin/page.tsx`) | Mantém contagens operacionais e carrega separadamente `GET /admin/credits/wallet`. | A UI apresenta disponível/ilimitado, consumo confirmado em 30 dias, reservas, até cinco movimentos recentes e resposta explícita de saldo insuficiente. Falha financeira não esconde métricas operacionais nem vira saldo zero. |
| Gestão global (`GET /admin/platform/credit-tenants`, `/credit-packages`, `/credit-grants`; `backend/app/main.py:2941–3034`) | As rotas de pacote, listagem/seleção de tenant, concessão e revogação exigem o `PlatformOwner` persistente. | `/admin/credits` apresenta pacotes sem preço/quantidade padrão, saldo/histórico do fotógrafo e concessão/revogação com referência auditável por origem. |

## Ciclo do arquivo, retry e processamento

1. A UI calcula uma chave determinística SHA-256 de galeria, pasta e conteúdo (`frontend/app/upload-jpeg.ts`). A rota de metadado cria ou reutiliza o mesmo `PhotoAsset`; ela não envia os bytes.
2. Para JPEG novo de `content` em tenant finito, o cadastro reserva uma unidade na mesma transação do `PhotoAsset`, usando o hash da chave antes da chamada frontend ao `PUT`. Saldo insuficiente impede a transferência. Tenant unmetered e `cover_assets` não reservam.
3. `PUT` direto sem cadastro também assegura reserva antes de ler o corpo; compara o SHA-256 real à identidade reservada e falha fechado em caso de divergência. A operação é única por tenant+PhotoAsset; retry/replay não duplica. `x-facial-reindex: true` reutiliza a operação existente.
4. `write_source` confina staging sob o diretório do tenant, escreve e faz `fsync`, revalida autorização e renomeia atomicamente para a fonte final. Após o rename, o fluxo registra uma captura única. DB e filesystem não participam da mesma transação; se o commit falha, a reserva permanece e a fonte não é apagada.
5. Falha/cancelamento anterior ao rename libera somente se a fonte ausente for comprovada; filesystem desconhecido ou hash divergente mantém a operação pendente. O worker financeiro reconcilia operações antigas: fonte correspondente captura uma vez, ausência comprovada libera, e divergência/indisponibilidade não devolve saldo automaticamente.
6. `finalize_source` e `enqueue_derivatives` seguem posteriores à fonte; prévias não determinam cobrança. A exclusão não estorna consumo e é bloqueada enquanto a operação depender da fonte para reconciliação. Em lotes, reserva/captura/liberação é por foto, permitindo conclusão parcial.
7. A UI repete respostas HTTP 503 usando `Retry-After`, com limite de 20 tentativas (`frontend/app/upload-jpeg.ts`). A chave/foto mantém a identidade técnica para retry e reenvio do mesmo asset.

Se houver queda depois do rename e antes do commit/finalização, arquivo durável e estado persistido podem divergir. A operação e fingerprint persistidos permitem reconciliar sem apagar a fonte ou consumir novamente. Decisão do proprietário em 01/11/2026: bytes idênticos selecionados de novo recebem aviso prévio. Confirmar cria intenção UUID nova e novo débito após a fonte durável; cancelar pula somente as repetidas. Retry/retomada mantém a chave existente. O servidor exige o consentimento no cadastro mesmo se outro envio concorrente aparecer após a prévia.

## Consumidores de UI e testes existentes

| Consumidor | Uso atual |
| --- | --- |
| `frontend/app/admin/galleries/sources/[sourceId]/edit/gallery-editor.tsx` | Registra e envia capas; cadastra JPEGs de conteúdo em sequência, usa lote para pasta com audiência selecionada e apresenta progresso/falhas. |
| `frontend/app/admin/galleries/client-gallery-card.tsx` | Upload sequencial de JPEGs em pasta selecionada, com UUID por intenção, lote, progresso e arquivos para retry que preservam a chave original. |
| `frontend/app/admin/galleries/[galleryId]/page.tsx` | Upload de conteúdo privado, reutilização/retomada de lote, deduplicação pela chave de conteúdo e atualização de estado facial. |
| `frontend/app/upload-jpeg.ts` | Transporte compartilhado, valida extensão JPEG, progresso XHR ou `fetch`, credenciais same-origin e retry de 503. |
| `frontend/app/admin/page.tsx` + `/api/admin/validation-summary` + `/api/admin/credits/wallet` | Dashboard mantém métricas operacionais e exibe snapshot financeiro separado fornecido pela API; carteira indisponível não representa saldo zero. |
| `frontend/app/admin/credits/page.tsx` e `owner-credit-operations.tsx` | Tela de carteira: próprio tenant ilimitado/read-only, catálogo de pacotes, busca/seleção de fotógrafos, saldo/histórico, concessão e revogação FIFO com confirmação da API. |

Os contratos são validados por `backend/tests/test_photographer_credits.py`, `test_tenant_acervo.py`, `test_tenant_producers.py`, `test_private_upload_batches.py`, `test_gallery_workflow_remediation.py`, `test_derived_galleries.py` e `test_highres_pipeline.py`, além de testes da UI de créditos e dashboard. Cada caso cobre sua própria fronteira; a lista não significa que compra/fidelidade estejam implementadas.

## Busca delimitada por entidades de crédito

O inventário inicial não encontrou carteira. A implementação local posterior adiciona `backend/app/photographer_credits.py`, migration `20261031_0094`, rotas owner-only em `backend/app/main.py` e a tela `frontend/app/admin/credits/`. A evidência cobre a worktree local e PostgreSQL descartável; nada foi publicado nem aplicado em produção/homologação.

## Decisões do proprietário e pendências

Decisões registradas pelo proprietário em 31/10 e 01/11/2026 (informação de produto, não observação da produção):

- Somente o proprietário global concede ou revoga créditos e administra pacotes; operador técnico não recebe permissão comercial.
- Não há outro tenant de fotógrafo hoje além da conta do proprietário. O tenant explicitamente associado ao proprietário é ilimitado; fotógrafos futuros usarão saldo finito, sem crédito inicial automático presumido.
- Um JPEG novo em pasta `content` consome um crédito após armazenamento durável. Retry/replay/reindex do mesmo `PhotoAsset` não cria segundo débito; `cover_assets` é excluído.
- O reenvio deliberado dos mesmos bytes à mesma pasta cria nova operação, após um aviso com quantidade e consequência; confirmar envia as repetidas, cancelar pula apenas essas e mantém os arquivos novos. Cada intenção nova usa UUID, enquanto retry técnico conserva a identidade original. A carteira do proprietário não debita.
- Se o banco falhar depois do rename durável, a operação é reconciliada pelo mesmo identificador/fingerprint e recebe no máximo um consumo; uma falha comprovada antes da durabilidade libera a reserva.

Os detalhes técnicos aprovados e implementados localmente estão em [design.md](design.md). A matriz inicial continua útil como mapa dos consumidores que a implementação precisou preservar; seu estado de código não deve ser lido como o estado atual da change. Nenhuma consulta ou alteração de produção foi feita por este inventário.

## Refatoração contínua

A revisão da política em `docs/CONTINUOUS-REFACTORING.md` não identificou limpeza não relacionada segura. As mudanças de upload permanecem focadas em `register_folder_photo_asset`, `import_photo_source` e no serviço da carteira; não removem nem reformatam `uploadJpeg`, `PhotoAnalysis` ou `MediaJob`. A compatibilidade é verificada nos consumidores de galerias, lotes, capa e reindex citados acima.

## Validação e continuidade

- `openspec validate add-photographer-credit-wallet --strict --json`: válido, sem issues; `docs/saas-evolution/requirements.json` foi parseado como JSON válido e reconciliado para R03-061–119.
- `test_tenant_photographer_migration.py`: 18 testes passaram em PostgreSQL descartável; o teste adicional dos gatilhos append-only também passou.
- Testes focados locais anteriores: 22 casos da carteira, 3 fluxos em `test_derived_galleries.py`, 17 de `test_gallery_workflow_remediation.py`, 6 de lotes, 1 high-res e 19 de acervo/produtor em SQLite temporário passaram. Checkpoint frontend final: 67 arquivos/571 testes, lint, typecheck e build passaram; regressões atuais de duplicidade/listagem passaram 4/4. Ruff e `py_compile` focados passaram.
- O checkpoint PostgreSQL final passou em container exclusivo descartável de 1,5 GiB: 28 testes passaram, 1 foi ignorado por ser o parâmetro SQLite de um caso exclusivo PostgreSQL e 6 avisos foram emitidos. O container e a rede dedicados à validação foram removidos após o ensaio; o container anterior de 512 MB que atingiu `DiskFull` permaneceu intocado.
- `git diff --check` passou; foi exibido apenas aviso de conversão LF/CRLF em `backend/tests/test_admin_security.py`, fora desta change.
- `openspec instructions apply` registra 12/12 tasks concluídas após os checkpoints backend/PostgreSQL, frontend e revisão final do diff. A decisão R03-101 está resolvida e refletida nos artefatos. A change é somente local; nada foi aplicado em homologação ou produção e não foi publicada. Sincronização da spec principal e arquivamento aguardam revisão humana.
