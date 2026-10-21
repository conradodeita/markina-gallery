# Contrato reutilizado do PR #260

Reconsulta somente documental em 21/10/2026: [Central de Ajuda oficial](https://ajuda.infinitepay.io/pt-BR/articles/10766888-como-usar-o-checkout-integrado-da-infinitepay). Nenhuma requisição à API financeira foi executada. A página vigente confirma `X-Api-Key`, criação em `/links`, opções por link e consulta em `/payment_check`. A chave é necessária às opções avançadas; o exemplo de consulta usa o header e os identificadores correlacionados à compra. O adaptador do #260 é preservado, inclusive cartão exclusivo e pagamento único.

Não consta nessa página uma operação isolada de validação de API Key sem pedido/transação. Portanto cadastro não cria link de teste, não consulta pedido fictício e não declara validação remota. O painel registra somente disponibilidade local da credencial e informa validação remota indisponível. Não inferir autenticidade de webhook sem contrato de assinatura; retorno do navegador continua sendo somente candidato para consulta autoritativa no tenant da compra.

A nova implementação altera a origem segura da credencial, conservando endpoints, header e payload do PR pai. Compra gerida usa sua referência persistida; compra legada com referência nula usa exclusivamente seu binding por tenant. Substituir a chave atual nunca altera o contrato de uma compra emitida.
