# Homologação — superfícies visuais de validação

Data: 2026-08-26

Commit implantado: `1f0d5b0` (`feat(ui): add visual validation surfaces`).

## Escopo aplicado

A publicação foi executada exclusivamente no diretório `/opt/markina-gallery`, usando o projeto Docker Compose `markina-gallery`. Foram reconstruídos e recriados somente os serviços `api` e `web` desse projeto.

Banco de dados, Redis, worker, proxy reverso, DNS, certificados, firewall, redes e volumes não foram alterados. Nenhum serviço ou arquivo do ClearBudget foi modificado.

## Interfaces incluídas

- Painel administrativo com indicadores operacionais, ambiente, versão, ações rápidas e galerias recentes.
- Biblioteca do cliente com estados de carregamento, vazio e erro, cartões de galerias e histórico de compras.
- Galeria do cliente com grade visual de fotos, seleção, favoritos, comentários e visualização protegida quando autorizada pelo backend.
- Resumo administrativo servido por `GET /api/admin/validation-summary`, sem expor telefones de clientes.

## Evidências de publicação

- O checkout em homologação está no commit `1f0d5b0`.
- Os containers `markina-gallery-api-1` e `markina-gallery-web-1` ficaram `healthy` após a reconstrução.
- `GET http://127.0.0.1:8080/api/health` respondeu `200` com `{"status":"ok","service":"api"}`.
- `GET http://127.0.0.1:8080/admin` respondeu `200`.
- O container `firefly_api` do ClearBudget permaneceu em execução.

## Verificações de código

- Teste focado do resumo administrativo: aprovado.
- `ruff check backend/app backend/tests`: aprovado.
- `npm run lint`: aprovado sem erros; permanece um aviso do Next.js sobre a otimização de uma imagem da galeria.

## Validação funcional pendente

Ainda é necessária a revisão visual manual nas duas perspectivas: administrador e cliente autenticado. Ela confirmará apresentação em tela, seleção, favoritos, comentários, visualização de compra e estados de erro/vazio com dados reais de homologação. Qualquer achado será registrado e tratado como correção ou nova mudança aprovada no OpenSpec.
