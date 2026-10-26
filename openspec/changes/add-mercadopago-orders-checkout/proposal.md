# Proposal

## Why

O Pick-your-Pic precisa receber pagamentos dentro da própria experiência por Checkout Transparente via Orders API, com configuração independente por fotógrafo, preservando PIX manual, isolamento e histórico financeiro.

## What Changes

- Adicionar conta Mercado Pago cifrada por tenant, configuração protegida por senha/OTP e controles independentes de PIX e Mercado Pago.
- Criar tentativa financeira imutável com pedidos por galeria, valores autoritativos, idempotência, conciliação e webhook durável do tópico `order`.
- Permitir compras simultâneas com conjuntos de fotos independentes, mantendo cada snapshot e tentativa isolados; fotos reservadas por uma ordem ativa não podem ser cobradas por outra tentativa.
- Integrar cartão tokenizado por MercadoPago.js e Pix da Orders API numa tela própria, com retomada, cancelamento e proteção contra duplicidade.
- Projetar estados de pagamento, pedido e provedor no histórico, dashboard e CSV.
- Aplicar piso global de R$ 1,00 às novas tentativas Mercado Pago, sem alterar o PIX manual, e preservar os mínimos dinâmicos por método retornados pelo provedor.
- Validar em desenvolvimento com fixtures oficiais simuladas e testes de integração; contas/credenciais de teste externas continuam dependentes de disponibilidade.
- Preparar a validação final solicitada pelo proprietário na instalação de produção, exclusivamente com credenciais de teste e seu próprio cliente. Fora de desenvolvimento/teste, emissão de teste SHALL exigir autorização por par tenant/cliente no servidor; a preparação do PR/plano não executa publicação.
- Priorizar a publicação do piloto sandbox com validação proporcional, CI aplicável e preservação/recuperação essencial, sem novas baterias rígidas opcionais ou sucessivos pushes apenas para ampliar testes/documentação. Em 25/10/2026, o proprietário autorizou explicitamente merge/deploy durante sua ausência e acompanhamento do CI a cada 30 minutos até a conclusão, mantendo o mesmo cliente de teste.

## Capabilities

### New Capabilities

- `gallery-sales/mercadopago-orders`: configuração por conta, tentativas, estados, checkout, notificações e reconciliação Orders.

### Modified Capabilities

- `gallery-sales/global-pix-configuration`: habilitação independente sem apagar configuração ou snapshots.
- `deployment-operations/owner-reset`: preservar configuração Orders do proprietário e impedir reset com evidência financeira enviada de qualquer tenant.
- `deployment-operations/orders-pilot-release`: atualizar o piloto já publicado em `9bd66c48`/0088 para 0089, preservando identidade, configurações e tentativas existentes, com preparação isolada, restauração ensaiada, fingerprint, parada verificada dos escritores e emissão de teste restrita ao proprietário. Janela de manutenção aceita explicitamente em 25/10/2026; a próxima aplicação depende de plano e aprovação concretos.

## Impact

Backend FastAPI/SQLAlchemy/Alembic, carrinho e compras Next.js, Configurações, Vendas e pagamentos, worker e exportação. A atualização exige 0089 após o piloto 0088, sem reescrever IDs ou registros financeiros legados. Dependências oficiais somente conforme autorização. Em 25/10/2026, o proprietário autorizou expressamente merge e deploy deste piloto, incluindo a atualização necessária de schema, após os gates essenciais. Liberação geral, novas credenciais de produção e cobranças reais continuam fora do escopo.
