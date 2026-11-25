# Reaproveitamento do backup global no arquivo de fotos

Registro de continuidade de 20/11/2026, solicitado pelo proprietário para evitar repetição de investigação, configuração e desenvolvimento na próxima etapa. Inventário de código na main `77cf2788` (PR #397). Este documento descreve evidência existente e pontos de integração; não autoriza novas operações remotas.

## Estado e fontes de verdade

- O transporte Drive e a recuperação global sintética possuem provas externas concluídas. A primeira cópia real no destino novo, a restauração de aceitação e a ativação do agendamento diário ainda dependem dos gates 3.2–3.3 de [enable-platform-backup-runtime](../../openspec/changes/enable-platform-backup-runtime/tasks.md).
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
| Integração Picker/console, 20/11 | Regressão reproduzida na revalidação de foco; seleção preservada com acesso positivo e descarte em recusa/logout; 38 testes UI, CI e release #397 aprovados, API/web saudáveis e HTTPS 200 | [Validação de foco e recibo de publicação](../../openspec/changes/enable-platform-backup-runtime/validation-picker-focus.md). Reteste real da seleção ainda pendente; não repetir a hipótese de `ERROR` como causa confirmada. |

## Código comum a reutilizar

| Componente | Reuso concreto | Limite da reutilização |
|---|---|---|
| [google_drive_client.py](../../backend/app/google_drive_client.py) | `DriveTransport`, transporte HTTP e contratos OAuth/Drive existentes | Configurar a identidade e autorização próprias de mídia; não ampliar escopo ou copiar credenciais do backup por inferência. |
| [google_drive_storage.py](../../backend/app/google_drive_storage.py) | `upload_drive_file`, envio retomável, medição dos bytes, validação da resposta, receipts e `provider_failure_code` | Mapear os receipts ao objeto/ciclo de mídia; conservar idempotência e recusa de conteúdo divergente. |
| [platform_backup/workspace_store.py](../../backend/app/platform_backup/workspace_store.py) | Referência comprovada para streaming, leitura de retorno, tamanho/checksum e tratamento de erros do Drive | O store é especializado em artefatos globais cifrados e `BackupContext`. Reutilizar primitivas compatíveis; não substituir o contrato de mídia por um pacote de banco. Extração de helper comum exige consumidores e compatibilidade comprovados. |
| [platform_backup/workspace_credentials.py](../../backend/app/platform_backup/workspace_credentials.py) e [integration_secrets.py](../../backend/app/integration_secrets.py) | Padrões de acesso efêmero, credenciais cifradas, configuração externa e erros sanitizados | A factory do backup valida contexto owner-only específico. A mídia precisa de seu próprio vínculo autorizado; não chamar essa factory como atalho para outro contexto. |
| [google_drive_media_archive_storage.py](../../backend/app/google_drive_media_archive_storage.py) | Adaptador `MediaArchiveStorage` exige token, raiz, tenant e transporte explícitos; a topologia aprovada é raiz → tenant → galeria → pasta → ciclo, com UUIDs e `appProperties` privadas. Busca de catálogo incompleta/ambígua falha fechado; bytes são baixados em streaming e falhas sanitizadas. Provas em [validation.md](../../openspec/changes/add-gallery-media-archive/validation.md). | O código não está ligado ao worker/runtime, não tem credencial/root configurados e só foi exercitado por transporte sintético. A raiz e identidade de mídia continuam separadas do backup global e aguardam o gate operacional 1.4. |
| [Validações operacionais](../../openspec/changes/enable-platform-backup-runtime/release-preflight.md) | Método de inventário, fingerprint, revisão de escopo, CI do SHA exato, preservação de rollback e saúde pós-release | O release API/web não instala automaticamente outro worker, mount, identidade, segredo ou timer. Cada operação usa o gate já aprovado para seu escopo. |

## Núcleo de mídia já existente — começar por estes consumidores

| Código | Responsabilidade pronta que deve ser preservada |
|---|---|
| [media_archive_storage.py](../../backend/app/media_archive_storage.py) | Interface `MediaArchiveStorage`: `upload_object`, `read_object`, `download_object` e `delete_object`; fronteira provider-neutral do adaptador sintético e do adaptador Drive local já implementado. |
| [media_archive_executor.py](../../backend/app/media_archive_executor.py) | `execute_archive_operation`, readback integral em `_verify_remote_object`, download conferido, promoção de staging e `execute_restore_operation`. |
| [media_archive_manifest.py](../../backend/app/media_archive_manifest.py) | Manifesto canônico com UUIDs, tamanhos, SHA-256, IDs remotos e validação da origem/destino pelos registros existentes. |
| [media_archive_worker.py](../../backend/app/media_archive_worker.py) e [media_archive_scheduler.py](../../backend/app/media_archive_scheduler.py) | Fila durável, claims, leases, checkpoints, transições e agendamento pelo lifecycle da mídia. |
| [media_archive_staging.py](../../backend/app/media_archive_staging.py) | Staging privado, orçamento de espaço por volume, reservas e publicação dos arquivos conferidos. |
| [media_archive_billing.py](../../backend/app/media_archive_billing.py) e [media_archive_notices.py](../../backend/app/media_archive_notices.py) | Reserva/débito idempotente após recuperação comprovada, isenção do proprietário e avisos do fluxo existente. |

## Sequência de implementação da ligação real

1. Ler as tasks 1.4a e 1.4, design/specs e evidências da change de arquivo. Conferir o runtime publicado e os consumidores abaixo antes de ligar qualquer adaptador.
2. Reutilizar `GoogleDriveMediaArchiveStorage` e seus testes sintéticos; não reconstruir o transporte, a fila, o catálogo, o manifesto ou a recuperação. O código provider-specific não está ligado ao runtime e nenhuma chamada real foi feita.
3. No gate pós-release 1.4, provisionar/verificar a identidade e a raiz próprias de mídia. O adaptador organiza pastas encadeadas por UUID de tenant, galeria, pasta e ciclo sob a raiz; `appProperties` privadas vinculam a hierarquia e o objeto à chave/manifesto. O vínculo no banco e a autorização no servidor continuam obrigatórios em cada operação; diretórios não são barreira de autorização.
4. Conectar o adaptador ao caller/agendamento existente, com limites de tamanho, tempo, quota e retentativas revisados. Preservar fila global, leases, estados incertos e reconciliação.
5. Executar o ensaio autorizado com galeria e JPEGs sintéticos do proprietário: upload, readback integral, manifesto/checksums e só então liberação dos bytes locais prevista pelo contrato. Recuperar os mesmos registros e conferir IDs, seleções, pedidos, prévias e histórico.
6. Provar retry/interrupção, recusa de tenant divergente, quota e espaço insuficientes, fonte/objeto ausente e resultado incerto. Não promover operação parcial a sucesso nem cobrar recuperação incompleta.
7. Registrar SHA, configuração não secreta, resultado, recibos e limites. Reconciliar o console com fontes duráveis comprovadas; concluir a task operacional somente após a evidência e o aceite previstos.

## Validação existente a aproveitar

- Drive: [test_google_drive_storage.py](../../backend/tests/test_google_drive_storage.py).
- Backup/Workspace: [test_platform_backup_workspace_store.py](../../backend/tests/test_platform_backup_workspace_store.py), [test_platform_backup_workspace_credentials.py](../../backend/tests/test_platform_backup_workspace_credentials.py) e [test_platform_backup_restore.py](../../backend/tests/test_platform_backup_restore.py).
- Mídia: [test_media_archive_executor.py](../../backend/tests/test_media_archive_executor.py), [test_media_archive_manifest.py](../../backend/tests/test_media_archive_manifest.py), [test_media_archive_worker.py](../../backend/tests/test_media_archive_worker.py), [test_media_archive_staging.py](../../backend/tests/test_media_archive_staging.py) e [test_media_archive_billing.py](../../backend/tests/test_media_archive_billing.py).

Reutilizar resultados quando código, dependências, configuração e ambiente relevantes permanecerem iguais. Mudança de identidade/pasta, transporte, formatos, limites, volumes ou runtime exige repetir as validações afetadas. A prova de texto/backup sintético fundamenta o transporte; a prova com mídia verifica o contrato adicional de múltiplos objetos e catálogo.

## Lições operacionais para evitar repetição

1. Uma pasta acessível pelo conector Drive pode não estar autorizada pelo OAuth do aplicativo. Conferir a autorização do app e o escopo mínimo antes de investigar o transporte ou criar outra integração Google.
2. No Picker, eventos intermediários de carregamento preservam a janela; os terminais são tratados explicitamente. Testar o retorno de foco com a página e sua revalidação de sessão, além do componente isolado. Preservar a segunda reautenticação e o descarte em perda de acesso.
3. Conferir os pins exatos do runtime e a lista nominal do gate antes do push. No caso #397, o hash Git de um helper causou um falso positivo de chave; a conferência do blob permitiu uma exceção por commit/path/regra/linha. Preservar os commits revisados quando o fingerprint depender deles; não generalizar a exceção.
4. O preflight remoto é somente leitura e não atualiza `origin/main`. Após um novo merge, a ref local desatualizada pode exigir a preparação pelo canal protegido, com CI de código e backups dos helpers. Confirmar invariância dos containers antes de repetir o preflight.
5. Uma falha operacional isolada não exige repetir testes verdes do mesmo SHA quando as premissas forem preservadas. Usar a repetição dos jobs falhos/dependentes pelo fluxo documentado; conferir novamente fingerprint, artefato e estado vivo antes da publicação.
6. Registrar a prova externa concluída e seu limite no recibo. Nova pasta, outra identidade ou operação com múltiplos objetos requerem sua própria validação; reaproveitar o código/procedimento comprovado e testar a diferença relevante.

## O que permanece separado

- Backup global: pacote do banco/configuração, chave própria, restauração global, retenção 7/4/3 e serviço diário.
- Mídia: múltiplos objetos por tenant, manifesto/catálogo de galeria, staging, preservação dos registros e fluxo próprio de créditos/lifecycle.
- A recuperação lógica do banco de um único tenant continua em fase própria. A restauração global inclui o catálogo de mídia, mas não traz automaticamente seus bytes do Drive.
- A v1 de arquivo não habilita expurgo remoto de fotos por idade. A autorização de backup global não autoriza remover mídia ou operar outras contas/serviços.

Próxima ação após comprovar o backup global: retomar a task 1.4 do arquivo para provisionar/verificar identidade, raiz, permissões e limites, e só então executar o ensaio real do proprietário. O adaptador local da task 1.4a e suas provas sintéticas devem ser reaproveitados, sem repetir a implementação do zero.

## Preparação local da composição — 24/11/2026

A change `compose-media-archive-worker-storage` acrescenta composição exclusivamente sintética ao dispatcher existente: `SyntheticMediaArchiveBinding` declara tenant selecionado, tenant do storage, raiz `synthetic:`, namespace e finalidade; configuração divergente recusa antes de descoberta/claim. Descoberta de avisos/ciclos e claim recebem o mesmo filtro opcional por tenant. Lease global fora do tenant permanece intacto e impede retomada pelo piloto; callers sem filtro preservam o comportamento anterior.

Essa declaração de fixture não autentica o proprietário nem comprova OAuth, acesso, quota ou custódia. A decisão de identidade Workspace dedicada distinta da conta/credencial de backup e raiz própria continua obrigatória. Nenhuma factory Google é selecionada ou conectada por esse trabalho. O futuro binding operacional exige o gate próprio da task 1.4; não usar esse binding sintético como evidência de autorização real.

Após revisão da durabilidade, o loop sem argumento permanece totalmente fechado e o configurador recusa qualquer storage/binding sintético. O slot legado não é selecionado. Composição em memória é exclusiva da chamada direta do harness local com SessionLocal/raízes descartáveis; em production até a chamada direta é recusada antes de claim/cleanup. Metadados da fixture não provam identidade nem durabilidade. A futura ativação exige contrato e vínculo operacional durável aprovados no gate próprio.
