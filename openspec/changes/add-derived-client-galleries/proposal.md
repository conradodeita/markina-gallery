## Why

O fotógrafo precisa transformar fotos encontradas ou selecionadas em um espaço privado e persistente para cada cliente, sem expor o acervo coletivo do evento. Também precisa visualizar a conversão real de cada seleção em vendas e permitir interação controlada do cliente durante a revisão.

## What Changes

- Criar galerias privadas derivadas de um acervo-mãe, com fotos referenciadas sem duplicar arquivos, acesso, prazo e mensagem próprios.
- Permitir que o cliente autorizado selecione, favorite e comente fotos na sua galeria derivada, podendo desfazer favoritos e excluir seus próprios comentários.
- Permitir ao fotógrafo habilitar ou desabilitar favoritos e comentários por galeria derivada; comentários permanecem privados entre o cliente e o fotógrafo.
- Criar a página administrativa de estatísticas com fotos compradas, selecionadas não compradas, listas nominais e exportação TXT, receita de pagamentos confirmados e gráfico temporal.

## Capabilities

### New Capabilities

- `client-access/derived-galleries`: acesso privado do cliente a galerias derivadas, com prazo, mensagem e permissões próprias.
- `gallery-sales/photo-engagement`: seleção, favoritos e comentários privados controlados pelo fotógrafo.
- `gallery-sales/sales-statistics`: indicadores de seleção e compra, exportação TXT e receita temporal administrativa.

### Modified Capabilities

<!-- Nenhuma especificação principal existente cobre estes comportamentos ainda. -->

## Impact

- Backend FastAPI, modelos e migrations para acervos, galerias derivadas, interações e agregados de venda.
- Frontend administrativo e portal do cliente, com permissões por galeria e estados acessíveis.
- APIs de seleção, interação, estatísticas e exportação autenticadas e auditáveis.
- Não inclui reconhecimento facial; resultados faciais só poderão alimentar galerias derivadas após o spike separado ser aprovado.
