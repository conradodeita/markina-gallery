# Proposal

## Why

O Pick-your-Pic precisa receber pagamentos dentro da própria experiência por Checkout Transparente via Orders API, com configuração independente por fotógrafo, preservando PIX manual, isolamento e histórico financeiro.

## What Changes

- Adicionar conta Mercado Pago cifrada por tenant, configuração protegida por senha/OTP e controles independentes de PIX e Mercado Pago.
- Criar tentativa financeira imutável com pedidos por galeria, valores autoritativos, idempotência, conciliação e webhook durável do tópico `order`.
- Integrar cartão tokenizado por MercadoPago.js e Pix da Orders API numa tela própria, com retomada, cancelamento e proteção contra duplicidade.
- Projetar estados de pagamento, pedido e provedor no histórico, dashboard e CSV.
- Validar em desenvolvimento com fixtures oficiais simuladas e testes de integração; contas/credenciais de teste externas continuam dependentes de disponibilidade.
- Preparar a validação final solicitada pelo proprietário na instalação de produção, exclusivamente com credenciais de teste e seu próprio cliente. Fora de desenvolvimento/teste, emissão de teste SHALL exigir autorização por par tenant/cliente no servidor; a preparação do PR/plano não executa publicação.

## Capabilities

### New Capabilities

- `gallery-sales/mercadopago-orders`: configuração por conta, tentativas, estados, checkout, notificações e reconciliação Orders.

### Modified Capabilities

- `gallery-sales/global-pix-configuration`: habilitação independente sem apagar configuração ou snapshots.

## Impact

Backend FastAPI/SQLAlchemy/Alembic, carrinho e compras Next.js, Configurações, Vendas e pagamentos, worker e exportação. Migration aditiva após 0087, sem reescrever IDs ou tabelas financeiras InfinitePay. Dependências oficiais somente conforme autorização. Não autoriza publicação, migração operacional, envio de mensagens ou operações financeiras reais.
