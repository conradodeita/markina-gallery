# Checklist de configuração após o deploy SaaS

> **Registro histórico, substituído em 25/11/2026.** As tarefas de Picker, runtime próprio, chave do backup e instalação do timer abaixo descrevem a tentativa aposentada e não são mais executáveis. Consulte [`retire-platform-backup-runtime`](../../openspec/changes/retire-platform-backup-runtime/tasks.md) para a higienização e [`prove-open-source-backup-and-recovery`](../../openspec/changes/prove-open-source-backup-and-recovery/tasks.md) para a prova nova. O fluxo de arquivo frio do fotógrafo continua vigente; sua integração com ferramentas deve seguir a prova nova, preservando o contrato de prazo/crédito.

Atualizado em 17/11/2026. Solicitação do proprietário: reunir as configurações deliberadamente deixadas para quando o candidato estiver no servidor, incluindo Drive e backup por tenant. Este documento acompanha o release; as tarefas abaixo não voltam a ser requisitos do primeiro push, que já ocorreu.

`[x]` indica uma decisão registrada ou uma prova executada, conforme o texto do item. `[ ]` indica trabalho pendente. Cada item identifica configuração, ensaio, implementação ou decisão comercial. Uma fundação validada localmente não equivale a serviço recorrente instalado.

O estágio inicial após o deploy fica restrito ao proprietário. As provas reais de Drive, backup/restauração e arquivo/recuperação precedem a liberação do SaaS para outros tenants, conforme as decisões já registradas. O keyring TOTP e o corte compatível de API/workers são pré-requisitos técnicos do deploy e continuam no [plano de release](../../openspec/changes/add-photographer-signup-portal/production-release-readiness.md).

## 1. Decisões recuperadas e proteções já comprovadas

- [x] **Deploy do proprietário** com runtime 9df3b735, schema 0126 e 13 serviços saudáveis, dados/fator TOTP/índices preservados e integrações conferidas. Evidências e limites no [registro do release](production-release-2026-11-16.md).
- [x] **Custódia TOTP** em arquivo root-only no servidor e cópia externa escolhida pelo proprietário em D:, com recuperação validada. A guarda offline física permanece sob responsabilidade do proprietário.

- [x] **Decisão:** configurar e testar Drive/backup/arquivo após o release restrito ao proprietário, antes de liberar outros tenants.
- [x] **Decisão:** backup inicial global diário, retenção de 7 diários/4 semanais/3 mensais; RPO alvo de 24 h e RTO alvo de 8 h, a medir; ensaio mensal de restauração.
- [x] **Decisão de 17/11:** a conta Workspace do proprietário já conectada será usada para a rotina de backup global. Arquivo de fotos mantém identidade e raiz próprias, separadas da cópia do banco.
- [x] **Decisão:** fidelidade e revisão jurídica futura ficaram para depois do primeiro release; nenhuma regra de fidelidade foi aprovada por inferência.
- [x] **Prova de preparação do release:** backup online de 16/11 restaurado em banco isolado; cadeia `0090→0126` ensaiada nessa cópia, preservando os registros financeiros comparados e o fator TOTP. Isso não comprova backup recorrente nem cópia no Drive.

Fontes: [D15–D17](decisions.md#decisões-de-backup-de-06112026), [gates pós-release](candidate-validation-2026-11-03.md), [recibo do ensaio](../../openspec/changes/add-photographer-signup-portal/production-release-readiness.md).

## 2. Google Drive / Workspace no servidor

- [ ] **Configuração no Google Cloud:** conferir o cliente OAuth Web já criado, Drive API, audience, titularidade e custodiante; recuperar as credenciais pelo store seguro, sem recriar a integração por padrão.
- [x] **Custódia OAuth no runtime:** armazenar o JSON do cliente Web em `/etc/pyp-google-drive/oauth-client.json` (`root:root`, modo `0400`, diretório `root:root`/`0700`), montar somente na API em `/run/secrets/google-drive-oauth-client.json` como read-only e remover as três variáveis `GOOGLE_DRIVE_*` do metadata de todos os containers. Merge e recibo em 17/11/2026; nenhum valor de credencial é registrado nesta checklist.
- [ ] **Configuração do Google Picker:** habilitar a Picker API no mesmo projeto e criar uma chave de navegador com restrição de referer para `https://markina.pickyourpic.com.br/*` e `https://docs.google.com/*`, limitada às APIs Google Picker e Drive. Guardar a configuração em `/etc/pyp-google-drive/picker-config.json` (`root:root`, modo `0400`, diretório `root:root`/`0700`) e montá-la somente na API, read-only, em `/run/secrets/google-drive-picker-config.json`. O arquivo contém `developer_key`, `project_number` e `expected_parent_folder_id`; não incluir valores no Git nem no bundle frontend. Enquanto faltar, o seletor deve permanecer indisponível e o backup desligado.
- [x] **Callback OAuth em produção.** HTTPS e proteção sem sessão confirmados em `/api/admin/platform/drive/oauth/callback`. O runtime conferiu o URI da configuração e a conexão manual completou o callback em 17/11/2026.
- [x] **Consentimento do proprietário.** Conexão concluída manualmente em Plataforma. Às `19:48:59 UTC`, a API registrou `connected`, escopo `drive.file`, refresh token em envelope cifrado e evento de auditoria. [Recibo](../../openspec/changes/add-google-drive-owner-connect-ui/deployment.md#conexão-confirmada-em-17112026).
- [x] **Quota do Drive no ensaio do proprietário.** A API Google retornou 100 TiB de limite e aproximadamente 90,31 TiB disponíveis em 17/11/2026. [Evidência](../../openspec/changes/add-google-drive-storage-foundation/production-drive-proof.md).
- [x] **Destino inicial do backup global:** `Meu Drive / Pick-your-Pic Tenants` foi criada e verificada na raiz pela conexão do app. Permanece intacta, mas foi substituída como destino pretendido pela decisão abaixo. [Recibo](../../openspec/changes/add-google-drive-storage-foundation/production-drive-proof.md#destino-da-rotina-verificado).
- [x] **Organização aprovada em 17/11:** preservar `Oracle-Production-Backups/Pick-your-Pic`, usada pelo timer compartilhado e com cópias existentes; manter como irmãs as pastas `Pick-your-Pic Global` e `Pick-your-Pic Tenants`. As duas novas pastas estão vazias e foram verificadas pelo conector Google Drive. A raiz global será usada para o banco; a raiz Tenants fica reservada a UUIDs futuros. Nenhuma cópia existente foi movida ou renomeada.
- [x] **Seleção e autorização pelo app:** o proprietário selecionou `Oracle-Production-Backups/Pick-your-Pic Global` no Picker e concluiu a segunda autorização com o escopo atual `drive.file`; a UI confirmou a pasta. O acesso do conector Google Drive não foi usado como prova do OAuth Pick-your-Pic. [Reteste](../../openspec/changes/enable-platform-backup-runtime/validation-picker-focus.md#continuidade-solicitada-pelo-proprietário).
- [ ] **Vínculo protegido:** gravar somente o ID autorizado na configuração root-only, mantendo `enabled=false`. Ainda pendente; exige instalador/canal de operador protegido descrito no recibo [operacional](../../openspec/changes/enable-platform-backup-runtime/validation-picker-focus.md#lacuna-do-executor-operacional).
- [x] **Ensaio em pasta privada temporária.** Upload retomável, conferência dos metadados, download e SHA-256 do texto sintético aprovados. Arquivo e pasta excluídos e ausência confirmada. [Recibo](../../openspec/changes/add-google-drive-storage-foundation/production-drive-proof.md#ensaio-com-pasta-temporária-concluído).
- [ ] **Configuração:** vincular a rotina ao acesso protegido da conta Workspace escolhida e definir a recuperação da credencial diante de perda do servidor de origem.

Fontes: [configuração OAuth](../../openspec/changes/add-google-drive-storage-foundation/configuration-inventory.md), [operação Drive](../../openspec/changes/add-google-drive-storage-foundation/operations.md), tasks 1.1/3.1 da [fundação Drive](../../openspec/changes/add-google-drive-storage-foundation/tasks.md).

## 3. Backup global, restauração seletiva e recuperação de pasta fria

> A tentativa própria de backup global via Google Workspace foi encerrada em 25/11/2026. Os itens antigos deste checklist foram retirados porque descreviam um runtime e workflows aposentados.

A direção atual é a prova sintética integrada da change [prove-open-source-backup-and-recovery](../../openspec/changes/prove-open-source-backup-and-recovery/proposal.md): backup global cifrado do PostgreSQL, extração isolada de um fotógrafo e arquivo/recuperação de pasta fria pelo fluxo existente, avaliando Restic e Rclone (Backrest opcional). Nenhuma dessas provas autoriza produção, uso de dados de clientes ou configuração real do Drive.

Não retomar as changes enable-platform-backup-runtime, prepare-platform-backup-source ou add-google-workspace-backup-copy. A retirada de arquivos do servidor segue [retire-platform-backup-runtime](../../openspec/changes/retire-platform-backup-runtime/tasks.md) pelo workflow protegido, sem SQL, migration, Compose ou restart.

O contrato de pasta fria preserva a janela de 30 dias antes do arquivo. Novas recuperações do fotógrafo concedem 30 dias a partir da disponibilização íntegra, com andamento na tela e débito somente após a conclusão. Veja [a decisão de prazo fixo](../../openspec/changes/fix-cold-recovery-access-window/proposal.md). A taxa por pasta e ciclo, a reconciliação, a isenção do proprietário e a ausência de expurgo automático seguem o contrato existente.
## 4. Arquivo de fotos e recuperação por tenant no Drive

Antes de implementar a ligação real, consultar o [mapa de reuso do backup global e do núcleo de mídia existente](backup-global-reuso-arquivo-midia.md), com código, provas concluídas e pontos de integração para evitar repetição de trabalho.

- [ ] **Configuração:** provisionar a identidade Workspace e a pasta-raiz dedicadas à mídia, conforme decisão já tomada; verificar permissões, quota e separação em relação ao backup do banco.
- [ ] **Configuração:** criar/verificar a subpasta do proprietário por UUID de tenant e o vínculo autenticado de cada operação; a hierarquia de pastas não substitui autorização no backend.
- [ ] **Configuração:** definir staging privado no servidor, fora das raízes servidas; conferir espaço livre, reservas, permissões, tamanhos, timeout e retentativas.
- [ ] **Implementação/configuração:** selecionar e ligar o transporte real de arquivo/recuperação ao runtime, preservando verificação integral, idempotência e reconciliação; o adapter sintético não prova essa ligação.
- [ ] **Ensaio:** usar galeria/pasta e JPEGs sintéticos do proprietário para testar expiração + janela de 30 dias, bloqueio por pedido, upload para o Drive e readback completo antes de retirar bytes da origem.
- [ ] **Ensaio:** recuperar a mesma mídia, conferir checksums, IDs, seleções, pedidos, prévias e histórico; validar retomada e estado incerto, sem duplicar registros.
- [ ] **Decisão/configuração:** definir a taxa global de recuperação em créditos no console; o campo começa sem preço. Validar preço congelado no pedido, reserva, débito único após recuperação comprovada e isenção do proprietário.
- [ ] **Ensaio:** verificar avisos exclusivos ao fotógrafo, histórico e retries; não habilitar expurgo remoto automático da mídia arquivada na v1.

Fonte: task 1.4 **pós-release/pré-tenants** e contratos da [change de arquivo](../../openspec/changes/add-gallery-media-archive/tasks.md), [decisão de identidade/raiz e piloto](../../openspec/changes/add-gallery-media-archive/design.md).

## 5. Domínios, TLS, e-mail e cadastro público

- [ ] **Configuração/ensaio:** revalidar o wildcard DNS criado em 08/11, raiz e domínio atual; concluir certificado e rota wildcard com renovação verificável, preservando o atendimento em `markina.pickyourpic.com.br`.
- [ ] **Ensaio:** conferir um hostname sintético de tenant, HTTPS, roteamento, reserva/ativação do hostname e recusa de hosts desconhecidos ou pertencentes a outro tenant.
- [ ] **Configuração:** alinhar origens públicas, cookies, CORS e callback OAuth aos domínios efetivamente publicados.
- [ ] **Configuração:** recuperar as chaves do widget Turnstile já criado, `Pick-your-Pic — Cadastro de fotógrafos`, Managed, hostname `pickyourpic.com.br`, sem pre-clearance; instalar as chaves no store da aplicação.
- [ ] **Configuração/ensaio:** validar `EMAIL_PROVIDER`, `EMAIL_CREDENTIAL_ENV`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_ADDRESS` e TLS/timeout, preservando a configuração existente e o contexto `production`.
- [ ] **Ensaio:** testar e-mail real para destinatário sintético controlado: entrega, OTP, expiração, rate limit e recuperação; conferir falha segura do Turnstile sem provisionamento de conta.
- [ ] **Implementação/configuração/ensaio:** promover formalmente o gate de prova local para ativação produtiva após as provas anteriores e os gates Drive/backup/arquivo; então habilitar as flags revisadas e verificar cadastro automático por e-mail + MFA. O código atual mantém essas rotas em404 com `APP_ENV=production`; `PHOTOGRAPHER_SIGNUP_LOCAL_PROOF_ENABLED` não é um interruptor de produção e não deve ser usado para contornar essa etapa. O fluxo aprovado não prevê aprovação manual de cada cadastro pelo console.

Fontes: [signup, task 5.1](../../openspec/changes/add-photographer-signup-portal/tasks.md), [ingress por subdomínio](../../openspec/changes/enable-tenant-subdomain-ingress/tasks.md).

## 6. Pacotes de créditos, pagamentos e configuração de cada fotógrafo

- [ ] **Decisão/configuração:** definir nomes, quantidades, preços, moeda e condições dos pacotes de créditos; ativar apenas os pacotes escolhidos, sem preços padrão inventados.
- [ ] **Ensaio:** preservar a carteira ilimitada do proprietário e validar compra de crédito de tenant sintético, saldo, consumo e replay idempotente.
- [ ] **Configuração/ensaio:** conferir a conta recebedora do proprietário já escolhida para Mercado Pago, webhook, assinatura, URLs e ambiente; preservar as contas e vendas existentes.
- [ ] **Ensaio/configuração:** validar a rotina de estorno/chargeback e revisão manual, conforme política já registrada, sem apagar ledger nem debitar automaticamente créditos consumidos.
- [ ] **Configuração por novo tenant:** completar perfil, verificação de e-mail/MFA, aceite dos Termos vigentes, PIX e canal WhatsApp antes de liberar seus uploads. O onboarding novo não deve impor um cadastro retroativo ao proprietário legado.
- [ ] **Ensaio por novo tenant:** conferir instância Evolution/binding, pareamento, webhook e isolamento do canal; preservar a sessão do proprietário, PIX e configurações existentes, sem mensagens a clientes reais no piloto.

Fontes: [decisões comerciais](decisions.md), [onboarding](../../openspec/changes/add-photographer-signup-portal/design.md), [console](../../openspec/changes/add-platform-owner-console/tasks.md).

## 7. Termos, retenção e operação contínua

- [ ] **Configuração:** revisar o rascunho editável, dados do operador/contato e condições comerciais escolhidas; publicar a primeira versão dos Termos com hash e aceite versionado.
- [ ] **Decisão/configuração:** fechar os prazos e exceções ainda pendentes de dados biométricos, mídia, logs técnicos e atendimento aos titulares; refletir somente decisões aprovadas na configuração e no texto.
- [ ] **Ensaio/configuração:** preservar a decisão de não expurgar automaticamente perfil operacional de cliente por inatividade e a política temporária de não expurgo automático do histórico financeiro/auditoria; remoções continuam explícitas e auditadas.
- [ ] **Configuração/ensaio:** verificar filas/leases, espaço, quota externa, saúde das integrações e fonte de alertas no console; ausência de fonte ou observação antiga permanece desconhecida.
- [ ] **Ensaio:** conferir reconhecimento facial em `APP_ENV=production`, com `FACIAL_PROCESSING_ENABLED=true`, índices preservados e a jornada autorizada; não reindexar por inferência.
- [ ] **Ensaio/configuração:** validar encerramento, reabertura, retenção e exclusão auditada somente com tenant/mídia sintéticos, incluindo remoção remota quando a capacidade estiver implementada.
- [ ] **Revisão futura:** realizar a revisão jurídica já adiada e reconciliar controlador/operador e suboperadores com o inventário operacional. Essa revisão não foi transformada em bloqueio novo do primeiro release.

Fontes: [matriz de retenção](../../openspec/changes/add-photographer-signup-portal/retention-privacy-matrix.md), [tasks 6.1/6.2](../../openspec/changes/add-photographer-signup-portal/tasks.md), [encerramento de conta](../../openspec/changes/add-photographer-account-closure/tasks.md).

## 8. Fidelidade após o primeiro release

- [ ] **Decisão:** definir eventos elegíveis, conversão, benefícios, validade e tratamento de reembolso/chargeback.
- [ ] **Implementação:** concluir schema, ledger, regras e interfaces da change de fidelidade; validar concorrência e isolamento antes de ativar.
- [ ] **Configuração/ensaio:** configurar somente as regras aprovadas e ligar as views do console depois da implementação. Atualmente não há uma funcionalidade de fidelidade pronta que dependa apenas de configuração no servidor.

Fonte: [adiamento explícito](../../openspec/changes/add-owner-configurable-loyalty/proposal.md), [tasks de fidelidade](../../openspec/changes/add-owner-configurable-loyalty/tasks.md).

## Registro de conclusão

Ao marcar um item, registrar data UTC, ambiente, SHA/imagem quando aplicável, local da evidência e resultado. Registrar somente IDs técnicos, contagens e estados; manter credenciais, dumps, conteúdo de fotos e dados pessoais fora deste documento e do Git. Os comprovantes do backup preparatório de 16/11 ficam separados das provas futuras do backup recorrente e do Drive.
