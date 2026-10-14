## Why

O proprietário solicitou retirar o feedback facial da interface cliente, reconhecer galerias e pastas pela fotografia e permitir corrigir a decisão de pagamento não localizado após resolução bancária fora do sistema.

## What Changes

- Retirar o botão “Não é esta pessoa” dos resultados, preservando seleção, favoritos, resultados e controles biométricos existentes.
- Mostrar capa clicável no card da biblioteca, mantendo nome, evento, estado e “Ver fotos”. Mostrar prévia da própria pasta no seletor de pastas.
- Estender a correção financeira existente de confirmação para recusa: voltar à revisão, silenciosamente, e permitir nova decisão explícita do fotógrafo sobre pedido ou PIX agrupado.

## Capabilities

### New Capabilities
- `client-gallery-covers-and-payment-review`: apresentação visual das galerias e revisão de recusa financeira.

### Modified Capabilities

Decisão explícita do proprietário substitui apenas a obrigatoriedade de botão de feedback cliente descrita no roadmap; não remove dados, endpoint ou revisão histórica.

## Impact

Frontend cliente e componente financeiro compartilhado; projeção de biblioteca e capacidades financeiras; endpoint de correção, testes e documentação. Sem migration prevista, deploy, mensagens reais ou alteração de secrets. Preservar trabalho local anterior. Push + PR seguido de parada para o proprietário conferir CI.
