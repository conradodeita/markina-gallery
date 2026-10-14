## Why

Após confirmar um pagamento em “Vendas e pagamentos”, o fotógrafo precisa voltar a “Galerias” e localizar o acervo da cliente para baixar o HTML das fotos compradas. A ação deve estar disponível junto às ações financeiras do pedido, preservando o relatório autônomo já existente e identificando a cliente também no nome do arquivo.

## What Changes

- Disponibilizar em cada card de pedido confirmado de “Vendas e pagamentos” a ação “Baixar fotos compradas”, usando a exportação HTML individual já existente.
- O HTML permanece limitado às fotos compradas pela cliente naquela galeria e mantém prévias embutidas, nomes de arquivo e metadados já previstos.
- Nomear o arquivo baixado com o nome da cliente, em formato seguro e compatível com nomes Unicode e caracteres especiais.
- A ação não confirma nem corrige pagamentos e não altera pedidos, seleções ou arquivos persistidos.

## Capabilities

### Modified Capabilities

- `gallery-sales/client-selection-operations`: permitir iniciar a exportação HTML a partir do pedido confirmado em Vendas e pagamentos e incluir o nome da cliente no nome do arquivo baixado.

## Impact

Interface administrativa de Vendas e pagamentos e resposta do endpoint HTML de exportação já existente. Não requer nova persistência, migration ou mudança no conteúdo comercial do relatório. A disponibilidade continuará condicionada à existência de compra confirmada para a cliente naquela galeria.
