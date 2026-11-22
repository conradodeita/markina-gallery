# Why

Após reabrir uma tentativa de cartão sem resultado conclusivo, sua exibição em Compras continua sugerindo compra pendente mesmo quando a cliente remove todas as fotos. O proprietário aprovou separar essa tentativa do carrinho editável e preservar somente seu histórico operacional, com destaque específico se surgir evidência financeira tardia.

# What Changes

- Retirar tentativa auditada reaberta de Compras e da lista principal de Vendas e pagamentos imediatamente após reabrir, independentemente de a cliente manter, alterar ou esvaziar a seleção.
- Oferecer ao fotógrafo consulta explícita de tentativas encerradas por reabertura, mantendo snapshots e auditoria sem tratar o registro como receita ou pendência ativa.
- Se houver evidência tardia queued/processing/verified ou recebido após a recuperação (inclusive ignored/failed), NSU, confirmação ou estado financeiro incompatível com a exceção reaberta, manter a ocorrência visível para conferência com rótulo específico; não confirmar pedidos cancelados nem alterar nova compra.
- Preservar isolamento e autorizações; nenhum delete, migration, chamada InfinitePay, segredo ou operação em compra real.

# Capabilities

## New Capabilities
- `gallery-sales/reopened-purchase-visibility`: projeção da recuperação nas listas do cliente e fotógrafo.

## Modified Capabilities
- Nenhuma spec principal é sincronizada antes da revisão humana. A decisão substitui somente a exibição de Carrinho reaberto em Compras prevista na change anterior, conforme autorização explícita da conversa.

# Impact

API de projeção e frontend Compras/Vendas e pagamentos; testes existentes de recuperação serão adaptados ao novo contrato, com novas regressões. A escrita financeira, callback, reabertura, seleção e inventários permanecem preservados. Reutilizar projeções/auditoria existentes; remover somente a apresentação substituída, sem limpeza geral. Publicação integrada futura API/web junto do cofre0085 exige plano e autorização próprios; não ampliar o manifesto0084.
