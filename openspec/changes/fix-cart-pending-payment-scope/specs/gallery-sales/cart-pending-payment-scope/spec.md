## ADDED Requirements

### Requirement: Pendência vinculada às fotos da compra

O carrinho SHALL distinguir a seleção atual das compras pendentes do mesmo cliente e tenant por seus snapshots de fotos. Compra anterior sem interseção MUST NOT ocultar meios disponíveis ou substituir o total da seleção nova. Fotos congeladas SHALL permanecer inelegíveis a nova cobrança em qualquer meio.

#### Scenario: Novas fotos após resultado desconhecido
- **WHEN** existe compra incerta e o cliente seleciona somente fotos não reservadas nessa compra
- **THEN** o carrinho mostra o total atual e oferece os meios disponíveis para essas fotos
- **AND** mantém a compra anterior, seu total e reservas inalterados em acompanhamento separado

#### Scenario: Seleção contém foto reservada
- **WHEN** uma seleção inclui foto de pedido congelado pendente, mesmo por outra galeria
- **THEN** o backend recusa preparar PIX e cartão para a seleção inválida
- **AND** não modifica nem reemite a compra existente

#### Scenario: Nenhuma nova seleção
- **WHEN** o carrinho não contém fotos selecionadas e há compra pendente
- **THEN** permite acompanhar ou retomar a compra existente sem oferecer nova cobrança para suas fotos

### Requirement: Escolha de meio antes da emissão

O cliente SHALL poder alternar PIX/cartão para a seleção atual válida enquanto não houver emissão pendente correspondente às suas fotos. O histórico SHALL identificar valores de compras anteriores separadamente. A troca MUST NOT cancelar, liberar, incrementar ou converter tentativa de resultado desconhecido.

#### Scenario: Troca de cartão para PIX na seleção nova
- **WHEN** o cliente escolhe cartão, volta a PIX e ainda não emitiu checkout da seleção atual
- **THEN** a interface apresenta o PIX correspondente ao total atual e não envia solicitação de cartão

#### Scenario: Emissão atual perde a resposta
- **WHEN** o checkout da seleção atual fica em verification_required
- **THEN** continua impedindo outra cobrança para as mesmas fotos e orienta acompanhamento/reconciliação

### Requirement: Isolamento das pendências

A projeção SHALL retornar somente compras, pedidos e snapshots do cliente e tenant autenticados. UUIDs de outra conta MUST NOT afetar o bloqueio ou revelar pendências. A correção MUST NOT alterar pagamentos reais, confirmar recusa por HTTP isolado ou recuperar reservas sem evidência financeira suficiente.

#### Scenario: Pendência de outra pessoa
- **WHEN** outra pessoa ou tenant possui compra pendente
- **THEN** a projeção não revela essa compra nem a considera impedimento da seleção autenticada
