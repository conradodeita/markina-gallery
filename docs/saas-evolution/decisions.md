# Decisões e dependências do proprietário

Atualizado em 03/11/2026. Observações de baseline abaixo são históricas; decisões substitutivas ao final prevalecem.

## Decisões aplicadas

- **D01 — Base de código:** usar o `main` remoto atual (`6af538…`, PR #351), que está seis commits à frente da API de produção (`74f613…`); confirmar igualdade entre `git ls-remote` e `origin/main`. O checkout sujo e o HEAD do repositório no servidor (`0dd015a…`) não são bases de implementação.
- **D02 — Divergência de runtime:** registrar separadamente os 3 módulos da API e os 9 do worker divergentes de `main`; não copiar arquivos de runtime nem reduzir capacidade de `main`. Antes de release, testar compatibilidade entre versões da API e worker, inclusive o limite de prévia 75/100.
- **D03 — Continuidade de multitenancy:** reutilizar a change ativa `add-small-multi-photographer-pilot` e sua matriz de ownership; não recriar sua análise nem interpretar 31 tarefas como aceite das quatro restantes.
- **D04 — Escopo operacional:** esta autorização cobre implementação local isolada e validação sintética. Não cobre deploy, alteração de produção/homologação, credenciais, compras financeiras reais ou eliminação de dados.
- **D05 — MFA de recuperação:** códigos aleatórios de 144 bits usam seletor público indexável e hash Argon2id apenas do restante secreto; regenerar exige senha e passo TOTP ainda não consumido. A alternativa de recuperar com outro código foi rejeitada porque poderia consumir o último fator de recuperação e conflita com o requisito de TOTP recente.
- **D06 — Segurança do Alembic URL:** escapar `%` ao inserir a URL no ConfigParser evita falha com credenciais percent-encoded; a URL entregue ao SQLAlchemy mantém o valor original.
- **D07 — Gate de compatibilidade TOTP:** `0091` adiciona envelope sem alterar plaintext legado; dual-write só é ligado durante janela explicitamente inventariada; `0093` limpa plaintext após consumidores drenados e validação/reconciliação. PostgreSQL isolado provou ORM legado/new runtime e downgrade. A publicação continua bloqueada até revisão do worker/runtimes ativos, backup/restore, rollout coordenado e autorização operacional.
- **D08 — Reenvio deliberado idêntico:** em 01/11/2026, o proprietário decidiu que selecionar novamente os mesmos bytes JPEG para a mesma pasta é uma operação nova. A UI apresenta um aviso por seleção com a quantidade e o possível débito; confirmar inclui as repetidas como novas intenções, e cancelar ignora somente essas fotos e envia o conteúdo novo. Cada nova intenção recebe UUID próprio; retry/replay/reindex preserva a identidade anterior. O tenant ilimitado do proprietário não debita créditos.

## Evidência local da Fase 2

- O código atual separa registro do item, recepção do JPEG durável e geração assíncrona de derivados. `write_source` usa staging, `fsync` e rename atômico; a transação do banco não é atômica com o filesystem. O retry HTTP automático é limitado a 503 e a identidade atual do arquivo usa o ID da foto e fingerprint, não uma chave de operação financeira.
- O worker pode falhar depois que o JPEG foi guardado; por isso a cobrança futura deve distinguir êxito de armazenamento de falha posterior de prévia. A recuperação de falha entre rename e commit precisa ser especificada antes de ativar consumo.
- `MercadoPagoPayment`/`MercadoPagoWebhook` e `SaleOrder`/`SaleOrderItem` representam compra de fotos por cliente. A infraestrutura existente pode ser reutilizada em fase própria, mantendo separadas compra de créditos e venda de fotos.
- `InstallationOperator` autoriza diagnóstico técnico. A capability publicada é somente `capacity_diagnostics`; não foi encontrada autorização comercial global em vigor.
- A inspeção do baseline foi somente leitura e não executou compra, upload de cliente ou escrita em ambiente remoto.
- O checkout Orders atual cria pagamento para uma cliente pagar pedidos de fotos ao fotógrafo tenant. Não prova, sozinho, um meio de receber o pagamento do fotógrafo para a plataforma.
- `add-mercadopago-credit-purchases` propõe ordem de crédito própria e reaproveitamento seletivo de cliente/validação Orders; não reutiliza a conta/webhook tenant como recebedor global por inferência.
- Busca delimitada de fidelidade em backend, migrations, frontend e specs principais não localizou regras, ledger ou UI. `add-owner-configurable-loyalty` mantém pontos e créditos separados e nenhuma regra ativa por padrão.

## Evidência local da Fase 5 — painel global

- `PlatformOwner` é ligado a `AdminUser` por UUID e verificação persistida; `MonitorGrant` cobre métricas/árvore/incidentes/export, enquanto `InstallationOperator` expõe `capacity_diagnostics`. Essas capacidades permitem diagnóstico técnico, não gestão comercial global.
- O monitor existente lê métricas sanitizadas de jobs, filas, disco e incidentes; não apresenta diretório comercial de tenants, compra de créditos, arquivo Drive ou restauração. `provision_photographer.py` é CLI offline com dry-run padrão, não uma UI de onboarding global.
- `Tenant.status` admite ativo/suspenso, mas não foi localizada rota/tela global de suspensão. `AuditEvent` registra evento, assunto, tenant e data, sem resultado/origem estruturados para cada ação administrativa global.
- `add-platform-owner-console` preserva grants técnicos e registra como pendentes autorização comercial, onboarding sem compartilhamento de credenciais, efeito da suspensão em pagamentos/jobs, escopo mínimo de dados e fontes confiáveis de backup/Drive.

## Evidência local das Fases 6–8 — Drive, backup e ciclo de vida

- Busca limitada aos arquivos de runtime `backend/app` e `frontend/app`, Compose e configuração de exemplo não encontrou cliente Drive/API. `GOOGLE_DRIVE_FOLDER_ID` aparece apenas comentado em `.env.example:145`. `backend/app/order_delivery.py` e `frontend/app/admin/payments/order-delivery.tsx` tratam uma URL HTTPS inserida pelo fotógrafo como entrega de pedido; não fazem upload, validação remota, arquivo ou backup.
- O Compose liga API/worker a volumes locais de origem, derivados e histórico e não declara serviço Drive/backup. `backend/app/worker.py` percorre filas e limpezas periódicas, sem job SaaS de backup identificado. Isso é evidência do repositório; cron/timers externos, catálogo e configuração real de produção continuam desconhecidos.
- `scripts/deploy-homolog.sh` e `scripts/deploy-prod-infinitepay-retirement.sh` fazem dumps PostgreSQL de operações específicas de release/migration; há manifesto/checksum e `pg_restore --list` em alguns fluxos. Isso não prova frequência diária, criptografia do backup integral, cópia externa, recuperação lógica de tenant ou restauração de cada conjunto. O diretório e o catálogo de backups reais não foram inspecionados.
- A expiração de seleção, renovação e pedido/aprovação de reabertura existem, mas a aprovação aceita qualquer prazo futuro e não impõe janela de 30 dias para arquivamento. A operação `delete_parent_gallery` prepara manifesto, preserva histórico comercial mínimo e remove mídias operacionais locais; após começar a remoção física, a API não aceita cancelar/restaurar. `commercial_retention.py` expurga mídia histórica de pedido segundo configuração explícita, sem arquivar originais no Drive.
- A mudança ativa `improve-gallery-and-client-data-lifecycle` excluiu “arquivo frio” de seus objetivos. O documento atual requer arquivamento após expiração; a nova proposta `add-gallery-media-archive` supersede essa exclusão somente para o fluxo automático, sem alterar prévias locais ou a exclusão explícita. A implementação precisa usar state machine independente e só remover o primário após prova de recuperação.
- Documentação oficial consultada em 31/10/2026: [escopos OAuth do Drive](https://developers.google.com/workspace/drive/api/guides/api-specific-auth) recomenda o escopo mais estreito; `drive.file` é por arquivo e `drive` tem escopo restrito, com verificação aplicável. [Shared Drives](https://developers.google.com/workspace/drive/api/guides/about-shareddrives) dependem de Google Workspace, usam armazenamento pooled da organização, e service accounts não têm quota nem podem possuir arquivos. [Uploads](https://developers.google.com/workspace/drive/api/guides/manage-uploads) recomenda upload retomável para arquivos grandes/interrupções. A assinatura/tipo de conta do proprietário não foi confirmada, então essas fontes não determinam a arquitetura final.

## Interface do fotógrafo — Seção 9

- O dashboard existente consulta um resumo do tenant e apresenta galerias, clientes, imports e storage; a interface atual de upload apresenta lotes, progresso e falhas por arquivo. A busca delimitada não encontrou carteira, compra de créditos, fidelidade, nem tela de arquivo/restauração. Seleções, pedidos, pagamentos e histórico comercial aparecem em telas/rotas distintas.
- A carteira acrescenta saldo, consumo recente, operações pendentes e avisos de insuficiência vindos do servidor. Falha da consulta financeira não pode ser mostrada como saldo zero nem esconder o dashboard operacional. O checkout do cliente e `SaleOrder` permanecem separados da monetização interna do fotógrafo.
- A rota pública de galeria e o checkout do cliente têm implementação/testes locais. Nenhuma sessão autenticada de cliente/fotógrafo em produção foi inspecionada nesta etapa; produção foi consultada somente para saúde/versões read-only. A prova visual e de não regressão pós-implementação continua pendente.

## Privacidade e segurança — Seção 11

- Evidência local cobre isolamento por tenant em rotas/testes selecionados, roles, cookies de sessão protegidos, tokens hasheados, prévias com `private,no-store`, upload JPEG validado, rate limits, auditoria por eventos e assinatura HMAC no webhook Mercado Pago. Isso não representa cobertura completa de todos os módulos, workers, proxies, logs e provedores.
- A exclusão administrativa de clientes não formaliza o processo completo para solicitações de titulares. A retenção técnica é configurável para classes específicas, mas base legal, prazos e exceções não foram validados. Em 06/11, foram identificados o timer e o status de falha do serviço de backup; catálogo atual, artefatos, retenção e restauração real continuam desconhecidos (evidência em `add-platform-backup-recovery/inventory.md`).
- Nenhum cliente Drive foi localizado no runtime inspecionado; URLs HTTPS de entrega são inseridas manualmente. O webhook Mercado Pago valida HMAC; idempotência do webhook Evolution foi localizada, mas autenticação criptográfica não foi comprovada nesta leitura.
- HTTPS, autenticação, criptografia de campos ou status saudável isolados não comprovam adequação LGPD. Parecer jurídico, prazos e procedimento de direitos permanecem dependências especializadas registradas.

## Escalabilidade e desempenho — Seção 12

- Listas de clientes/pagamentos usam cursores; galerias paginam pastas/fotos; o domínio declara índices por tenant/estado. Derivados e indexação são jobs persistidos com lease, `SKIP LOCKED`, tentativas e retry; o cache do cálculo de storage usa tenant na chave e revalida autorização.
- Observabilidade técnica do monitor é restrita e limitada por semáforo; o dashboard mede storage local por tenant, não quota externa validada. Nenhum perfil de volume real de produção foi consultado e não há benchmark representativo de milhares de JPEGs nesta execução.
- Não criar meta de capacidade nem otimização antecipada. Quando houver medição autorizada, usar dados sintéticos e revisar planos de consulta, filas, storage, latência e backpressure sem usar fotos/dados pessoais reais.

## Prioridade de execução — Seção 14

- A ordem explicitamente prioritária do documento prevalece sobre a numeração temática: F0 reconciliação/ambiente; F1 TOTP/isolamento; F2 carteira/upload; F3 compra Mercado Pago; F4 painéis; F5 Drive/backup/arquivo; F6 fidelidade; F7 cadastro público; F8 integração/piloto.
- A auditoria pode mapear antecipadamente requisitos de fases futuras, mas implementação deve respeitar dependências e gates nesta ordem. UI começa desde as primeiras fases; cadastro público só depois das bases de segurança/operação validadas.

## Decisões ainda necessárias

- Preços, quantidades e condições comerciais dos pacotes de créditos.
- Momento de ativação comercial da carteira após o checkpoint de release, mantendo o tenant atual do proprietário ilimitado e sem saldo artificial.
- Conta recebedora decidida: conta do proprietário já utilizada nas vendas de fotos; sandbox de créditos validado e limites aceitos em 02/11, conforme a change de compras. Ativação real requer release autorizado.
- Estorno/chargeback decidido: manter ledger e bloquear uploads/compras até revisão manual, sem débito automático de créditos consumidos.
- Eventos, critérios, conversão e benefícios do programa de fidelidade.
- Validade dos pontos de fidelidade e tratamento de reembolso/chargeback depois de pontos ou recompensa emitidos.
- Base legal, prazos de retenção e exceções legais para históricos pessoais/comerciais; requer validação especializada.
- Quota efetiva e destino concreto no Google Workspace (My Drive ou Shared Drive), permissões herdadas, cadastro da identidade dedicada de rotina e custódia dos tokens/chaves; a conta do proprietário será usada somente no teste pré-abertura.
- Portal de fotógrafo — decisão de 31/10 SUBSTITUÍDA em 03/11: ativação automática pelo website após e-mail verificado e MFA, sem aprovação manual ou convite do console. A change `add-photographer-signup-portal` está gated por R14-0–6. Permanecem pendentes confirmação do domínio `pickyourpic.com.br`/titularidade/DNS/TLS, provedor anti-bot e retenção legal. Não reutilizar dados do checkout enquanto finalidade/transparência não forem validadas.
- Backup SaaS: política global/escopo inicial, Google Workspace como destino e identidade dedicada para a rotina decididos em 06/11 (D15–D17 abaixo). O teste pré-abertura usará somente a conta do proprietário; cadastro da identidade dedicada, quota, pasta/Shared Drive, custódia operacional, consentimento e autorização do ensaio externo continuam pendentes. Arquivos e restore por tenant foram faseados para depois.
- Política de arquivo: janela operacional de 30 dias, objetos originais/derivados/históricos incluídos, precedência com pedidos em revisão e retenção legal/biométrica; quem aprova restauração e SLA/custo futuro sem cobrança implementada.
- Limites de tenant, cotas e metas de serviço, após medição representativa.
- Regras comerciais e administrativas para ativação/suspensão, taxas, reembolsos e chargebacks da compra de créditos.


## Decisões substitutivas de 03/11/2026

- **D09 — Suspensão:** autorização explícita para implementar/testar somente localmente. Bloquear acessos/uploads/jobs/mensagens, preservar dados e conciliação de pagamentos já iniciados; reativação explícita. Não é autorização para suspender produção.
- **D10 — Cadastro automatizado:** proprietário escolheu “Ativar automaticamente após verificar e-mail”. Website `pickyourpic.com.br` realiza ingresso; não haverá aprovação manual ou convite criado no console. Verificação de e-mail, senha/TOTP e isolamento permanecem controles; nada concede papéis globais.
- **D11 — Prova de fluxo:** backend e prova de cadastro têm prioridade. Interface simples local é suficiente; prova sintética pode ser implementada antes do design final. Isso não publica website nem antecipa Termos jurídicos de lançamento; e-mail/anti-bot reais e DNS/TLS precisam de configuração/liberação próprias.
- **D12 — Identidade global:** reutilizar `PlatformOwner` como permissão persistida exclusiva; não criar grants comerciais delegáveis nem dar autoridade por MonitorGrant/InstallationOperator. O novo schema local 0096 contém somente auditoria append-only, sem substituir log legado.
- **D13 — Baseline:** em 03/11 `origin/main` e ls-remote são `855be42b`; worktree SaaS mantém baseline `6af538ec` e diff intacto. Não importar amplamente patches faciais ou usar status operacional stale. Publicação exige reconciliação/compatibilidade próprias.

- **D14 — Google Workspace:** proprietário confirmou organização e informou que ainda não existe projeto Google Cloud/cliente OAuth. Solicitou orientação. Guia em `google-workspace-setup.md`; quota aproximada declarada ainda não é observação autenticada. Projeto/API/consentimento podem ser preparados pelo proprietário; callback, escopos, custódia e destino precisam ser fechados antes de credenciais/código. Nenhuma criação remota foi executada.

## Decisões de backup de 06/11/2026

- **D15 — Política global:** após esclarecer que os valores são da plataforma inteira, e não por tenant, o proprietário aprovou cópia diária; RPO alvo 24 h e RTO alvo 8 h a comprovar, sem SLA; retenção 7 diários/4 semanais/3 mensais e ensaio mensal de restore em ambiente descartável. A política permanece configurável e não altera retenção dos dados ativos.
- **D16 — Escopo inicial e custódia:** aprovado PostgreSQL completo e configurações essenciais cifradas, incluindo dados pessoais/financeiros/biométricos existentes no banco, com recuperação global. Fotos, arquivos biométricos/WhatsApp e restore lógico por tenant ficam para etapa própria. Chave de recuperação sob custódia offline do proprietário e segunda cópia externa com conta/credenciais independentes do servidor de origem. Implementação e testes locais com adapters sintéticos podem avançar; publicação/expurgo/ensaio real exigem gates próprios. Evidência e implementação em `add-platform-backup-recovery`; nenhuma chave real foi criada/configurada.

- **D17 — Destino externo e teste pré-abertura:** em 06/11, o proprietário selecionou Google Workspace, uma identidade dedicada para a rotina e a própria conta para o ensaio. Em 17/11/2026, escolheu a conta Workspace do proprietário já conectada também para a rotina global e autorizou criar `Meu Drive / Pick-your-Pic Tenants` como destino. O app criou e verificou a nova pasta privada na raiz. A pasta homônima em `Oracle-Production-Backups` foi preservada. A custódia independente da chave fora do servidor e da conta do Drive segue conforme D16. A rotina automática e seu acesso operacional permanecem pendentes. [Verificação do destino](../../openspec/changes/add-google-drive-storage-foundation/production-drive-proof.md#destino-da-rotina-verificado).

  **Atualização de 17/11/2026:** o proprietário aprovou preservar sem alterações `Oracle-Production-Backups/Pick-your-Pic`, já utilizada pelo timer compartilhado e contendo cópias existentes. Foram preparadas e verificadas vazias, como pastas irmãs, `Pick-your-Pic Global` e `Pick-your-Pic Tenants`. O destino pretendido do backup global passa a ser `Oracle-Production-Backups/Pick-your-Pic Global`; a raiz `Pick-your-Pic Tenants` fica reservada para subpastas futuras por UUID, sem habilitar backup/restauração lógica por tenant. A criação pelo conector Drive não concede acesso ao OAuth do Pick-your-Pic; o novo destino ainda precisa ser selecionado pelo app com `drive.file`, vinculado com a rotina desativada e validado por ensaio sintético. A pasta app-autorizada que já existe na raiz de Meu Drive e a configuração desativada permanecem intactas até essa validação.
