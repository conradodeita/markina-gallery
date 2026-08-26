# Homologação — interfaces operacionais de galerias

Data: 2026-08-26

Commit implantado: `ad098c2` (`feat(galleries): add operational gallery interface`).

## Escopo aplicado

O deploy foi executado somente em `/opt/markina-gallery`, com o projeto Docker Compose `markina-gallery`. Foram reconstruídos e recriados somente os serviços web, API, worker e migração desse projeto. Banco, Redis e Nginx do Markina permaneceram no mesmo projeto; ClearBudget, Nginx Proxy Manager, firewall, DNS, certificados, redes e volumes externos não foram alterados.

## Evidências

- Todos os serviços `markina-gallery-*` ficaram saudáveis.
- `GET /api/health` respondeu `200` com `{"status":"ok","service":"api"}`.
- A nova rota `/admin/operations` respondeu `200`.
- `GET /api/admin/clients` sem sessão respondeu `403`, confirmando a fronteira administrativa.
- O container `firefly_api` do ClearBudget permaneceu em execução.

## Pendência deliberada

Não foram inseridos clientes, acervos ou fotos sintéticos no banco de homologação e não foram usadas credenciais administrativas reais. A validação autenticada ponta a ponta do fluxo de cadastro, importação e criação de galeria deve ocorrer em uma sessão administrativa autorizada, com dados sintéticos descartáveis.
