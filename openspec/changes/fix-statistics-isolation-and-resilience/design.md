# Design

## Context

Consulte `proposal.md` e os deltas de `gallery-sales/sales-statistics`. A API atual já calcula os agregados no backend, mas resolve o cliente por galerias e depois consulta todos os pedidos e seleções dessas galerias. A página recebe no máximo 100 itens e transforma qualquer falha da consulta em um objeto vazio.

## Goals / Non-Goals

**Goals:**

- Aplicar o cliente como predicado explícito em pedidos e seleções quando o filtro estiver presente.
- Preservar a contagem e a identificação textual de itens confirmados mesmo quando a FK operacional foi anulada.
- Manter exports completos e adicionar paginação somente à resposta HTML.
- Exibir erro recuperável sem confundir indisponibilidade com ausência de dados.

**Non-Goals:**

- Não criar migration, alterar o modelo de retenção histórica ou mudar a regra financeira de confirmação.
- Não adicionar CSV, PDF, filtros novos ou exportação assíncrona.
- Não alterar deploy, infraestrutura, autenticação ou dados existentes.

## Decisions

1. **Escopo comercial explícito:** conservar a resolução de galerias autorizadas para o filtro de cliente, mas adicionar `SaleOrder.client_id` e `PhotoSelection.client_id` às consultas. Essa abordagem corrige galerias compartilhadas sem mudar o contrato dos filtros.
2. **Snapshot como fallback:** cada item confirmado usará `photo_asset_id` quando disponível e `photo_asset_id_snapshot` caso contrário; o nome virá de `filename_snapshot`. O ID do snapshot será a identidade textual estável no export.
3. **Paginação independente:** a resposta aceitará offsets distintos para compradas e selecionadas, retornará totais separados e manterá `limit` comum. Os exports não enviarão offsets e continuarão completos.
4. **Erro explícito no frontend:** a página manterá filtros e opções carregadas, limpará somente os dados em carregamento e exibirá mensagem com retry quando a consulta falhar. O estado vazio continuará reservado para resposta válida sem itens.
5. **Compatibilidade de payload:** os campos existentes `purchased_count` e `selected_not_purchased_count` continuarão presentes; novos totais explícitos suportarão a paginação sem quebrar consumidores atuais.

## Risks / Trade-offs

- [Uma resposta antiga pode não conter os novos totais] → a interface usará os campos de total novos quando presentes e manterá fallback para os contadores existentes.
- [Offsets separados aumentam a superfície de query] → ambos serão validados com `ge=0`, o limite permanecerá entre 1 e 500 e os exports seguirão sem paginação.
- [Foto selecionada sem ativo nem snapshot próprio] → a seleção continuará dependente da referência textual disponível no modelo atual; este change não inventa nome nem restaura mídia.

## Migration Plan

Não há migration. Publicar o backend antes ou junto do frontend é compatível porque os campos antigos permanecem na resposta; após a atualização, executar testes automatizados e smoke autenticado em homologação conforme autorização humana, sem alterar dados.
