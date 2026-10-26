## Context

O dl payment-order__facts possui três colunas globais. Dentro do painel de pagamento, IDs longos não quebram e extrapolam as células.

## Goals / Non-Goals

Garantir leitura integral em desktop e mobile. Não alterar lógica de pagamentos, conteúdo, snapshots, APIs, schema, critérios dos filtros ou ações.

## Decisions

Aplicar regras no CSS Module existente, limitadas ao dl dentro de paymentSection. Usar uma coluna, min-width:0 e overflow-wrap:anywhere, preservando o estilo global dos demais fatos do pedido. Não há código obsoleto a remover; a regra global permanece consumida pelos metadados gerais.

Seguimento autorizado: a grade de Mais filtros usa colunas proporcionais, mas o select de situação financeira mantém largura intrínseca maior que a célula e invade Provedor. Limitar controles e labels à célula e usar colunas auto-fit com largura mínima útil, restritas aos filtros desta página. Preservar todas as opções e o envio existente.

## Risks / Trade-offs

O card ocupa mais altura; em troca, cada identificador e estado permanece associado ao seu rótulo e não exige truncamento.

## Validation

Validar geometria com dados sintéticos nos temas claro/escuro e larguras desktop/mobile, executar verificações frontend proporcionais e OpenSpec estrito. Não modificar DOM/CSS de produção para simular publicação.
