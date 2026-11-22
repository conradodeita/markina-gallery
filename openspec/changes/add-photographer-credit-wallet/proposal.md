# Proposal: Carteira de créditos do fotógrafo

## Contexto

A base selecionada já registra o JPEG em `/admin/photo-assets/{id}/source`, grava a fonte com publicação atômica e agenda o processamento de derivados. O worker processa esse job depois. O dashboard atual resume galerias, clientes, imports e armazenamento, mas não saldo nem consumo de créditos. O checkout Mercado Pago atual pertence a clientes e pedidos de fotografias. Não há carteira pré-paga, livro-razão de créditos ou débito por upload.

A Fase 2 do documento de execução requer um crédito por JPEG novo de conteúdo efetivamente armazenado, saldo e movimentações por fotógrafo, idempotência e tratamento consistente de uploads individuais, lotes, repetição e concorrência. A conta tenant atual do proprietário permanece ilimitada; carteiras finitas serão usadas pelos fotógrafos futuros. Capas técnicas são excluídas da cobrança e retry/replay/reindex do mesmo conteúdo não geram novo débito. Esta proposta cobre a carteira e a cobrança por envio; a compra Mercado Pago de créditos será especificada separadamente na Fase 3.

## Goals

- Registrar movimentos de créditos por tenant em livro-razão auditável, sem edição direta de saldo e sem expiração.
- Reservar e consumir um crédito uma única vez por operação lógica de upload que conclua com sucesso; liberar a reserva após falha técnica comprovada.
- Proteger saldo e reservas contra concorrência, duplicidade, replay e falha parcial de lote.
- Apresentar saldo e histórico ao fotógrafo e administrar pacotes configuráveis pelo proprietário global, sem inventar valores comerciais.
- Permitir ao proprietário global selecionar tenants de fotógrafos, consultar carteira e concessões ainda revogáveis, e conceder ou revogar créditos com referência auditável.
- Integrar ao dashboard do fotógrafo saldo disponível, consumo recente, operações de upload pendentes e avisos de insuficiência recebidos do servidor, mantendo a tela útil quando a informação financeira estiver indisponível.
- Preservar checkout, pagamentos, pedidos, galerias, uploads e identificadores existentes até que uma transição autorizada e validada esteja pronta.

## Non-goals

- Processar RAW ou alterar a pipeline de prévias além do ponto estritamente necessário para integrar a operação lógica de upload.
- Comprar créditos via Mercado Pago, processar reembolso/chargeback de compra de créditos ou habilitar transações financeiras reais; isso pertence a change separada.
- Criar fidelidade, pontos, cadastro público ou políticas comerciais de suspensão/confisco.
- Ativar a cobrança em produção, conceder saldo inicial real, alterar dados remotos ou publicar migrations.

## Evidência inicial e compatibilidade

- `backend/app/main.py` separa cadastro da foto (`register_folder_photo_asset`) do recebimento da fonte (`import_photo_source`). O segundo valida e armazena o JPEG, chama o lifecycle facial e enfileira os derivados.
- `backend/app/facial/lifecycle.py` reconhece replay pela identidade persistida da foto e pelo fingerprint do conteúdo; `write_source` grava em staging, usa `fsync` e publica por rename atômico. A escrita em arquivo e a confirmação no banco não formam uma única transação.
- `backend/app/worker.py` executa derivados após o recebimento. Erros de processamento posteriores não apagam por si só a fonte já persistida.
- `backend/app/auth.py` contém pagamentos Mercado Pago vinculados a cliente/checkout de fotos e pedidos `SaleOrder`; não há entidade de compra de saldo do fotógrafo.
- `frontend/app/admin/page.tsx` e `backend/app/main.py:2784-2857` implementam o dashboard por tenant com galerias, clientes, imports e storage, sem dados de carteira. A interface de upload já mostra progresso e interrupções, mas não consumo de créditos.
- `InstallationOperator` e `/admin/installation-capabilities` representam autorização técnica de diagnóstico (`capacity_diagnostics`), não autorização comercial global.

## Decisões do proprietário registradas em 31/10/2026

1. Somente o proprietário global poderá criar pacotes, conceder créditos e revogar concessões; a permissão técnica de diagnóstico não terá poder comercial.
2. Hoje não há outro tenant de fotógrafo além da conta do proprietário. O tenant explicitamente associado ao proprietário permanece sem limite e sem débito; não haverá saldo numérico artificial. Fotógrafos futuros usarão carteira finita, sem concessão inicial automática presumida.
3. Um JPEG novo de uma pasta `content` consome um crédito. Retry/replay/reindex do mesmo `PhotoAsset` não consome outro; JPEGs em `cover_assets` não consomem crédito.
4. Uma fonte confirmada como durável corresponde a um único consumo, inclusive quando uma falha de confirmação exige reconciliação. A mesma operação deve ser recuperada sem débito duplicado; falha comprovada antes da durabilidade libera a reserva.
5. A revogação de concessões usará alocação FIFO por origem (`created_at`, `id`) com eventos imutáveis; só o saldo ainda livre do grant identificado poderá ser revogado. O proprietário aprovou esta regra em 31/10/2026.
6. Reenvio deliberado de bytes JPEG idênticos para a mesma pasta é uma nova operação debitável, mas exige confirmação antes de transferir. Cancelar pula somente as repetidas e continua com os arquivos novos. Retry/replay técnico e reindex preservam a identidade anterior. O proprietário decidiu em 01/11/2026.

Preços, quantidades e condições comerciais permanecem configuráveis sem defaults; nenhum valor será presumido ou semeado nesta change. A identificação técnica do tenant ilimitado, a chave persistente da operação e a implementação da reconciliação são detalhadas no design antes de qualquer migration. Esta decisão de produto não autoriza ativação ou alteração de dados em produção.

## Impacto de refatoração contínua

A área afetada é upload JPEG, sua recuperação/idempotência, pagamentos e projeções administrativas do fotógrafo. A avaliação deve preservar os contratos existentes e procurar somente duplicação ou código obsoleto que a integração necessariamente substitua. Se não houver remoção segura, registrar isso; não ampliar para uma auditoria geral.
