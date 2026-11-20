# Reaproveitamento do backup global no arquivo de fotos

Registro de continuidade de 20/11/2026, solicitado pelo proprietário para evitar repetição de investigação, configuração e desenvolvimento na próxima etapa. Inventário de código na main `77cf2788` (PR #397). Este documento descreve evidência existente e pontos de integração; não autoriza novas operações remotas.

## Estado e fontes de verdade

- O transporte Drive e a recuperação global sintética possuem provas externas concluídas. A primeira execução recorrente de backup global no destino novo ainda depende dos gates 3.2–3.3 de [enable-platform-backup-runtime](../../openspec/changes/enable-platform-backup-runtime/tasks.md).
- O núcleo de arquivo/recuperação de mídia já existe. Sua ligação ao transporte real e o ensaio operacional permanecem na task 1.4 de [add-gallery-media-archive](../../openspec/changes/add-gallery-media-archive/tasks.md), com contratos no [design](../../openspec/changes/add-gallery-media-archive/design.md).
- O [checklist pós-deploy](post-deploy-configuration-checklist.md) estabelece a sequência: backup comprovado, arquivo/recuperação sintéticos na conta do proprietário e depois liberação de outros fotógrafos.
- O proprietário confirmou em 20/11 manter a retenção global de 7 diários / 4 semanais / 3 mensais. Ela não define o lifecycle da mídia nem autoriza expurgo de fotos.

## O que já funcionou e pode fundamentar a próxima etapa

| Prova | Resultado comprovado | Evidência e limite |
|---|---|---|
| Transporte real Drive, 17/11 | Upload retomável de texto sintético, conferência de metadados, download integral, SHA-256 e limpeza apenas dos objetos do ensaio | [Recibo de transporte](../../openspec/changes/add-google-drive-storage-foundation/production-drive-proof.md). Conta do proprietário e pasta temporária; não comprova acesso da futura identidade de mídia nem desempenho em lotes grandes. |
| Recuperação global pelo Drive, 17/11 | Pacote PostgreSQL sintético cifrado, readback idêntico, recusa de adulteração, autenticação GCM e restore em PostgreSQL descartável; dados e ownership conferidos | [Recibo de recuperação](../../openspec/changes/add-platform-backup-recovery/drive-restore-proof.md). Não usou o banco produtivo como origem/destino e não mede seu RTO. |
| Custódia e configuração operacional, 17/11 | Configuração root-only, cópia offline da chave e desafio autenticado entre os materiais de recuperação | [Tasks 1.1–1.2](../../openspec/changes/enable-platform-backup-runtime/tasks.md). Reutilizar o procedimento de custódia; a chave do pacote global não é automaticamente chave de mídia. |
| Publicação protegida e mount Picker, 20/11 | Suporte protegido instalado, configuração do Picker read-only somente na API e release API/web saudável de #395 | [Inventário e recibos](../../openspec/changes/enable-platform-backup-runtime/release-preflight.md). Não equivale à seleção/autorização da nova pasta nem ao timer ativo. |
| Integração Picker/console, 20/11 | Regressão reproduzida na revalidação de foco; seleção preservada com acesso positivo e descarte em recusa/logout; 38 testes UI e CI da PR #397 verdes | [Validação de foco e recibo de publicação](../../openspec/changes/enable-platform-backup-runtime/validation-picker-focus.md). Conferir nesse recibo o resultado do release e do reteste real; não repetir a hipótese de `ERROR` como causa confirmada. |

## Código comum a reutilizar

| Componente | Reuso concreto | Limite da reutilização |
|---|---|---|
| [google_drive_client.py](../../backend/app/google_drive_client.py) | `DriveTransport`, transporte HTTP e contratos OAuth/Drive existentes | Configurar a identidade e autorização próprias de mídia; não ampliar escopo ou copiar credenciais do backup por inferência. |
| [google_drive_storage.py](../../backend/app/google_drive_storage.py) | `upload_drive_file`, envio retomável, medição dos bytes, validação da resposta, receipts e `provider_failure_code` | Mapear os receipts ao objeto/ciclo de mídia; conservar idempotência e recusa de conteúdo divergente. |
| [platform_backup/workspace_store.py](../../backend/app/platform_backup/workspace_store.py) | Referência comprovada para streaming, leitura de retorno, tamanho/checksum e tratamento de erros do Drive | O store é especializado em artefatos globais cifrados e `BackupContext`. Reutilizar primitivas compatíveis; não substituir o contrato de mídia por um pacote de banco. Extração de helper comum exige consumidores e compatibilidade comprovados. |
| [platform_backup/workspace_credentials.py](../../backend/app/platform_backup/workspace_credentials.py) e [integration_secrets.py](../../backend/app/integration_secrets.py) | Padrões de acesso efêmero, credenciais cifradas, configuração externa e erros sanitizados | A factory do backup valida contexto owner-only específico. A mídia precisa de seu próprio vínculo autorizado; não chamar essa factory como atalho para outro contexto. |
| [Validações operacionais](../../openspec/changes/enable-platform-backup-runtime/release-preflight.md) | Método de inventário, fingerprint, revisão de escopo, CI do SHA exato, preservação de rollback e saúde pós-release | O release API/web não instala automaticamente outro worker, mount, identidade, segredo ou timer. Cada operação usa o gate já aprovado para seu escopo. |

## Núcleo de mídia já existente — começar por estes consumidores

| Código | Responsabilidade pronta que deve ser preservada |
|---|---|
| [media_archive_storage.py](../../backend/app/media_archive_storage.py) | Interface `MediaArchiveStorage`: `upload_object`, `read_object`, `download_object` e `delete_object`; fronteira para o adaptador real. |
| [media_archive_executor.py](../../backend/app/media_archive_executor.py) | `execute_archive_operation`, readback integral em `_verify_remote_object`, download conferido, promoção de staging e `execute_restore_operation`. |
| [media_archive_manifest.py](../../backend/app/media_archive_manifest.py) | Manifesto canônico com UUIDs, tamanhos, SHA-256, IDs remotos e validação da origem/destino pelos registros existentes. |
| [media_archive_worker.py](../../backend/app/media_archive_worker.py) e [media_archive_scheduler.py](../../backend/app/media_archive_scheduler.py) | Fila durável, claims, leases, checkpoints, transições e agendamento pelo lifecycle da mídia. |
| [media_archive_staging.py](../../backend/app/media_archive_staging.py) | Staging privado, orçamento de espaço por volume, reservas e publicação dos arquivos conferidos. |
| [media_archive_billing.py](../../backend/app/media_archive_billing.py) e [media_archive_notices.py](../../backend/app/media_archive_notices.py) | Reserva/débito idempotente após recuperação comprovada, isenção do proprietário e avisos do fluxo existente. |

## Sequência de implementação da ligação real

1. Ler a task 1.4, design/specs e evidências da change de arquivo. Conferir o runtime publicado e os consumidores acima antes de adicionar outra abstração.
2. Inventariar o adaptador disponível e completar a implementação de `MediaArchiveStorage` para Drive usando os helpers comuns. Reaproveitar contratos/fixtures; não reconstruir a fila, catálogo, manifesto ou recuperação.
3. Vincular identidade e raiz próprias de mídia; organizar subpastas por UUID de tenant/galeria/pasta/ciclo conforme o design. O vínculo no banco e a autorização no servidor são obrigatórios em cada operação; diretórios não são barreira de autorização.
4. Conectar o adaptador ao caller/agendamento existente, com limites de tamanho, tempo, quota e retentativas revisados. Preservar fila global, leases, estados incertos e reconciliação.
5. Executar o ensaio autorizado com galeria e JPEGs sintéticos do proprietário: upload, readback integral, manifesto/checksums e só então liberação dos bytes locais prevista pelo contrato. Recuperar os mesmos registros e conferir IDs, seleções, pedidos, prévias e histórico.
6. Provar retry/interrupção, recusa de tenant divergente, quota e espaço insuficientes, fonte/objeto ausente e resultado incerto. Não promover operação parcial a sucesso nem cobrar recuperação incompleta.
7. Registrar SHA, configuração não secreta, resultado, recibos e limites. Reconciliar o console com fontes duráveis comprovadas; concluir a task operacional somente após a evidência e o aceite previstos.

## Validação existente a aproveitar

- Drive: [test_google_drive_storage.py](../../backend/tests/test_google_drive_storage.py).
- Backup/Workspace: [test_platform_backup_workspace_store.py](../../backend/tests/test_platform_backup_workspace_store.py), [test_platform_backup_workspace_credentials.py](../../backend/tests/test_platform_backup_workspace_credentials.py) e [test_platform_backup_restore.py](../../backend/tests/test_platform_backup_restore.py).
- Mídia: [test_media_archive_executor.py](../../backend/tests/test_media_archive_executor.py), [test_media_archive_manifest.py](../../backend/tests/test_media_archive_manifest.py), [test_media_archive_worker.py](../../backend/tests/test_media_archive_worker.py), [test_media_archive_staging.py](../../backend/tests/test_media_archive_staging.py) e [test_media_archive_billing.py](../../backend/tests/test_media_archive_billing.py).

Reutilizar resultados quando código, dependências, configuração e ambiente relevantes permanecerem iguais. Mudança de identidade/pasta, transporte, formatos, limites, volumes ou runtime exige repetir as validações afetadas. A prova de texto/backup sintético fundamenta o transporte; a prova com mídia verifica o contrato adicional de múltiplos objetos e catálogo.

## O que permanece separado

- Backup global: pacote do banco/configuração, chave própria, restauração global, retenção 7/4/3 e serviço diário.
- Mídia: múltiplos objetos por tenant, manifesto/catálogo de galeria, staging, preservação dos registros e fluxo próprio de créditos/lifecycle.
- A recuperação lógica do banco de um único tenant continua em fase própria. A restauração global inclui o catálogo de mídia, mas não traz automaticamente seus bytes do Drive.
- A v1 de arquivo não habilita expurgo remoto de fotos por idade. A autorização de backup global não autoriza remover mídia ou operar outras contas/serviços.

Próxima ação após comprovar o backup global: retomar a task 1.4 do arquivo a partir deste mapa, começando pela fronteira `MediaArchiveStorage` e pelo transporte real já existente.
