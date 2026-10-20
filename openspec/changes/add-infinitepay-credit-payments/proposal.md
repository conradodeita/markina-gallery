# Proposal

## Why

O fotógrafo precisa oferecer cartão de crédito pela própria conta InfinitePay, além do PIX manual já existente. A base multitenant atual já isola o PIX e o comércio por conta; a nova integração precisa conservar esse isolamento e confirmar pagamentos com evidência do provedor.

## What Changes

- Adicionar uma configuração InfinitePay por conta de fotógrafo em Configurações, com InfiniteTag, estado de preparação/ativação e controle explícito para habilitar ou desabilitar cartão aos clientes; proteger alterações sensíveis e não solicitar senha da InfinitePay nem dados de cartão.
- Oferecer `PIX` e `Cartão de crédito` separadamente na revisão de compras que exigem pagamento. Cartão será habilitado apenas para a conta configurada e após comprovar que o link externo oferece somente crédito.
- Criar cobrança de cartão no servidor com recebedor, itens e valor congelados por compra; conservar a configuração PIX, sua confirmação manual e seus snapshots existentes.
- Confirmar cartão somente após consulta autoritativa à InfinitePay, vinculada a conta, compra e transação, com valor correto e método `credit_card`; redirecionamento e notificação isolados não confirmam pagamento.
- Acrescentar idempotência, proteção contra cobrança duplicada, retomada de compra pendente, auditoria e integração com os eventos existentes de confirmação e entrega.
- Persistir categorias técnicas minimizadas para diagnosticar respostas sem checkout utilizável, sem armazenar corpos externos ou segredos e sem converter incerteza em liberação automática.
- Desabilitar cartão somente para novos checkouts; links já emitidos continuam visíveis e retomáveis enquanto permanecerem pendentes, pois a plataforma não cancela links remotos.
- Condicionar implementação/ativação aos gates registrados em `provider-contract.md` e `readiness.md`. A exigência vigente de webhook assinado não é substituída automaticamente pela consulta de status.

## Capabilities

### New Capabilities

- `gallery-sales/infinitepay-credit-payments`: recebimento por cartão na conta própria do fotógrafo, preparação protegida, checkout imutável, confirmação verificável, retomada e coexistência com o PIX manual.

### Modified Capabilities

Nenhuma alteração ao contrato do PIX manual. Seu isolamento segue o delta aprovado de `add-small-multi-photographer-pilot`; esta change não sincroniza nem arquiva esse trabalho.

## Impact

Backend FastAPI/SQLAlchemy/Alembic, porta `PaymentProvider`, worker durável de verificação, revisão do carrinho, Configurações e Compras no frontend, projeções financeiras e notificações existentes. Os novos recursos e referências precisam de `tenant_id` e integridade composta. Cartão será preenchido exclusivamente no checkout hospedado pelo provedor.

A preparação usa o SHA verde `f942cf3a74c432b53263f175c27f5b4274bcae82`; evidências e limites estão em `readiness.md`. A implementação depende da revisão desta proposta, da reconciliação das pendências da change de isolamento e do contrato externo aplicável. Deploy, provisionamento, configuração externa e transações reais exigem autorizações próprias e pacote de impacto zero.

## Non-goals

PIX da InfinitePay, substituição do PIX manual, divisão de recebíveis, comissão da plataforma, assinaturas, débito, formulário próprio de cartão, armazenamento de PAN/CVV, integração bancária do PIX, reembolso financeiro por API, novo cadastro público de fotógrafo ou ativação de contas reais nesta preparação.

## Review

Escopo confirmado pelo proprietário em 12/10/2026: PIX existente isolado por fotógrafo e InfinitePay exclusivamente para cartão de crédito. Após a apresentação dos artefatos e esclarecimento da confirmação automática do cartão, o proprietário autorizou a implementação com “ótimo! Então vamos prosseguir”. O requisito de assinatura de webhook permanece vigente; o aceite não autoriza substituí-lo nem habilitar cobranças/deploy reais.

Complemento aprovado pelo proprietário em 13/10/2026: adicionar em Configurações um controle explícito para habilitar/desabilitar pagamentos com cartão para clientes da conta do fotógrafo.
