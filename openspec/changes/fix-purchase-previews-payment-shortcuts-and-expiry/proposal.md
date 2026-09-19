## Why

O cliente vê imagens quebradas ao abrir fotos de uma compra confirmada. O fotógrafo precisa navegar demais para decidir pagamentos nos cards de clientes e o prazo configurado não aparece como tempo restante, dificultando a compreensão da expiração.

## What Changes

- Corrigir o carregamento autenticado das prévias históricas e operacionais em Compras, incluindo ampliação, sem expor originais ou perder histórico após expiração.
- Exibir atalhos `Confirmar pagamento`, `Pagamento não localizado` e `Corrigir confirmação` nos cards de clientes da pública e privada, reutilizando as decisões existentes e identificando o pedido correto.
- Apresentar data/hora limite e tempo restante de seleção nas superfícies cliente/admin pertinentes, usando a data efetiva do backend. Não inventar vencimento global a partir de um prazo padrão nem tratar compras como expiradas.
- Preservar confirmação condicionada à comunicação do cliente, correção silenciosa, separação cliente/galeria/pedido e independência de WhatsApp/push.
- Manter layout fluido, duas colunas de fotos no mobile/quatro no desktop, textos curtos e validação cirúrgica.

## Capabilities

### New Capabilities

Nenhuma capacidade independente nova.

### Modified Capabilities

- `client-access/derived-galleries`: explicitar prévias de compras carregáveis e prazo de seleção visível com contagem contextual, sem alterar autorização ou histórico.
- `gallery-sales/client-selection-operations`: ações financeiras contextuais por pedido nos cards, com mesmos gates e confirmação existentes.

## Impact

Biblioteca cliente, apresentação do prazo em galeria/biblioteca, cards administrativos compartilhados, Vendas e pagamentos e projeções mínimas do backend para identificar prazo/pedidos/capacidades. Sem nova migration prevista, sem alteração de preços, datas persistidas, retenção, biometria, ícones, credenciais ou canais ativos. Reutilizar APIs e componentes; não carregar o dashboard financeiro inteiro por card nem criar polling de rede por segundo.

Relaciona-se às changes `fix-client-deadline-and-watermark-size`, `complete-private-gallery-operations-and-sales`, `separate-client-cart-and-purchase-history` e `configurable-push-and-whatsapp-notifications`; não reabre nem substitui suas regras financeiras/privacidade. A implementação foi autorizada pelo proprietário e está registrada em `continuity.md`. Push/CI segue o processo do repositório, parando após push para o proprietário conferir Actions. Deploy exige inventário/plano aprovado; aceite remoto e sincronização/arquivamento continuam pendentes.
