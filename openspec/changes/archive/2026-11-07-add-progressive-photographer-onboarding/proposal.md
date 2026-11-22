# Proposal

## Why

O cadastro local atual exige TOTP antes de criar a conta e o login sempre exige segundo fator. Isso impede que um fotógrafo verifique o e-mail e explore o painel com nome, e-mail e senha, conforme a decisão do proprietário em 04/11/2026. Compra de créditos e upload precisam de gates próprios, independentes da navegação.

## What Changes

- Decisão final do proprietário em 05/11/2026, após considerar o OTP de clientes: **WhatsApp permanece obrigatório para uploads**; a ideia de torná-lo opcional foi retirada antes de alteração funcional. Sem conexão própria operacional, a central Notificações explica a pendência e bloqueia edição/ativação dos textos WhatsApp, preservando o push independente. A escolha futura WhatsApp ou e-mail é exclusiva por tenant e está em avaliação, incluindo o acesso de clientes, sem implementação de transporte e-mail nesta etapa.

- Dividir ingresso em conta exploratória com e-mail verificado e cadastro operacional completo. A conta exploratória poderá navegar no painel do próprio tenant, sem comprar créditos nem realizar upload.
- Tornar TOTP opcional para ingresso; após ativação voluntária, exigi-lo em cada login. Prever revogação exclusiva pelo `PlatformOwner` em recuperação assistida, com justificativa, auditoria, invalidação de sessões e notificação ao endereço verificado.
- Exibir estado e progresso na página Configurações, orientar correção de pendências no momento da compra e do upload e preservar o retorno à ação original.
- Reorganizar o progresso em etapas recolhíveis com indicação visual de conclusão; reutilizar nome e e-mail informados no ingresso sem solicitá-los novamente em Configurações.
- Solicitar CPF e endereço do pagador alinhado aos campos do Mercado Pago; exigir endereço completo para compra de créditos e pré-preencher os mesmos dados no checkout.
- Exigir dados pessoais aprovados e aceite versionado dos Termos operacionais para compra. Exigir também saldo, PIX recebedor e WhatsApp operacional para upload. Mercado Pago próprio do fotógrafo permanece opcional; a compra de créditos usa a conta do proprietário.
- Aplicar todos os gates no backend com contexto de tenant, sem permitir contorno por URL/API ou bloquear a exploração por requisitos operacionais.
- Conservar contas e sessões legadas; migração aditiva e evolução local sem alteração de produção.

## Capabilities

### New Capabilities

- `photographer-onboarding`: fases exploratória e operacional, progresso e protocolo de aceite.

### Modified Capabilities

- `auth`: TOTP opcional até ativação, recuperação conforme fator vigente e revogação assistida pelo proprietário.
- `billing/mercadopago-credit-purchases`: compra liberada somente após conclusão operacional.
- `billing/photographer-credit-wallet`: reserva para upload condicionada ao onboarding e às configurações operacionais.
- `media-storage`: bloquear uploads em todos os caminhos enquanto requisitos obrigatórios estiverem pendentes.
- `platform-admin/owner-console`: revogação assistida e auditada de TOTP do fotógrafo.

## Impact

Alterações aditivas em schema, API, UI e testes de autenticação, cadastro, pagamentos, créditos, uploads, configurações e console. A prova será local e sintética. Não há autorização de deploy, migration remota, configuração de segredos nem alteração de produção.

## Decisões e bloqueios

- Confirmado pelo proprietário: TOTP passa a ser obrigatório nos logins posteriores à ativação voluntária; o proprietário poderá revogá-lo em problemas de acesso. A revogação não deve revelar segredo, criar senha ou abrir sessão por si só.
- Decisão atualizada pelo proprietário em 05/11/2026: o cadastro operacional exige nome completo e e-mail capturados no ingresso, CPF e endereço do pagador. Configurações não repetirá nome/e-mail. Endereço obrigatório para liberar compra, formado por CEP, logradouro, número ou S/N, bairro, cidade e UF; complemento opcional. Telefone permanece opcional.
- O propósito de coletar esses dados no cadastro é pré-preencher o checkout de créditos do próprio fotógrafo com nome completo, e-mail verificado, CPF e endereço, evitando redigitação. O endereço permanecerá editável apenas para a transação quando o pagador diferir do fotógrafo; essa alteração não muda o perfil contratual.
- A regra de exigir endereço na compra é uma decisão de negócio do proprietário, não uma exigência universal do Mercado Pago: a documentação atual do Pix e dos cartões não o marca como campo obrigatório, enquanto o fluxo de boleto o exige. A futura inclusão de boleto continuará condicionada aos gates próprios dessa integração.
- Confirmado pelo proprietário: WhatsApp configurado significa a integração Evolution API existente configurada para a comunicação do tenant com seus clientes. A interface exibirá apenas “WhatsApp”. Uma simples digitação de número não comprova o requisito operacional.
- Confirmado pelo proprietário: cada fotógrafo conecta seu próprio número de WhatsApp por autoconfiguração em Configurações. O servidor cria uma instância isolada automaticamente; o fotógrafo faz o pareamento. A unicidade tenant/ambiente já é imposta pelo schema de isolamento (migration 0070); esta change deve preservar essa constraint e implementar credenciais protegidas, provisionamento idempotente, webhook e entregas por tenant, sem copiar a identidade do canal legado.
- Confirmado pelo proprietário: usar versão de teste dos Termos exclusivamente na prova local sintética. Minuta jurídica, identidade do provedor e retenção continuam pendentes; aceite operacional real falha fechado até aprovação.
- O portal público, SMTP e proteção anti-bot reais continuam sujeitos aos gates da change `add-photographer-signup-portal`.

## Fontes oficiais consultadas em 05/11/2026

- [Mercado Pago — Orders API com Pix](https://www.mercadopago.com.br/developers/pt/docs/checkout-api-orders/payment-integration/websites/pix).
- [Mercado Pago — Orders API com cartões](https://www.mercadopago.com.br/developers/pt/docs/checkout-api-orders/payment-integration/websites/cards).
- [Mercado Pago — Orders API com boleto e campos de endereço do pagador](https://www.mercadopago.com.br/developers/pt/docs/checkout-api-orders/payment-integration/websites/boleto).
