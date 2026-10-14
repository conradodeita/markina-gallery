# Proposal

## Why

A área `Vendas e pagamentos` já oferece um filtro por nome, mas ele aparece depois do card `Seleções em aberto` e deixa de acompanhar o fotógrafo durante a rolagem. O filtro existente também não localiza uma cliente pelo telefone, dificultando encontrar vendas rapidamente quando há muitos pedidos.

## What Changes

- Ampliar o filtro existente de Cliente para localizar por nome ou telefone cadastrado e sugerir nomes correspondentes enquanto o fotógrafo digita, sem criar um segundo campo de busca.
- Ao escolher uma sugestão, restringir a consulta à identidade daquela cliente; texto digitado sem seleção continua como busca parcial por nome ou telefone.
- Reposicionar os filtros antes do resumo e das listas operacionais e mantê-los acessíveis no topo durante a rolagem, abaixo da navegação administrativa.
- Manter os filtros secundários de galeria, situação financeira, mensagem e período dentro do mesmo conjunto de controles, com apresentação compacta em telas pequenas.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `gallery-sales/operational-gallery-interface`: definir busca por nome/telefone e posição persistente dos filtros em Vendas e pagamentos.

## Impact

- Frontend: `frontend/app/admin/payments/page.tsx` e estilos administrativos.
- Backend: reutilizar a busca autenticada existente `GET /admin/clients` para sugestões e ampliar `GET /admin/payment-communications` com busca por telefone e seleção exata por identificador; sem migration.
- Testes focados de busca, sugestões, seleção exata, paginação, acessibilidade e posição responsiva da barra; sem alteração de pedidos, estados financeiros, mensagens ou dados persistidos.
