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

## Estado inicial

Na primeira publicação não foram inseridos clientes, acervos ou fotos sintéticos no banco de homologação e não foram usadas credenciais administrativas reais. A validação autenticada foi executada posteriormente, conforme registrado abaixo.

## Validação autenticada posterior

Com uma sessão administrativa autorizada, foram criados em homologação um cliente, um acervo e uma galeria identificados como `Teste Operacional 20260826`, além de duas importações de uma imagem JPEG sintética de cor sólida, sem pessoa ou metadados reais. Ambas terminaram em `completed`; as fotos ficaram disponíveis para atribuição e a galeria privada foi criada com favoritos e comentários habilitados.

Durante esse teste foi identificado e corrigido um erro de interface após o envio de arquivo: a limpeza do formulário ocorria após a referência do evento ter sido descartada. A correção `13846a4` foi publicada somente no serviço web do Markina Gallery e retestada com sucesso. O ClearBudget permaneceu em execução durante toda a operação.
