# Proposal

## Why

Na edição e no resumo da Galeria pública, os cards das clientes vinculadas ficam lado a lado em telas largas, reduzindo a área útil e dificultando localizar a cliente que acessou por último.

## What Changes

- Apresentar cada card de cliente em uma única coluna, preservando o menu recolhível da coleção e os demais controles.
- Ordenar as clientes pela última prévia protegida visualizada na Galeria pública ou privada, da mais recente para a mais antiga; usar a data do vínculo como fallback quando ainda não houver visualização.
- Expor a data de atividade na projeção administrativa da galeria para que a ordem seja autoritativa e consistente.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `gallery-sales/operational-gallery-interface`: apresentação vertical e ordenação por atividade recente dos cards de clientes vinculadas.

## Impact

Afeta a projeção administrativa de clientes, o tipo de dados do card, estilos da lista e testes direcionados. Não altera autorização, regras de venda, seleção, menu recolhível, banco de dados ou armazenamento.
