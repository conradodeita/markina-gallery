# gallery-sales/sales-statistics Specification

## Purpose

Registrar a aposentadoria das interfaces de Estatísticas. Os dados de pedidos e pagamentos permanecem preservados e são apresentados nas áreas operacionais correspondentes.

## Requirements

### Requirement: Estatísticas aposentada com dados preservados

O sistema SHALL NOT expor `/admin/statistics` nem suas APIs exclusivas de consulta e exportação. A navegação SHALL NOT oferecer Estatísticas. Os registros persistidos SHALL permanecer intactos, e métricas operacionais compartilhadas SHALL continuar disponíveis nas áreas correspondentes.

#### Scenario: Acesso legado

- **WHEN** alguém acessa diretamente a página ou uma API antiga de Estatísticas
- **THEN** a aplicação retorna 404 sem alterar pedidos, pagamentos, itens, seleções ou histórico comercial
