# Proposal

## Why

A busca por cliente/telefone, as sugestões de nomes e os filtros fixos foram implementados e publicados anteriormente, mas deixaram de constar na linha `main` usada pela release progressiva da galeria. O commit `92366f5` ficou somente em `develop`; o PR #179 partiu do baseline de produção `aa7119c` e foi publicado em `main` sem esse commit. A interface de produção perdeu o filtro e uma futura atualização da API baseada nessa linha também perderia a busca por telefone e cliente exato.

## What Changes

- Reintegrar na linha atual de `main` o comportamento já aprovado para Vendas e pagamentos: busca por nome/telefone, sugestões no filtro existente, seleção exata de cliente e faixa de filtros fixa no topo.
- Preservar as alterações de carregamento progressivo já publicadas em `main` e limitar o port aos arquivos da busca financeira e seus testes.
- Registrar a causa de linhagem e manter a atualização de dependências do PR #177 separada.
- Preparar validação e revisão por PR; nenhuma publicação de produção faz parte desta change.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `gallery-sales/operational-gallery-interface`: restaurar o filtro de cliente/telefone e sua posição fixa na linha de produção.

## Impact

- API: `GET /admin/payment-communications` aceita busca por telefone e identidade selecionada, sem serializar o telefone.
- Frontend: filtro existente com sugestões acessíveis, paginação pelo critério atual e posição fixa responsiva.
- Testes focados backend/frontend e validação OpenSpec.
- Não altera dependências, pedidos, pagamentos, mensagens, dados persistidos, banco ou serviços de produção.

## Não objetivos

- Mesclar todo `develop` em `main`.
- Incorporar ou modificar o PR #177 de dependências.
- Publicar em produção nesta change.
