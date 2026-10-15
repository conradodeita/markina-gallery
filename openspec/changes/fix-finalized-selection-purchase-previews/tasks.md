# Tasks

## 1. Correção da prévia comercial

- [x] 1.1 Registrar regressão para `/library/purchases/items/{item_id}/preview`, com e sem `/api`, no teste real do normalizador; executar antes da correção e comprovar a falha esperada em `validation.md`. Evidência: execução pré-correção com 27 aprovados e duas falhas esperadas (normalizador retornava null e card não montava imagem).
- [x] 1.2 Aceitar somente o novo formato de prévia comercial; validar as quatro famílias de rota, prefixo único, recusa de URLs externas/administrativas/originais, traversal, queries e fragments e fallback de mídia ausente; registrar os resultados dos testes focados.
- [x] 1.3 Exercitar o card real de Compras com seleção canônica finalizada sem cobrança e prévia por item, sem mockar o normalizador; comprovar montagem da imagem protegida e compatibilidade de histórico/pedidos existentes pelos testes pertinentes.

## 2. Integração e entrega

- [x] 2.1 Revisar o baseline e a cobertura existente de autorização do endpoint comercial, preservando recusa de item alheio e pedido inelegível; executar as regressões afetadas ou registrar a validade verificável de evidência reutilizada.
- [x] 2.2 Executar lint, typecheck, build e testes frontend pertinentes; validar OpenSpec estrito em 1.14.0 e diff-check; registrar resultados e revisar diff sem incorporar alterações anteriores das outras changes.
- [ ] 2.3 Preparar commit/PR focado e anexar ao chat; verificar CI do HEAD entregue. Deploy não integra a autorização desta etapa e depende de inventário/plano/autorização específicos.

## Workflow follow-up

Após publicação autorizada, o proprietário deve conferir a prévia do pedido observado em Compras. Revisão humana antes de sincronizar specs e arquivar. Retomar o piloto A+B na sua task 8.3; não marcar o roteiro remoto concluído pelas sessões somente de A.
