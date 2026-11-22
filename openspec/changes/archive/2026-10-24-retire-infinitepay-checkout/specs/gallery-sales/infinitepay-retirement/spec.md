# Spec Delta

## Purpose

Retirar a operação InfinitePay antes da integração de outro provedor, preservar o histórico das compras concluídas e manter o PIX manual do Pick-your-Pic.

## ADDED Requirements

### Requirement: InfinitePay desativada para novas compras

O sistema SHALL deixar de oferecer ou criar novos checkouts InfinitePay. Antes de uma integração posterior de cartão, o PIX manual SHALL continuar disponível conforme suas próprias configurações e regras.

#### Scenario: Cliente inicia compra durante a transição
- **WHEN** a cliente revisa uma compra que exige pagamento antes da integração Mercado Pago
- **THEN** o sistema não apresenta InfinitePay nem emite link externo de cartão
- **AND** um PIX manual válido continua disponível de forma independente

#### Scenario: Tentativa de chamar endpoint legado
- **WHEN** cliente ou interface chama uma rota de emissão, retorno, webhook ou recuperação InfinitePay aposentada
- **THEN** o sistema não cria, confirma, retoma nem altera uma cobrança InfinitePay
- **AND** a resposta não revela credenciais, configuração ou dados de outro tenant

### Requirement: Segredos e configuração InfinitePay removidos

O sistema SHALL remover a interface e as rotas para cadastrar ou alterar InfiniteTag/API Key, e SHALL remover por migration os registros exclusivos de configuração e segredos InfinitePay. A infraestrutura genérica de segredos MUST permanecer disponível para outras integrações. Nenhum segredo real MUST ser lido, exibido ou incluído em código versionado durante esta change.

#### Scenario: Configurações após a aposentadoria
- **WHEN** o fotógrafo abre Configurações
- **THEN** não há card ou fluxo para cadastrar, habilitar ou desconectar InfinitePay
- **AND** os controles de PIX permanecem operacionais

### Requirement: Histórico financeiro InfinitePay preservado

Os pedidos e registros financeiros InfinitePay existentes SHALL conservar identidade, cliente/tenant, fotos, total, estado confirmado, NSU de transação, snapshots comerciais, timestamps, recibos e correções. Compras históricas SHALL permanecer visíveis como InfinitePay legado, em modo de consulta, sem link ou ação para retomar checkout.

#### Scenario: Consulta de uma compra concluída
- **WHEN** cliente ou fotógrafo consulta uma das compras InfinitePay concluídas
- **THEN** pedidos, fotos, valor, confirmação e referência da transação continuam associados e consultáveis
- **AND** a interface identifica InfinitePay como meio legado e não oferece novo pagamento pelo link antigo

#### Scenario: Migration sobre histórico existente
- **WHEN** a migration de aposentadoria é aplicada a uma base contendo compras InfinitePay
- **THEN** linhas de pedidos, pagamentos, tentativas, recibos e correções permanecem consistentes e sem órfãos
- **AND** apenas configuração, segredos, referência técnica às credenciais e URL operacional do checkout são removidos

### Requirement: PIX manual independente preservado

A aposentadoria da InfinitePay MUST NOT modificar configurações, snapshots, grupos, confirmações, histórico, disponibilidade ou interface do PIX manual.

#### Scenario: PIX antes e depois da aposentadoria
- **WHEN** uma compra usa PIX manual ou o fotógrafo consulta uma compra PIX anterior
- **THEN** QR/copia-e-cola, valores, confirmação manual e histórico mantêm o contrato vigente
- **AND** nenhuma configuração InfinitePay é necessária para concluir ou consultar esse fluxo
