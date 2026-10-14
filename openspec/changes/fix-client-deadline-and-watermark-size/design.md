## Context

Veja `proposal.md`. A galeria privada já armazena `selection_expires_at`, criado a partir de `selection_duration_days` da Galeria pública, e o backend já devolve prazo e permissão de seleção. A galeria e a biblioteca da cliente, porém, não vinculam de forma consistente a mensagem de prazo à existência de um carrinho editável. Na proteção visual, API e gerador de mídia aceitam 10–96 px, mas a prova do frontend aplica um teto de 32 px.

## Goals / Non-Goals

**Goals:**

- Manter uma única data autoritativa por galeria privada e apresentá-la somente quando orientar uma ação editável da cliente.
- Preservar expiração, reabertura, carrinho e pedido congelado já existentes.
- Fazer a prova de proteção refletir o valor real aceito pelo servidor.

**Non-Goals:**

- Recalcular retroativamente prazos já gravados quando o padrão da Galeria pública mudar.
- Bloquear a consulta de pedidos ou fotos compradas após a expiração.
- Reprocessar prévias existentes, ampliar o intervalo de 10–96 px ou alterar o algoritmo da marca-d’água.

## Decisions

### Prazo absoluto continua pertencendo à galeria privada

Ao criar a associação, o backend continuará convertendo a duração configurada na Galeria pública em `selection_expires_at`. Mudanças posteriores no padrão valerão para novas galerias; reaberturas continuarão sendo o mecanismo explícito para alterar uma galeria existente. Isso evita que uma edição global prolongue ou encurte silenciosamente seleções em andamento.

Alternativa descartada: calcular `agora + duração` em cada leitura. Esse modelo nunca expiraria de forma estável e não seria auditável.

### Visibilidade depende do carrinho editável

A galeria e a biblioteca usarão o prazo devolvido pelo backend em conjunto com a quantidade da seleção corrente. A data será mostrada quando `selection.quantity > 0` e o conjunto ainda puder ser alterado. Um pedido congelado por comunicação de pagamento usa seu próprio estado comercial e não será apresentado como seleção editável.

Alternativa descartada: mostrar a data em todos os cards. Isso polui a jornada e sugere que pedidos já congelados ainda podem ser modificados.

### Prova usa o tamanho configurado sem teto de 32 px

O frontend removerá somente o `Math.min(..., 32)` da prova. Os limites do campo e da API permanecem 10–96 px; o contêiner continuará controlando overflow e posicionamento sem alterar o valor mostrado.

Alternativa descartada: aumentar o teto para outro número arbitrário. Isso manteria divergência entre configuração válida e prova visual.

## Risks / Trade-offs

- [Texto grande pode ultrapassar a pequena prova] → manter contenção visual e testar 96 px sem reduzir o tamanho configurado.
- [Prazo aparecer para pedido já congelado] → condicionar a mensagem à seleção corrente, não à existência de qualquer pedido histórico.
- [Galerias antigas sem data] → preservar `null` como “sem prazo configurado”, sem inventar data móvel ou fazer backfill.

## Migration Plan

1. Adicionar contratos direcionados para seleção com prazo e prova acima de 32 px.
2. Ajustar somente as condições de apresentação da cliente e o cálculo visual da prova.
3. Validar testes focados, TypeScript, lint focado e OpenSpec estrito.
4. Publicar por SHA imutável somente após inventário e autorização específica; rollback retorna API/web ao SHA saudável anterior, sem downgrade ou restauração.
