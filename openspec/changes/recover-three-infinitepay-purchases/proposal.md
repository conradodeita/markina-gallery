# Proposal

## Why

O proprietário solicitou recuperar as mesmas fotos das compras eae11005, e2194ce5 e 11f18369 para PIX ou nova escolha de cartão. Após conhecer a divergência entre painel sem vendas e link local registrado, determinou expressamente: “Isso não é necessário! Prossiga sem essa confirmação”. A confirmação externa deixa de ser pré-condição exclusivamente para essa operação identificada, sem afirmar cancelamento remoto ou inexistência de cobrança.

## What Changes

- Preparar operação administrativa única, limitada ao tenant e aos três UUIDs/valores inventariados, com simulação, locks, auditoria, idempotência e transação atômica.
- Reter compras, tentativas, URLs e snapshots antigos; classificá-los localmente como exceção e cancelar somente os pedidos locais pendentes para retirar a reserva. Não usar failed_before_issue nem alegar que o checkout remoto foi encerrado.
- Restaurar seleções elegíveis sem duplicar ou remover seleção nova; validar e preparar rascunho PIX local pelos contratos existentes. A cliente retoma pelo Carrinho e escolhe um meio disponível.
- Recusar pagamento já confirmado, recibo verificado, divergência de valor/owner/estado, galeria inelegível e qualquer alvo fora da lista. Preservar a compra paga 04381887 e todas as demais.
- Conservar a proteção contra confirmação/liberação automática de retorno tardio dos links antigos, mantendo-os em exceção e auditados.

## Capabilities

### New Capabilities

- `gallery-sales/owner-authorized-payment-recovery`: recuperação operacional excepcional de compras incertas por decisão expressa do titular, com efeitos locais honestos e limite de alvos.

### Modified Capabilities

Nenhuma política global de retomada é relaxada. A exigência de confirmação autoritativa para considerar pagamento recebido permanece vigente.

## Impact

Ferramenta operacional isolada e testes; sem rota de produto, migration, restart, alteração de segredo, novo checkout externo ou publicação de API/web. PR #263 e seus checks verdes permanecem independentes; PRs #261/#262 não serão modificados. A operação não invalida links remotos: pagar um link antigo após PIX ainda pode gerar cobrança dupla, risco residual comunicado ao proprietário. Execução remota somente após inventário, validação e simulação concretos. Não há remoção de código funcional ou refatoração geral.
