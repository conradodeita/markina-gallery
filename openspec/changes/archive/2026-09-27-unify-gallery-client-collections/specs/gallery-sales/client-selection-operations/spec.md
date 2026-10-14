# Spec Delta

## MODIFIED Requirements

### Requirement: Ficha individual de seleção e compra

O sistema SHALL fornecer ao fotógrafo uma ficha individual por combinação de galeria e cliente, com vínculo, prazo, estado de seleção, pagamento, quantidade, totais e datas operacionais, sem exigir galeria derivada.

#### Scenario: Fotógrafo abre uma seleção

- **WHEN** o fotógrafo expande `Acervo da cliente` no card de uma cliente vinculada
- **THEN** vê somente resumo, fotos e pedidos daquela cliente, sem combinar dados das demais

### Requirement: Imutabilidade comercial após confirmação

O sistema SHALL manter congeladas as fotos, valores e regras de um pedido confirmado. A cliente poderá realizar novo pedido distinto de fotos ainda elegíveis enquanto seu prazo de seleção naquela galeria estiver ativo.

#### Scenario: Cliente compra fotos adicionais

- **WHEN** uma cliente com pedido confirmado seleciona novas fotos autorizadas na mesma galeria ainda ativa
- **THEN** o sistema cria novo fluxo de pedido sem alterar o pedido confirmado
