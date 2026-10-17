# Spec Delta

## ADDED Requirements

### Requirement: Não exibir resumo agregado legado de falhas de mensagem
Vendas e pagamentos SHALL NOT apresentar um total agregado de falhas derivado da projeção de compatibilidade de mensagens. Estados e ações de recuperação SHALL permanecer associados às entregas reais de cada pedido quando forem atuais e acionáveis.

#### Scenario: Resumo financeiro
- **WHEN** o fotógrafo abre Vendas e pagamentos
- **THEN** a página não apresenta o card agregado `Falhas de mensagem`

#### Scenario: Falha recuperável em pedido
- **WHEN** uma entrega real associada a um pedido falha e ainda pode ser reenviada
- **THEN** o pedido mantém o estado de falha e a ação de recuperação aplicável

#### Scenario: Canal desativado ou entrega cancelada
- **WHEN** uma entrega está cancelada por configuração de canal ou não foi tentada
- **THEN** o painel não a apresenta como falha real de transporte
