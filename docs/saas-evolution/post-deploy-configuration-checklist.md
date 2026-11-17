# Checklist de configuração após o deploy SaaS

Atualizado em 16/11/2026. Solicitação do proprietário: reunir as configurações deliberadamente deixadas para quando o candidato estiver no servidor, incluindo Drive e backup por tenant. Este documento acompanha o release; as tarefas abaixo não voltam a ser requisitos do primeiro push, que já ocorreu.

`[x]` indica uma decisão registrada ou uma prova executada, conforme o texto do item. `[ ]` indica trabalho pendente. Cada item identifica configuração, ensaio, implementação ou decisão comercial. Uma fundação validada localmente não equivale a serviço recorrente instalado.

O estágio inicial após o deploy fica restrito ao proprietário. As provas reais de Drive, backup/restauração e arquivo/recuperação precedem a liberação do SaaS para outros tenants, conforme as decisões já registradas. O keyring TOTP e o corte compatível de API/workers são pré-requisitos técnicos do deploy e continuam no [plano de release](../../openspec/changes/add-photographer-signup-portal/production-release-readiness.md).

## 1. Decisões recuperadas e proteções já comprovadas

- [x] **Deploy do proprietário** com runtime 9df3b735, schema 0126 e 13 serviços saudáveis, dados/fator TOTP/índices preservados e integrações conferidas. Evidências e limites no [registro do release](production-release-2026-11-16.md).
- [x] **Custódia TOTP** em arquivo root-only no servidor e cópia externa escolhida pelo proprietário em D:, com recuperação validada. A guarda offline física permanece sob responsabilidade do proprietário.

- [x] **Decisão:** configurar e testar Drive/backup/arquivo após o release restrito ao proprietário, antes de liberar outros tenants.
- [x] **Decisão:** backup inicial global diário, retenção de 7 diários/4 semanais/3 mensais; RPO alvo de 24 h e RTO alvo de 8 h, a medir; ensaio mensal de restauração.
- [x] **Decisão:** conta do proprietário somente no ensaio inicial; identidade Workspace dedicada para a rotina de backup. Arquivo de fotos terá identidade e raiz próprias, separadas da cópia do banco.
- [x] **Decisão:** fidelidade e revisão jurídica futura ficaram para depois do primeiro release; nenhuma regra de fidelidade foi aprovada por inferência.
- [x] **Prova de preparação do release:** backup online de 16/11 restaurado em banco isolado; cadeia `0090→0126` ensaiada nessa cópia, preservando os registros financeiros comparados e o fator TOTP. Isso não comprova backup recorrente nem cópia no Drive.

Fontes: [D15–D17](decisions.md#decisões-de-backup-de-06112026), [gates pós-release](candidate-validation-2026-11-03.md), [recibo do ensaio](../../openspec/changes/add-photographer-signup-portal/production-release-readiness.md).

## 2. Google Drive / Workspace no servidor

- [ ] **Configuração no Google Cloud:** conferir o cliente OAuth Web já criado, Drive API, audience, titularidade e custodiante; recuperar as credenciais pelo store seguro, sem recriar a integração por padrão.
- [x] **Custódia OAuth no runtime:** armazenar o JSON do cliente Web em `/etc/pyp-google-drive/oauth-client.json` (`root:root`, modo `0400`, diretório `root:root`/`0700`), montar somente na API em `/run/secrets/google-drive-oauth-client.json` como read-only e remover as três variáveis `GOOGLE_DRIVE_*` do metadata de todos os containers. Merge e recibo em 17/11/2026; nenhum valor de credencial é registrado nesta checklist.
- [ ] **Configuração:** validar publicamente o callback `/api/admin/platform/drive/oauth/callback`, HTTPS, origem e correspondência com o URI autorizado no Google.
- [ ] **Consentimento do proprietário:** revisar a tela Google e aprovar somente o escopo `drive.file`; depois confirmar refresh token cifrado e reautorização/revogação. O fluxo ainda não foi iniciado e aguarda o consentimento explícito.
- [ ] **Configuração:** escolher o destino concreto — pasta em My Drive ou Shared Drive — e comprovar acesso, permissões herdadas, quota disponível e limites do serviço.
- [ ] **Ensaio:** enviar arquivo sintético, conferir metadata/checksum, ler novamente e baixar; registrar contagens/IDs técnicos e resultado, sem tokens ou conteúdo pessoal.
- [ ] **Configuração:** cadastrar a identidade Workspace dedicada da rotina e definir custódia/recuperação das credenciais; conferir independência em relação ao servidor de origem.

Fontes: [configuração OAuth](../../openspec/changes/add-google-drive-storage-foundation/configuration-inventory.md), [operação Drive](../../openspec/changes/add-google-drive-storage-foundation/operations.md), tasks 1.1/3.1 da [fundação Drive](../../openspec/changes/add-google-drive-storage-foundation/tasks.md).

## 3. Backup do banco e configuração solicitada por tenant

O escopo inicial aprovado é PostgreSQL completo e configurações essenciais cifradas, com recuperação global. Backup/recuperação lógica individual por tenant foi faseado para etapa própria. A organização de fotos em subpastas por UUID de tenant pertence ao arquivo de mídia, na seção 4. O pedido atual de backup por tenant fica explicitamente rastreado abaixo, sem declarar uma capacidade individual já entregue.

- [ ] **Configuração:** definir a pasta externa de backup do banco e manter sua identidade/raiz separadas do arquivo de fotos.
- [ ] **Configuração:** provisionar material de cifragem/recuperação no store aprovado; guardar cópia offline sob custódia do proprietário e versões de chave necessárias aos backups retidos.
- [ ] **Ensaio:** executar backup → upload → readback → autenticação criptográfica → restore global em destino descartável, usando primeiro a conta do proprietário.
- [ ] **Implementação:** integrar e publicar o caller/worker/scheduler produtivo de backup. A fundação e o adapter Workspace existentes não instalam a rotina de produção; não usar flags de teste para contornar esse limite.
- [ ] **Configuração, após o caller:** definir horário/fuso e habilitar a rotina diária somente para o projeto Pick-your-Pic, preservando timers e cópias dos demais projetos do servidor.
- [ ] **Ensaio:** comprovar cópia recorrente e retry idempotente com a identidade dedicada; falha ou estado desconhecido deve ficar visível.
- [ ] **Configuração/ensaio:** aplicar a retenção global 7/4/3 com preservação do último ponto recuperável; só descartar cópia após existir outra independente e restaurável.
- [ ] **Configuração/ensaio:** agendar e registrar o restore mensal, medir RPO/RTO efetivos e comprovar recuperação com as chaves correspondentes ao snapshot.
- [ ] **Implementação — backup por tenant:** definir e implementar o recorte de dados, dependências compartilhadas, cifragem, destino e restauração seletiva preservando IDs, vínculos e histórico financeiro; testar isolamento antes de oferecer essa capacidade.
- [ ] **Ensaio — backup por tenant:** comprovar restauração do tenant em ambiente separado, sem alterar outros tenants nem restaurar sobre a base produtiva ativa.
- [ ] **Implementação/configuração:** alimentar o console do proprietário com fonte durável do último backup, cópias verificadas, falhas, idade e restore comprovado.

Fontes: [política aprovada](../../openspec/changes/add-platform-backup-recovery/policy-decision-draft.md), [alcance e limites da fundação](platform-backup-local.md), [tasks 4.2–4.4 Workspace](../../openspec/changes/add-google-workspace-backup-copy/tasks.md), [console, task 2.7](../../openspec/changes/add-platform-owner-console/tasks.md).

## 4. Arquivo de fotos e recuperação por tenant no Drive

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
