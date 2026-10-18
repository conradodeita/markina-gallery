## ADDED Requirements

### Requirement: Estatísticas aposentada com dados preservados

O sistema SHALL NOT expor `/admin/statistics` nem suas APIs exclusivas de consulta e exportação. A navegação SHALL NOT oferecer Estatísticas. Os registros persistidos SHALL permanecer intactos, e métricas operacionais compartilhadas SHALL continuar disponíveis nas áreas correspondentes.

#### Scenario: Acesso legado

- **WHEN** alguém acessa diretamente a página ou uma API antiga de Estatísticas
- **THEN** a aplicação retorna 404 sem alterar pedidos, pagamentos, itens, seleções ou histórico comercial

## REMOVED Requirements

### Requirement: Estatísticas comerciais isoladas por fotógrafo

#### Reason

O painel e suas rotas foram aposentados; o escopo operacional remanescente é coberto pelas telas correspondentes.

### Requirement: Indicadores financeiros com denominadores explícitos

#### Reason

Os indicadores exclusivos de Estatísticas foram aposentados; os indicadores operacionais de Vendas e pagamentos e Visão geral permanecem.

### Requirement: Seleção sem compra distinta de abandono

#### Reason

O relatório exclusivo de seleções sem compra foi aposentado, mantendo seleções em andamento nas áreas operacionais.

### Requirement: Conversão por seleção resolvida

#### Reason

A análise de conversão exclusiva de Estatísticas foi aposentada.

### Requirement: Detalhamento de venda e pagamento

#### Reason

O relatório duplicado foi aposentado; pedidos e dados financeiros continuam disponíveis em Vendas e pagamentos.

### Requirement: Reconciliação financeira visível

#### Reason

A reconciliação exclusiva de Estatísticas foi aposentada; os valores persistidos não são alterados por esta change.

### Requirement: HTML comercial autônomo

#### Reason

A exportação HTML exclusiva de Estatísticas foi aposentada.

### Requirement: CSV de vendas exclusivo do proprietário

#### Reason

O CSV antigo foi aposentado. A nova exportação operacional tem escopo e colunas próprios, protegidos pela sessão administrativa.

### Requirement: CSV estruturado por item

#### Reason

O formato de relatório antigo foi aposentado em favor do CSV operacional de uma linha por pedido.
