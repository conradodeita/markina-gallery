# Design

## Context

Veja proposal.md. O painel usa CSS e UI Kit locais, consulta todos os pedidos correspondentes antes de paginar clientes e mantém decisões em handlers independentes. Derivados `thumbnail` (480 px) e `admin_preview` já existem em media.py; respostas protegidas possuem cache privado/restritivo. Estatísticas tem quatro rotas e agregações exclusivas em main.py. Há mudanças preexistentes no workspace que devem ser preservadas.

## Goals / Non-Goals

**Goals:** interfaces agrupadas legíveis; filtro prioritário sintético; consulta/exportação com predicados comuns; imagens por pedido apenas sob demanda; remoção exclusiva de Estatísticas.

**Non-Goals:** novas fórmulas financeiras, pipeline de mídia, migration, SaaS multitenant, deploy ou mudança de secrets. O código atual autoriza o único fotógrafo por require_admin; a fundação multitenant está planejada em change separada e não será improvisada aqui.

## Decisions

- Extrair função interna da projeção existente, preservando a consulta/ordenação; listar continua com paginação. Export usa a mesma projeção sem cursor e sem consultar seleções, com campos adicionais confirmados. `priority` é apenas filtro sintético; ausência continua compatível com consumidores atuais da API.
- CSV produzido no servidor, BOM/semicolon/CRLF, quatro colunas; valores derivados dos snapshots/totais, data efetivamente confirmada convertida para America/Sao_Paulo. Não montar CSV de páginas baixadas no browser. Usar escopos de PIX em lote para evitar N+1.
- Servir variantes existentes em endpoint autenticado por item de pedido: validar pedido+item e FK da foto; sem fallback a original/histórico removido. Nenhum novo processamento. Detalhes abertos montam imagens lazy; modal carrega somente a imagem ativa. Manter headers de proteção existentes.
- Usar dialog nativo modal na top layer com portal, foco restaurado, Escape/setas, backdrop e bloqueio de scroll. Alternativa de seção inline rejeitada pelo mandato.
- Manter os controles existentes de PaymentActions/OrderDeliveryForm. Layout de detalhe em áreas Fotos, Pagamento, Entrega; resumo inclui quantidade real de itens. Usar CSS local e tokens em todos os temas.
- Estatísticas retorna 404 pela ausência de page.tsx e dos handlers exclusivos. Remover helpers e CSS após busca de referências; preservar tabelas, tipos e helpers compartilhados. Arquivos históricos OpenSpec permanecem como registro, com esta change supersedendo a funcionalidade.
- Sincronizar o escopo operacional API/web com esta change: incluir por caminhos exatos os runtimes de `/admin/payments`, exportação e navegação; permitir somente a remoção dos dois arquivos antigos da página/teste de Estatísticas; registrar blobs exatos dos runtimes presentes. Baseline, revisão de banco e aprovações de produção permanecem inalterados. Essa preparação mantém CI e preflight em falha fechada e não autoriza publicação.

## Risks / Trade-offs

- [Consulta completa do legado em memória] → reutilizar agregação em lote já existente, sem imagens no CSV e sem transferir todos os dados ao browser. Não criar limite que trunque silenciosamente exportação.
- [Resposta obsoleta] → AbortController e revisão da consulta; preservar filtros aplicados ao escolher sugestão.
- [Imagem removida ou derivado ausente] → 404 protegido e placeholder; não expor caminhos ou original.
- [Mudanças locais paralelas] → preservar baseline e revisar diff incremental; não commitar/reverter arquivos preexistentes.

## Migration Plan

Sem migration ou dados alterados. Validação local com banco sintético isolado e suites existentes; build/lint/typecheck. Qualquer liberação remota exige inventário e autorização separada. Não sincronizar spec principal nem arquivar antes da revisão humana.
