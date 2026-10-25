# Análise e fontes — 24/10/2026

## Arquitetura e dependências

Frontend Next.js App Router/React 19/TypeScript e tokens visuais atuais; proxy /api já preserva cookies. Backend FastAPI em main.py com módulos comerciais, SQLAlchemy 2, PostgreSQL, Alembic, Redis/workers. UUIDs públicos, UTC e centavos. Acervo, biometria e importação permanecem fora da alteração.

Admin e cliente usam AuthSession vinculada a tenant; diretório, memberships e owned_record validam conta. Constraints compostas em ownership_schema reforçam propriedade no banco. Clientes de mesmo telefone em contas diferentes não são equivalentes. Origens de mutação e reautenticação administrativa precisam continuar obrigatórias.

## Fluxo comercial existente

Seleções PhotoSelection apontam galeria canônica/GalleryClientState ou galeria derivada legada, foto e cliente. checkout._checkout_material valida acesso, material, prazo e preço pela galeria pública. gallery_pricing calcula preço/faixas no servidor. SaleOrder/SaleOrderItem congelam fotos, nomes, preços, termos, cliente, referências e recebedor. Pagamento confirmado habilita entrega manual Google Photos; seleções sem cobrança usam not_required e não geram receita.

unified_checkout agrupa o carrinho autorizado da conta. GET consulta sem cobrar; prepare_group cria/revisa PaymentGroup PIX draft e pedidos editáveis. report_group congela e consome seleção atomicamente sob locks conta/cliente/galerias; PaymentCommunication exige decisão manual do fotógrafo. Comunicação e outboxes produzem avisos deduplicados. Alterações posteriores de PIX não modificam snapshots.

PIX usa GlobalPixSettings por tenant, protegido por senha e desafio WhatsApp vinculado à sessão/proposta/versão. Não pode apagar configuração; nova flag permite desabilitar emissão sem removê-la. Mercado Pago não usa PaymentCommunication como prova financeira.

ProviderPayment/Attempt/Receipt/Correction são exclusivamente históricos InfinitePay, com constraint de provider, sem URL ou credenciais operacionais. Não reativar módulos ou rotas aposentados. A spec infinitepay-retirement e alterações arquivadas prevalecem sobre tasks InfinitePay antigas ainda visíveis.

Compras em main.py projeta pedidos congelados, mídia histórica e grupos. Dashboard /admin/payments agrupa por cliente e mantém filtros de situação, galeria, cliente, intervalo, busca e entrega, mais CSV. Situação financeira e payment_status são conceitos separados; o novo provedor precisa projetar ambos. Estatísticas usam apenas pedidos confirmados, logo estornos não podem continuar receita confirmada.

## Skills efetivamente consultadas

- Jev Codex Token Saver: duas seleções amplas bem-sucedidas. Recuperaram decisões/specs e fronteiras; não trouxeram detalhes suficientes de auth.py/checkout.py/unified_checkout.py, que foram lidos diretamente após a recuperação informada. Não prova cobertura absoluta do repositório.
- ai-memory-retrieval: roteamento declarado workspace pick-your-pic/project system. Tools memory_query/read indisponíveis nesta sessão; nenhuma instalação/configuração realizada. Histórico local MEMORY.md ajudou a identificar snapshots, incerteza e grupos; cada fato foi confrontado com a base atual. Não salvar memória sem pedido específico.
- mp-integrate, referências terminology/recommendation/checkout-api/marketplace/webhooks/products, mp-webhooks e mp-review: contratos especializados, CTA, tokenização, idempotência, segurança e teste. MCP Mercado Pago indisponível; documentação pública oficial foi consultada.
- openspec-apply-change: execução da change add-mercadopago-orders-checkout. A instrução explícita do proprietário autoriza criação de artefatos seguida de implementação, sem encerrar em plano.

## Fontes oficiais verificadas

- https://www.mercadopago.com.br/developers/pt/docs/checkout-api-orders/overview
- https://www.mercadopago.com.br/developers/pt/docs/checkout-api-orders/payment-integration/websites/cards
- https://www.mercadopago.com.br/developers/pt/docs/checkout-api-orders/payment-integration/websites/pix
- https://www.mercadopago.com.br/developers/pt/reference/online-payments/checkout-api/create-order/post
- https://www.mercadopago.com.br/developers/pt/reference/online-payments/checkout-api/search-order/get
- https://www.mercadopago.com.br/developers/pt/docs/checkout-api-orders/payment-management/status/order-status
- https://www.mercadopago.com.br/developers/pt/docs/checkout-api-orders/payment-management/status/transaction-status
- https://www.mercadopago.com.br/developers/pt/docs/checkout-api-orders/notifications
- https://www.mercadopago.com.br/developers/pt/docs/checkout-api-payments/how-tos/integrate-marketplace
- https://github.com/mercadopago/sdk-python
- https://pypi.org/project/mercadopago/ (estável 3.6.0 consultada também no JSON do registry)

Divergências: skill genérica usa orders e limita Brick a Payments; documentação específica atual usa order e demonstra Card Payment -> /v1/orders. Fontes específicas prevalecem. llms.txt não acessível pelo navegador de pesquisa; fallback oficial acima. SDK Python não instalado no início, autorização solicitada conforme skill. Não houve acesso a produção ou dados de clientes.

Reconsulta durante preparação externa: `resources/test-accounts`, `integration-test/cards` e `your-integrations/credentials` agora documentam que o teste básico Orders usa credenciais Teste da aplicação e não exige criar/logar contas extras. Access Token de teste continua APP_USR. O trecho antigo de mp-test-setup que exige comprador separado para todo Orders não foi seguido contra a fonte oficial atual. Cartão Mastercard atual documentado: 5480 8328 0103 3311; cenários APRO/FUND/CONT. O proprietário confirmou acesso ao Developers e disponibilidade de Public Key/Access Token no ambiente Teste. Recebimento seguro por caminho de arquivo externo ao Git foi solicitado; nenhum valor foi enviado ao chat. Browser controlado recusou abertura por estar desabilitado nas configurações, sem tentativa de contornar ou acessar perfil pessoal.

## Refatoração proporcional

Reutilizar cotação, snapshots, autenticação, cofre, outboxes e projeções. Acrescentar módulo financeiro focado. Não remover histórico InfinitePay ou modernizar main.py fora do necessário.
