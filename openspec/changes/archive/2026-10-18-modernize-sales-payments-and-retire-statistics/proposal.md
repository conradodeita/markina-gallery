# Proposal

## Why

O fotógrafo precisa localizar pendências e revisar pedidos com fotos sem sair do contexto financeiro. O mandato humano desta execução aprova a implementação imediata do redesign, busca automática, filtro prioritário, lightbox, CSV compacto e aposentadoria de Estatísticas.

## What Changes

- Reorganizar Vendas e pagamentos usando UI Kit e tokens existentes, mantendo grupos por cliente, pedidos expansíveis e todos os gates financeiros/entrega.
- Aplicar imediatamente a seleção de sugestão de cliente, conservando filtros aplicados e busca livre manual.
- Iniciar e limpar filtros para pendências prioritárias (`reported` + `confirmed_undelivered`), com opção explícita Todos e filtros individuais.
- Reutilizar thumbnail e admin_preview existentes em detalhes sob demanda, com modal acessível, navegação e fallback.
- Exportar todos os pedidos filtrados no servidor em CSV Excel/pt-BR, exatamente quatro colunas e confirmação efetiva como data.
- **BREAKING:** remover interface, menu e APIs comprovadamente exclusivas de Estatísticas; rota antiga retorna 404. Preservar dados e métricas compartilhadas.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `gallery-sales/payment-operations-dashboard`: organização operacional, busca automática, filtro combinado, prévias, CSV e aposentadoria de Estatísticas.

## Impact

Frontend de pagamentos, CSS local, menu e página de Estatísticas; handlers de consulta e APIs exclusivas no FastAPI; testes direcionados e relatório técnico. Sem migration, mudança de banco/segredo, dependência visual ou deploy. A arquitetura atual opera uma conta administrativa; o isolamento SaaS futuro em `add-tenant-ownership-foundation` permanece fora deste escopo.
