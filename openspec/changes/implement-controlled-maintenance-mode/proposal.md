# Proposal

## Why

Manutenções programadas precisam fechar novas operações sem invalidar sessões, interromper uploads ou perder tarefas em execução. A implementação local anterior não estava isolada do experimento de release Python nem definia um contrato autocontido de manutenção. Esta change organiza o controle dedicado; a primeira ativação continua sem mecanismo reconhecido pelos containers legados.

## What Changes

- Formalizar um modo operacional de manutenção, desativado por padrão, que fecha ingressos incompatíveis e pausa novos ciclos de workers.
- Preservar operações já admitidas até conclusão confirmada; erros ou falta de ACK mantêm o gate fechado.
- Tratar retornos de pagamento e webhooks de mensagens como operações críticas monitoradas, sem resposta 2xx artificial.
- Preservar filas persistentes e permitir retomada por comando explícito.
- Registrar o limite do bootstrap legado e bloquear publicação até haver uma decisão operacional e uma estratégia comprovada para a primeira transição.

## Capabilities

### New Capabilities

### Modified Capabilities

- `deployment-operations`: adiciona o contrato de manutenção cooperativa, callbacks críticos e retomada controlada.

## Impact

Afeta a middleware ASGI, um controle Redis dedicado à manutenção, o CLI operacional e os consumidores de jobs instrumentados. Não inclui o executor experimental de release Python, serviços novos, schema ou migrations. A disponibilidade de callbacks durante a substituição do processo API e o primeiro bootstrap legado permanecem condições operacionais a comprovar, não garantias implícitas deste modo.
